import os
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_files_path = "/opt/homebrew/var/lib/clamav"
db_files_ext = ".cvd"
bucket_name = "clamav-db-067270456427"
bucket_path = "clamav"

db_files = []
for f in os.listdir(db_files_path):
    if f.endswith(db_files_ext):
        db_files.append(f)
print(db_files)

s3_client = boto3.client('s3')
try:
    for file in db_files:
        upload_db_files = s3_client.upload_file(os.path.join(db_files_path, file), bucket_name, os.path.join(bucket_path, file))
        logger.info(f"{file} uploaded successfully to {bucket_name}")
except ClientError as e:
    logger.error(str(e))
