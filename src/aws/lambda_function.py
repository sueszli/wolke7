"""
content of this file is deployed as AWS Lambda function
"""

import boto3
import datetime
import json

TABLE_NAME = "wolke-sieben-table"


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
