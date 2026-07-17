import boto3
import json
import os
from urllib.parse import unquote_plus
import subprocess
import logging
from download_db import download_db_from_s3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

queue_url = "https://sqs.us-east-1.amazonaws.com/067270456427/clamav-scanner-queue"
sns_topic_arn = "arn:aws:sns:us-east-1:067270456427:clamav-alerts"
sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/067270456427/clamav-scanner-queue"

# Create SQS client
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
sqs_client = boto3.client('sqs')
clean_bucket = 'clamav-clean-067270456427'

logger.info(f"Reading messages from SQS queue")
# Receive message from SQS queue
read_msg = sqs_client.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=10,
    WaitTimeSeconds=10
)
# Creating one loop, one message at a time, fully processed before moving to the next
for msg in read_msg.get('Messages', []):
    logger.info(f"Found one message in queue, extracting message body")
    receipt_handle = msg.get('ReceiptHandle')

    # Extract "Messages" > "Body" (Body is JSON format)
    ## Noticed that "Messages" is a list of dicts, but "Body" is a JSON itself
    body = msg.get('Body')
    parsed_body = json.loads(body)

    if not parsed_body.get('Records'):
        logger.info("Not a real S3 event, skipping")
        continue

    logger.info(f"Message body parsed successfully, extracting details of file to process")
    # Extract S3 bucket name and S3 object key from the output above

    for record in parsed_body.get('Records'):
        bucket = record.get('s3').get('bucket').get('name')
        obj_key = unquote_plus(record.get('s3').get('object').get('key'))
        if obj_key.endswith('/'):
            logger.info(f"Skipping folder placeholder object: {obj_key}, not a valid item to process further")
            continue
        #print(bucket)
        #print(obj_key)

        logger.info(f"Finished extracting file details from SQS message, preparing to download file from S3 bucket {bucket}")
        # Step: Download the file from S3
        current_folder = os.getcwd()
        local_file = os.path.basename(obj_key)
        local_file_path = os.path.join(current_folder, local_file)
        s3_client.download_file(bucket, obj_key, local_file_path)
        logger.info(f"File {obj_key} successfully downloaded locally")

        # Scan downloaded file, tag and route accordingly
        logger.info(f"Preparing to run clamscan scan on {obj_key}")
        scan_result = subprocess.run(
            ["clamscan", local_file_path],
            capture_output=True,
            text=True
        )
        if scan_result.returncode == 0:
            logger.info(f"The file {obj_key} is clean. Tagging the file as scanned and clean")
            response = s3_client.put_object_tagging(
                Bucket=bucket,
                Key=obj_key,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'FILES_SCANNED',
                            'Value': 'true' 
                        },
                        {
                            'Key': 'SCAN_RESULT',
                            'Value': 'CLEAN'
                        }
                    ]
                }
            )
            logger.info(f"Moving file {obj_key} to {clean_bucket}")
            copy_source = {
                'Bucket': bucket,
                'Key': obj_key
            }
            s3_client.copy(
                CopySource=copy_source,
                Bucket=clean_bucket,
                Key=obj_key
            )

        else:
            logger.info(f"File {obj_key} did not pass clamscan scan. Tagging the file as 'scanned' and 'dirty")
            response = s3_client.put_object_tagging(
                Bucket=bucket,
                Key=obj_key,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'FILES_SCANNED',
                            'Value': 'true' 
                        },
                        {
                            'Key': 'SCAN_RESULT',
                            'Value': 'DIRTY'
                        }
                    ]
                }
            )
            logger.info(f"File {obj_key} tagged successfully. Sending SNS notifcation")
            sns_alert = sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject='Infected file detected by Clamav',
                Message=f"Clamav detected an infected file {obj_key}"
            )
        logger.info(f"Finished processing message in SNS queue, deleting it from queue")
        # Delete processed SQS messages from queue
        del_sqs_response = sqs_client.delete_message(
            QueueUrl=sqs_queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.info(f"Deleted SQS message with receipt handle {receipt_handle}")