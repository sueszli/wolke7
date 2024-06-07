"""
content of this file is deployed as AWS Lambda function
"""

import boto3
import datetime
import json

TABLE_NAME = "wolke-sieben-table"


def main(args, context) -> dict:

    output = {
        # useful for debugging
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

    # write output to dynamodb
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)  # type: ignore
    res = table.put_item(
        Item={
            "timestamp": datetime.datetime.now().isoformat(),
            **output,
        }
    )
    assert res["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

    # return output as json
    return output
