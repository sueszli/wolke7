"""
content of this file is deployed as AWS Lambda function
"""

import boto3
import datetime
import json
import cv2
import os

TABLE_NAME = "wolke-sieben-table"
BUCKET_NAME = "wolke-sieben-bucket-paul"  # Replace with your bucket name
S3_FOLDER = "yolo_tiny_configs/"
LOCAL_TMP_FOLDER = "/tmp/yolo_tiny_configs/"


def download_from_s3(bucket_name, s3_key, local_path):
    s3 = boto3.client("s3")
    s3.download_file(bucket_name, s3_key, local_path)
    print(f"Downloaded {s3_key} from bucket {bucket_name} to {local_path}")


def download_all_files_in_folder(bucket_name, s3_folder, local_folder):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_folder)

    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                s3_key = obj["Key"]
                relative_path = os.path.relpath(s3_key, s3_folder)
                local_path = os.path.join(local_folder, relative_path)
                local_dir = os.path.dirname(local_path)

                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)

                if not os.path.exists(local_path):
                    download_from_s3(bucket_name, s3_key, local_path)


# Ensure the local directory exists
if not os.path.exists(LOCAL_TMP_FOLDER):
    os.makedirs(LOCAL_TMP_FOLDER)

# Download all files in the specified S3 folder to /tmp when the container is initialized
download_all_files_in_folder(BUCKET_NAME, S3_FOLDER, LOCAL_TMP_FOLDER)


def main(event, context) -> dict:
    print("Lambda Function invoked with event:", event)
    output = {
        "args": event,
        "context": {
            "function_name": context.function_name,
            "function_version": context.function_version,
            "memory_limit_in_mb": context.memory_limit_in_mb,
            "time_remaining_in_millis": context.get_remaining_time_in_millis(),
            "aws_request_id": context.aws_request_id,
            "log_group_name": context.log_group_name,
        },
    }

    # Extract S3 event details
    if "Records" in event and len(event["Records"]) > 0:
        s3_event = event["Records"][0]["s3"]
        bucket_name = s3_event["bucket"]["name"]
        object_key = s3_event["object"]["key"]
        output["s3"] = {
            "bucket_name": bucket_name,
            "object_key": object_key,
        }

    # Write output to DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)
    res = table.put_item(
        Item={
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "S3 Event Processed",  # Log message
            **output,
        }
    )
    assert res["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

    # Return output as json
    return output
