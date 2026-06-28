import boto3                # To speak with AWS APIs
import logging              # Used for Log formatting
import os                   # To read environment variables
from datetime import datetime, timezone             # To interpret dates

# Set logging level for production code
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Query environment variable
key_age = int(os.environ.get('EXPIRY_DAYS', 2))

# Initialize the IAM client
iam_client = boto3.client('iam')

# Step 1. Get all IAM users
def get_users():
    response = iam_client.list_users()          # Return type: dict
    logger.debug(response)

    # 2. We need to extract IAM user and access key from the above response
    user_names = []
    for user in response.get('Users', []):
        user_names.append(user.get('UserName'))
        logger.info(user_names)
        #print(type(user_names))
    return user_names

# 3. Query Access key for the said users
## This call needs to user username extracted in Step 2. Need to use for loop to go over the entire list of 
def get_access_keys(user_names):
    user_key_date = []
    for un in user_names:
        access_key = iam_client.list_access_keys(
            UserName=un
        )
        logger.debug(access_key)

        for metadata in access_key.get('AccessKeyMetadata', []):
            user_name = metadata.get('UserName')
            ak_id = metadata.get('AccessKeyId')
            date = metadata.get('CreateDate')
            # Calculate age of the access key
            current_date = datetime.now(timezone.utc)
            age = current_date - date
            logger.debug(age)
            user_key_date.append((user_name, ak_id, age.days))
    logger.debug(user_key_date)
    #print(type(user_key_date))
    return user_key_date

# 4. If age > 2 days -> add to delete list
## Loop over tuple to test deletion condition
def delete_key(user_key_date):
    for u in user_key_date:
        try:
            if u[2] > key_age:
                logger.info("Deleting access key {} for user {}".format(u[0], u[1]))
                key_delete = iam_client.delete_access_key(
                    UserName=u[0],
                    AccessKeyId=u[1]
                )
                logger.info("Successfully deleted access key {} for user {}".format(u[0], u[1]))
        except Exception as e:
            logger.error(str(e))
    return ()

def run():
    users = get_users()
    key_tuple = get_access_keys(users)
    delete_key(key_tuple)


def lambda_handler(event, context):
    try:
        run()
        return { 'statusCode' : 200, 'body' : "OK" }
    except Exception as e:
        return { 'statusCode' : 500, 'body' : str(e) }
