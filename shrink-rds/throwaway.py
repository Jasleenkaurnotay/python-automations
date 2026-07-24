import boto3
import logging
import os
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger=logging.getLogger(__name__)

source_region = "us-east-1"


# Step 1: Query all details of existing, oversized rds instance
def sourcedbinfo(source_db_name, source_region):
    try:
        source_db_client = boto3.client('rds', region_name=source_region)

        source_db_info = source_db_client.describe_db_instances(
            DBInstanceIdentifier=source_db_name
        )
        logger.info(source_db_info)
    except source_db_client.exceptions.DBInstanceNotFoundFault as e:
        logger.error(str(e))
        raise
    # Unwrap the output so that everything downstream gets a clean single-instance dict as opposed to a list of dict
    return source_db_info['DBInstances'][0]


## postgresql://myuser:mypassword@my-instance.abc123.us-east-1.rds.amazonaws.com:5432/mydb
# username; password; endpoint; port; databasename
def get_db_link_details(source_db_info, password_env_var):
    if os.getenv(password_env_var) is None:
        raise ValueError(f"Environment variables {password_env_var} is not set")
    return {
        'user' : source_db_info['MasterUsername'],
        'endpoint' : source_db_info['Endpoint']['Address'],
        'port' : source_db_info['Endpoint']['Port'],
        'dbname' : source_db_info.get('DBName'),
        'password' : os.getenv(password_env_var)
    }

## Query actual storage utilized over a range of time from cloudwatch
def get_db_free_storage(source_db_info, source_region):
    start_time = datetime.now(timezone.utc) - timedelta(days=2)
    end_time = datetime.now(timezone.utc)
    cw_client = boto3.client('cloudwatch', region_name=source_region)

    free_storage_values = cw_client.get_metric_data(
        MetricDataQueries=[
            {
                'Id' : 'storage_utilized',
                'MetricStat': {
                    'Metric': {
                        "Namespace": "AWS/RDS",
                        "MetricName": "FreeStorageSpace",
                        "Dimensions": [
                            {
                                "Name": "DBInstanceIdentifier", "Value": source_db_info['DBInstanceIdentifier']
                            },
                        ],
                    },
                    'Period': 300,
                    'Stat': "Maximum"
                },
                "ReturnData": True
            }
        ],
        StartTime=start_time,
        EndTime=end_time
    )
    print(free_storage_values)
    return free_storage_values['MetricDataResults'][0]['Values']       # Extracts only the 'values' section from the output. Values is a list type of item


def evaluate_db_storage(free_storage_values, source_db_info):
    if not free_storage_values:
        raise ValueError("No Cloudwatch datapoints available - cannot evaluate storage")
    
    bytes_to_gb = 1024 ** 3
    min_free_space = min(free_storage_values) / bytes_to_gb
    used_gb = source_db_info['AllocatedStorage'] - min_free_space
    if used_gb >= 20:
        revised_db_size = used_gb * 1.2
    else:
        revised_db_size = 20 * 1.2
    
    logger.info(f"Revised DB storage size is {revised_db_size}")

    return round(revised_db_size)

def create_new_db(source_db_info, source_region, password_env_var, revised_db_size):

    try:
        logger.info("Creating DB password string")
        db_link = get_db_link_details(source_db_info, password_env_var)

        # Compute a list of security groups for the new DB
        sg_ids = []
        for sg in source_db_info['VpcSecurityGroups']:
            sg_ids.append(sg['VpcSecurityGroupId'])

        rds_client = boto3.client('rds', region_name=source_region)

        logger.info("Creating resized database")

        resized_db = rds_client.create_db_instance(
            DBInstanceIdentifier = f"new_{source_db_info['DBInstanceIdentifier']}",
            DBName = source_db_info['DBName'],
            AllocatedStorage = revised_db_size,
            DBInstanceClass = source_db_info['DBInstanceClass'],
            Engine = source_db_info['Engine'],
            EngineVersion = source_db_info['EngineVersion'],
            MasterUsername = source_db_info['MasterUsername'],
            MasterUserPassword = db_link['password'],
            Port = source_db_info['Endpoint']['Port'],
            PubliclyAccessible = source_db_info['PubliclyAccessible'],
            VpcSecurityGroupIds = sg_ids,
            DBSubnetGroupName = source_db_info['DBSubnetGroup']['DBSubnetGroupName']
        )

    except Exception as e:
        logger.error(f"An error occurred while creating resized database: {str(e)}")
        raise

    logger.info(f"New database instance creation initiated: {resized_db['DBInstance']['DBInstanceIdentifier']}")
    return resized_db['DBInstance']['DBInstanceIdentifier']






if __name__ == "__main__":
    db_info = sourcedbinfo("shrink-db", "us-east-1")
    free_storage = get_db_free_storage(db_info, "us-east-1")
    recommended_size = evaluate_db_storage(free_storage, db_info)
    logger.info(f"Original AllocatedStorage: {db_info['AllocatedStorage']} GB, Recommended: {recommended_size} GB")