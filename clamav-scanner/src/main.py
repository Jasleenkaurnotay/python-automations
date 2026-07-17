import argparse
# import helper function
from helper import process_sqs_message
# Import upload db to s3
from update_db import update_db_in_s3

def main():
    # Request arguments from end user and decide which action to perform in the script
    parser = argparse.ArgumentParser(description="ClamAV scanner for S3 files")
    parser.add_argument("--action", choices=["scan", "update"], required=True)
    args = parser.parse_args()

    print(args.action)

    if args.action == "scan":
        process_sqs_message()
    elif args.action == "update":
        update_db_in_s3()

if __name__ == "__main__":
    main()