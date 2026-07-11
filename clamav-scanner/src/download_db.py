import os
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

local_db_files_path = "/opt/homebrew/var/lib/clamav"
db_files = ["main.cvd", "daily.cvd", "bytecode.cvd"]
bucket_name = "clamav-db-067270456427"
bucket_path = "clamav"

s3_client = boto3.client('s3')
for f in db_files:
    logger.info(f"Downloading {db_files} from {bucket_name}")
    try:
        s3_client.download_file(bucket_name, os.path.join(bucket_path, f), os.path.join(local_db_files_path, f))
        logger.info(f"Successfully downloaded {f}")
    except Exception as e:
        logger.error(f"Encountered error while {str(e)}")