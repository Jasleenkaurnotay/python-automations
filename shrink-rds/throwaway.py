import boto3
import logging
import os
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError, WaiterError
import psycopg2
from urllib.parse import quote_plus
import yaml
import subprocess
import time

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

# Create new DB instance with revised size 
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
            DBInstanceIdentifier = f"new-{source_db_info['DBInstanceIdentifier']}",
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

# Wait for revised db size instance to become available and accept DB connections
def check_rds_availability(source_region, resized_db, source_db_info, password_env_var):

    # 1. Query AWS for instance status
    # Initialize rds client
    rds_client = boto3.client('rds', region_name=source_region)

    # Get ready the DB_LINK variable
    db_link = get_db_link_details(source_db_info, password_env_var)

    try:
        logger.info(f"Querying if status of {resized_db} is available yet. This might take time")


        # Get the waiter object
        waiter = rds_client.get_waiter('db_instance_available')

        # Wait for instance to be available
        waiter.wait(
            DBInstanceIdentifier=resized_db,
            WaiterConfig={
                'Delay': 15,
                'MaxAttempts': 40
            }
        )
        logger.info(f"{resized_db} is now in 'Available' state. Attempting to connect to the postgresql application")
    except WaiterError as e:
        logger.error(f"Querying database status encountered an error: {str(e)}")
        raise

    resized_db_dict = rds_client.describe_db_instances(DBInstanceIdentifier=resized_db)['DBInstances'][0]
    logger.info(resized_db_dict)
    
    # 2. Attempt to connect to the database applcation
    if resized_db_dict['DBInstanceStatus'] == 'available':
        # Attempt to connect using psycopg2
        try:
            connection = psycopg2.connect(
                host = resized_db_dict['Endpoint']['Address'],
                database = db_link['dbname'],
                user = db_link['user'],
                password = db_link['password'],
                port = resized_db_dict['Endpoint']['Port'],
                sslmode = "require"
            )
            logger.info(f"Database connection using pscycopg2 with {resized_db_dict['DBInstanceIdentifier']} is successful")
        except Exception as e:
            logger.error(f"Encountered error connecting to database application using psycopg: {str(e)}")
            raise

        connection.close()
    else:
        raise RuntimeError(f"{resized_db_dict['DBInstanceStatus']} reported runtime error after waiter succeeded")

    return resized_db_dict

# Prepare pre-requisites for pgsync.yml file
def sync_dbs(source_db_info, resized_db_dict, password_env_var):
    try:
        from_db = get_db_link_details(source_db_info, password_env_var)
        to_db = get_db_link_details(resized_db_dict, password_env_var)

        #postgres://{user}:{password}@{endpoint}:{port}/{dbname}
        from_db_url = f"postgres://{from_db['user']}:{quote_plus(from_db['password'])}@{from_db['endpoint']}:{from_db['port']}/{from_db['dbname']}"

        to_db_url = f"postgres://{to_db['user']}:{quote_plus(to_db['password'])}@{to_db['endpoint']}:{to_db['port']}/{to_db['dbname']}"

        # Format yaml content as a dictionary to supply to yaml library
        yml_content = {
            'from': from_db_url,
            'to': to_db_url,
            'to_safe': True
        }

        # Write to the file in the same directory
        with open(".pgsync.yml", "w") as file:
            yaml.dump(yml_content, file)

        logger.info(".pgsync.yml has been successfully written to")

        # Executing pgsync
        logger.info("Executing pgsync")
        sync_output = subprocess.run(
            ["pgsync"],
            capture_output=True,
            text=True
        )

        if sync_output.returncode == 0:
            logger.info("pgsync completed successfully")
        else:
            raise RuntimeError(f"pgsync command execution failed with an error: {sync_output.stderr}")

    except Exception as e:
        logger.error(f"An error was encountered while constructing pre-requisites for pgsync run: {str(e)}")
        raise

    finally:
        if os.path.exists(".pgsync.yml"):
            os.remove(".pgsync.yml")
            logger.info(f".pgsync.yml deleted successfully")
        else:
            logger.info(f"Error: .pgysnc.yml file not found")
    return None

