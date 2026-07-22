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
start_time = datetime.now(datetime.timezone.utc) - timedelta(days=2)
end_time = datetime.now(datetime.timezone.utc)

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
cw_client = boto3.client('cloudwatch', region_name=source_region)

response = cw_client.get_metric_data(
    MetricDataQueries=[
        {
            'Id' : 'storage_utilized',
            'MetricStat': {
                'Metric': {
                    "Namespace": "AWS/RDS",
                    "MetricName": "FreeStorageSpace",
                    "Dimensions": [
                        {
                            "Name": "DBInstanceIdentifier", "Value": "shrink-db"
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
print(response)
