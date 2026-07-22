import boto3
from logger import logging

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
    except source_db_client.exceptions.DBInstanceNotFoundFault as e:
        logger.error(str(e))
        raise
    return source_db_info

sourcedbinfo(shrink-db)


## postgresql://myuser:mypassword@my-instance.abc123.us-east-1.rds.amazonaws.com:5432/mydb