# rename_rds() - to be used for renaming the source_db to old_db and the resized_db to source_db
def rename_rds(current_id, new_id, source_region):
    # Initialize RDS client
    rds_client = boto3.client('rds', region_name=source_region)

    try:
        logger.info(f"Updating RDS identifier name from {current_id} to {new_id}")
        # Modify the DB instance identifier
        update_db_id = rds_client.modify_db_instance(
            DBInstanceIdentifier=current_id,
            NewDBInstanceIdentifier=new_id,
            ApplyImmediately=True
        )
        logger.info(f"RDS identifier name update from {current_id} to {new_id} is pending reboot")

        logger.info("Waiting for updated instance to return from reboot, the script would pause for a five minutes")

        time.sleep(300)

        # Fresh lookup — this is the actual current state, taken AFTER the sleep
        renamed_db = rds_client.describe_db_instances(DBInstanceIdentifier=new_id)['DBInstances'][0]
        
        if renamed_db['DBInstanceStatus'] == "available":
            logger.info(f"RDS instance with ID: {current_id} has been renamed to {new_id} and is in Available state")
        else:
            raise RuntimeError(f"{new_id} is still in {renamed_db['DBInstanceStatus']}' state after sleep")

    except Exception as e:
        logger.error(f"Updating RDS identifier from {current_id} to {new_id} encountered an error: {str(e)}")
        raise

    return renamed_db

def swap_db(source_db_info, resized_db_dict, source_region):

    # Rename source DB to old_db
    logger.info(f"Renaming {source_db_info['DBInstanceIdentifier']} to {source_db_info['DBInstanceIdentifier']}-old")

    orig_to_old = rename_rds(source_db_info['DBInstanceIdentifier'], f"{source_db_info['DBInstanceIdentifier']}-old", source_region)

    # Rename new resized DB to source DB
    logger.info(f"Renaming {resized_db_dict['DBInstanceIdentifier']} to {source_db_info['DBInstanceIdentifier']}")

    resized_to_source = rename_rds(resized_db_dict['DBInstanceIdentifier'], source_db_info['DBInstanceIdentifier'], source_region)

    return {"orig_renamed": orig_to_old, "resized_renamed": resized_to_source}


def stop_rds(source_db_info, source_region):

    # Initialize RDS client
    rds_client = boto3.client('rds', region_name=source_region)

    old_db_id = f"{source_db_info['DBInstanceIdentifier']}-old"

    # Stop the oversized DB instance
    stop_old_db = rds_client.stop_db_instance(
        DBInstanceIdentifier=old_db_id
    )

    stop_status = stop_old_db['DBInstance']['DBInstanceStatus']

    logger.info(f"Status of {old_db_id}: {stop_status}")

    return None


# Add inbound rule on the security group of the DB, allowing traffic from the runner of the script (EC2/ECS)
def allow_sgs(resized_db_dict, runner_sg_id, source_region):
    # Initialize the EC2 client
    ec2_client = boto3.client('ec2', region_name=source_region)

    db_sg_id = resized_db_dict['VpcSecurityGroups'][0]['VpcSecurityGroupId']

    try:
        logger.info("Checking whether the said security group/rule already exists. If not, creating one")
        allow_runner_rule = ec2_client.authorize_security_group_ingress(
            GroupId=db_sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 5432,
                    'ToPort': 5432,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': runner_sg_id,
                            'Description': 'Allow DB access from runner'
                        },
                    ],
                },
            ],
        )
    except ec2_client.exceptions.InvalidPermission.Duplicate as e:
        logger.info("Security group rule already exists")
        allow_runner_rule = None
    except Exception as e:
        logger.error(f"Creating security group rule encountered an error: {str(e)}")
        raise

    return allow_runner_rule




if __name__ == "__main__":
    db_info = sourcedbinfo("shrink-db", "us-east-1")
    free_storage = get_db_free_storage(db_info, "us-east-1")
    recommended_size = evaluate_db_storage(free_storage, db_info)
    logger.info(f"Original AllocatedStorage: {db_info['AllocatedStorage']} GB, Recommended: {recommended_size} GB")
    #new_db = create_new_db(db_info, "us-east-1", password_env_var="RDS_PASSWORD", revised_db_size=recommended_size)
    new_db = "new-shrink-db"  # reusing the instance that already exists
    new_db_dict = check_rds_availability("us-east-1", new_db, db_info, password_env_var="RDS_PASSWORD")