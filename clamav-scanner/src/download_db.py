import os
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

local_db_files_path = os.getenv("DATABASE_DIRECTORY", "/opt/homebrew/var/lib/clamav")
db_files = ["main.cvd", "daily.cvd", "bytecode.cvd"]
bucket_name = os.getenv("CLAMAV_DB_BUCKET_NAME", "clamav-db-067270456427")
bucket_path = os.getenv("CLAMAV_DB_BUCKET_PATH", "clamav")

def download_db_from_s3():
    s3_client = boto3.client('s3')
    failing_db_files = []
    for f in db_files:
        logger.info(f"Downloading {f} from {bucket_name}")
        try:
            s3_client.download_file(bucket_name, os.path.join(bucket_path, f), os.path.join(local_db_files_path, f))
            logger.info(f"Successfully downloaded {f}")
        except Exception as e:
            logger.error(f"Encountered error while downloading {f}: {str(e)}")
            failing_db_files.append(f)
            continue
    return failing_db_files