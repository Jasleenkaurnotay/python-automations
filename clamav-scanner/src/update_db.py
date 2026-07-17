import os
import boto3
from botocore.exceptions import ClientError
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client('s3')

db_files_path = os.getenv("DATABASE_DIRECTORY", "/opt/homebrew/var/lib/clamav")
db_files_ext = ".cvd"
bucket_name = os.getenv("CLAMAV_DB_BUCKET_NAME", "clamav-db-067270456427")
bucket_path = os.getenv("CLAMAV_DB_BUCKET_PATH", "clamav")

def update_db_in_s3():
    try:
        download_latest_db = subprocess.run(
            ["freshclam"],
            capture_output=True,
            text=True
        )
        if download_latest_db.returncode == 0:
            logger.info(f"New database files downloaded successfully")
        else:
            logger.error(f"Freshclam refresh failed")
    except Exception as e:
        logger.error(f"Downloading fresh databases errored out: {str(e)}")

    db_files = []
    for f in os.listdir(db_files_path):
        if f.endswith(db_files_ext):
            db_files.append(f)
            logger.info(f"Found database files {f} in {db_files_path}")
        #print(db_files)
    if not db_files:
        logger.error(f"No {db_files_ext} files found in {db_files_path}, nothing to upload")

    file_fail_to_upload = []
    for file in db_files:
        try:   
            s3_client.upload_file(os.path.join(db_files_path, file), bucket_name, os.path.join(bucket_path, file))
            logger.info(f"{file} uploaded successfully to {bucket_name}")
        except Exception as e:
            file_fail_to_upload.append(file)
            logger.error(str(e))
            continue
    return file_fail_to_upload
