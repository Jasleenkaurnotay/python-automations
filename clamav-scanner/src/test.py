import boto3
import json
import os
from urllib.parse import unquote_plus
import subprocess

queue_url = "https://sqs.us-east-1.amazonaws.com/067270456427/clamav-scanner-queue"

# Create SQS client
sqs_client = boto3.client('sqs')

# Receive message from SQS queue
read_msg = sqs_client.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=10,
    WaitTimeSeconds=10
)
# Creating one loop, one message at a time, fully processed before moving to the next
for msg in read_msg.get('Messages', []):
    receipt_handle = msg.get('ReceiptHandle')

    # Extract "Messages" > "Body" (Body is JSON format)
    ## Noticed that "Messages" is a list of dicts, but "Body" is a JSON itself
    body = msg.get('Body')
    parsed_body = json.loads(body)

    if not parsed_body.get('Records'):
        print("Not a real S3 event, skipping")
        continue


    # Extract S3 bucket name and S3 object key from the output above

    for record in parsed_body.get('Records'):
        bucket = record.get('s3').get('bucket').get('name')
        obj_key = unquote_plus(record.get('s3').get('object').get('key'))
        print(bucket)
        print(obj_key)
        print(receipt_handle)

        # Step: Download the file from S3
        s3_client = boto3.client('s3')

        current_folder = os.getcwd()
        local_file = os.path.basename(obj_key)
        local_file_path = os.path.join(current_folder, local_file)
        s3_client.download_file(bucket, obj_key, local_file_path)


    # Scan downloaded files
    scan_result = subprocess.run(
        ["clamscan", local_file_path],
        capture_output=True,
        text=True
    )
    if result.scan_result == 1:
        
    print(result.returncode)