"""
content of this file is deployed as AWS Lambda function
"""

import boto3
import datetime
import json


def main(args, context) -> dict:
    assert args.get("table_name")
    table_name = args["table_name"]
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # write arbitrary data to DynamoDB
    response = table.put_item(
        Item={
            "id": "1",
            "hello": "world",
            "timestamp": datetime.datetime.now().isoformat(),
        }
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

    return {
        # echo input args for debugging
        # see: https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
        "args": dict(args),
        "context": {
            "function_name": context.function_name,
            "function_version": context.function_version,
            "memory_limit_in_mb": context.memory_limit_in_mb,
            "time_remaining_in_millis": context.get_remaining_time_in_millis(),
            "aws_request_id": context.aws_request_id,
            "log_group_name": context.log_group_name,
        },
    }
