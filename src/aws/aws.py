import boto3
from botocore.exceptions import ClientError
from botocore import exceptions as botocore
from botocore.response import StreamingBody

from lambda_function import TABLE_NAME

import os
import zipfile
import json
from datetime import datetime
import time
from pathlib import Path
from tqdm import tqdm
from colorama import Fore, Style


def assert_user_authenticated():
    sts = boto3.client("sts")
    assert sts.get_caller_identity(), "unable to authenticate"

    uid = sts.get_caller_identity()["Account"]
    secret = boto3.session.Session().get_credentials().secret_key  # type: ignore
    access = boto3.session.Session().get_credentials().access_key  # type: ignore
    session = boto3.session.Session().get_credentials().token  # type: ignore
    region = boto3.session.Session().region_name  # type: ignore
    assert uid and secret and access and session, "credentials must be set"
    assert region == "us-east-1", "region must be set to us-east-1"
    # print(f"credentials:\n\tacc id: {uid}\n\tsecret: {secret}\n\taccess: {access}\n\tsession: {session}\n\tnregion: {region}\n")

    try:
        ec2 = boto3.client("ec2")
        _ = ec2.describe_instances()
    except ClientError as e:
        print(f"{Fore.RED}ec2 instance not accessible - start lab, update credentials{Style.RESET_ALL}")
        exit(1)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)


class S3Client:
    c = boto3.client("s3")

    @staticmethod
    def bucket_exists(bucket_name: str) -> bool:
        response = S3Client.c.list_buckets()
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        for bucket in response["Buckets"]:
            if bucket["Name"] == bucket_name:
                return True
        return False

    @staticmethod
    def list_buckets() -> None:
        print(f"{Fore.GREEN}listing bucket content{Style.RESET_ALL}")

        response = S3Client.c.list_buckets()
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        if len(response["Buckets"]) == 0:
            print("no buckets")
            return
        for bucket in response["Buckets"]:
            print(bucket["Name"])
            response = S3Client.c.list_objects_v2(Bucket=bucket["Name"])
            if response["KeyCount"] > 0:
                for obj in response["Contents"]:
                    print(f"\t{obj['Key']}")
            else:
                print("\tempty")

    @staticmethod
    def delete_bucket(bucket_name: str) -> None:
        print(f"{Fore.GREEN}deleting bucket {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)

        response = S3Client.c.list_objects_v2(Bucket=bucket_name)
        if response["KeyCount"] > 0:
            S3Client.c.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": obj["Key"]} for obj in response["Contents"]]})
        S3Client.c.delete_bucket(Bucket=bucket_name)

        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        assert not S3Client.bucket_exists(bucket_name)

    @staticmethod
    def create_bucket(bucket_name: str) -> None:
        print(f"{Fore.GREEN}creating bucket {bucket_name}{Style.RESET_ALL}")

        if S3Client.bucket_exists(bucket_name):
            print(f"bucket {bucket_name} already exists, deleting first")
            S3Client.delete_bucket(bucket_name)
            print(f"deleted existing bucket - back to creating")

        response = S3Client.c.create_bucket(Bucket=bucket_name)
        print(json.dumps(response, indent=2))

        assert S3Client.bucket_exists(bucket_name)

    @staticmethod
    def add_invoke_permission(lambda_arn: str, bucket_name: str) -> None:
        print(f"{Fore.GREEN}adding invoke permission for {bucket_name} to {lambda_arn}{Style.RESET_ALL}")

        statement_id = f"{bucket_name}-invoke-permission"

        try:
            policy = LambdaClient.c.get_policy(FunctionName=lambda_arn)
            policy_dict = json.loads(policy["Policy"])
            for statement in policy_dict["Statement"]:
                if statement["Sid"] == statement_id:
                    # If the permission exists, remove it
                    LambdaClient.c.remove_permission(FunctionName=lambda_arn, StatementId=statement_id)
                    break
        except LambdaClient.c.exceptions.ResourceNotFoundException:
            pass

        response = LambdaClient.c.add_permission(
            FunctionName=lambda_arn, StatementId=statement_id, Action="lambda:InvokeFunction", Principal="s3.amazonaws.com", SourceArn=f"arn:aws:s3:::{bucket_name}"
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        print(f"{Fore.GREEN}Invoke permission added for {bucket_name} to {lambda_arn}{Style.RESET_ALL}")
        # Print the resulting policy for debugging
        policy = LambdaClient.c.get_policy(FunctionName=lambda_arn)
        print(json.dumps(json.loads(policy["Policy"]), indent=2))

    @staticmethod
    def upload_file(bucket_name: str, file_path: Path) -> None:
        print(f"{Fore.GREEN}uploading file {file_path} to bucket {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)
        assert file_path.exists()

        S3Client.c.upload_file(str(file_path), bucket_name, file_path.name)

    @staticmethod
    def upload_folder(bucket_name: str, folder_path: Path, s3_directory: str = "") -> None:
        print(f"{Fore.GREEN}uploading folder {folder_path} to bucket {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)

        for file_path in tqdm(folder_path.rglob("*")):
            if file_path.is_file():
                relative_path = file_path.relative_to(folder_path)
                key = f"{s3_directory}/{relative_path}" if s3_directory else str(relative_path)

                S3Client.c.upload_file(str(file_path), bucket_name, key)

    @staticmethod
    def set_bucket_notification(bucket_name: str, lambda_function_arn: str) -> None:
        print(f"{Fore.GREEN}setting bucket notification for {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)

        response = S3Client.c.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration={
                "LambdaFunctionConfigurations": [
                    {
                        "LambdaFunctionArn": lambda_function_arn,
                        "Events": ["s3:ObjectCreated:*"],
                        "Filter": {
                            "Key": {
                                "FilterRules": [
                                    {"Name": "suffix", "Value": ".jpg"},
                                ]
                            }
                        },
                    },
                ]
            },
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

    @staticmethod
    def get_bucket_notification(bucket_name: str) -> None:
        response = S3Client.c.get_bucket_notification_configuration(Bucket=bucket_name)
        print(json.dumps(response, indent=2))


class DynamoDBClient:
    c = boto3.client("dynamodb")

    @staticmethod
    def table_exists(table_name: str) -> bool:
        response = DynamoDBClient.c.list_tables()
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        for table in response["TableNames"]:
            if table == table_name:
                return True
        return False

    @staticmethod
    def list_tables() -> None:
        print(f"{Fore.GREEN}listing tables{Style.RESET_ALL}")

        response = DynamoDBClient.c.list_tables()
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        if len(response["TableNames"]) == 0:
            print("no tables")
            return
        for table in response["TableNames"]:
            print(table)
            response = DynamoDBClient.c.scan(TableName=table)
            print(json.dumps(response, indent=2))

    @staticmethod
    def delete_table(table_name: str) -> None:
        print(f"{Fore.GREEN}deleting table {table_name}{Style.RESET_ALL}")
        assert DynamoDBClient.table_exists(table_name)

        # wait for users to stop using table
        while True:
            try:
                response = DynamoDBClient.c.delete_table(TableName=table_name)
                break
            except botocore.ClientError:
                pass
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        print(json.dumps(response, indent=2))

        # wait for table to be deleted
        max_wait = 5
        for _ in range(max_wait):
            if not DynamoDBClient.table_exists(table_name):
                break
            time.sleep(1)
        assert not DynamoDBClient.table_exists(table_name)

    @staticmethod
    def create_table(table_name: str) -> None:
        print(f"{Fore.GREEN}creating table {table_name}{Style.RESET_ALL}")

        if DynamoDBClient.table_exists(table_name):
            print(f"table {table_name} already exists, deleting first")
            DynamoDBClient.delete_table(table_name)
            print(f"deleted existing table - back to creating")

        # create table
        args = {
            "KeySchema": [{"AttributeName": "timestamp", "KeyType": "HASH"}],  # use timestamp as primary key
            "AttributeDefinitions": [{"AttributeName": "timestamp", "AttributeType": "S"}],
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},  # throughput: 5 reads and 5 writes per second
        }
        response = DynamoDBClient.c.create_table(TableName=table_name, **args)
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        # wait for creation to finish
        while True:
            response = DynamoDBClient.c.describe_table(TableName=table_name)
            if response["Table"]["TableStatus"] == "ACTIVE":
                break
            time.sleep(1)
        print(json.dumps(response, cls=DateTimeEncoder, indent=2))
        assert DynamoDBClient.table_exists(table_name)


class LambdaClient:
    c = boto3.client("lambda")
    iam = boto3.client("iam")

    @staticmethod
    def layer_exists(lambda_name: str) -> bool:
        existing_functions = LambdaClient.c.list_layers()["Layers"]
        for function in existing_functions:
            if lambda_name == function["LayerName"]:
                return True
        return False

    @staticmethod
    def lambda_exists(lambda_name: str) -> bool:
        existing_functions = LambdaClient.c.list_functions()["Functions"]
        for function in existing_functions:
            if lambda_name == function["FunctionName"]:
                return True
        return False

    @staticmethod
    def list_lambdas():
        print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

        response = LambdaClient.c.list_functions()
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        for function in response["Functions"]:
            print(f"\t{function['FunctionName']}")

    @staticmethod
    def delete_lambda(lambda_name: str, file_path: Path) -> None:
        print(f"{Fore.GREEN}deleting lambda function {lambda_name}{Style.RESET_ALL}")
        assert LambdaClient.lambda_exists(lambda_name)
        assert file_path.exists()

        response = LambdaClient.c.delete_function(FunctionName=lambda_name)
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        def delete_zip(file_path):
            zip_file_path = file_path.with_suffix(".zip")
            assert zip_file_path.exists(), f"zip file {zip_file_path} does not exist"
            zip_file_path.unlink()
            print(f"deleted lambda zip")

        delete_zip(file_path)

        assert not LambdaClient.lambda_exists(lambda_name)
        assert not file_path.with_suffix(".zip").exists()

    @staticmethod
    def __remove_permission(lambda_function_name: str, statement_id: str):
        try:
            policy = LambdaClient.c.get_policy(FunctionName=lambda_function_name)
            policy_dict = json.loads(policy["Policy"])
            for statement in policy_dict["Statement"]:
                if statement["Sid"] == statement_id:
                    response = LambdaClient.c.remove_permission(FunctionName=lambda_function_name, StatementId=statement_id)

                    if response["ResponseMetadata"]["HTTPStatusCode"] == 204:
                        print("Permission removed successfully.")
                    else:
                        print("Failed to remove permission.")
                    break
        except LambdaClient.c.exceptions.ResourceNotFoundException:
            print("No policy with the given statement ID exists.")

    @staticmethod
    def __add_invoke_permission(lambda_function_name: str, bucket_name: str):

        LambdaClient.__remove_permission(lambda_function_name, f"{bucket_name}-invoke-permission")

        response = LambdaClient.c.add_permission(
            FunctionName=lambda_function_name, StatementId=f"{bucket_name}-invoke-permission", Action="lambda:InvokeFunction", Principal="s3.amazonaws.com", SourceArn=f"arn:aws:s3:::{bucket_name}"
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

    @staticmethod
    def create_lambda(lambda_name: str, bucket_name: str, layer_name: str, file_path: Path) -> str:
        print(f"{Fore.GREEN}creating lambda function {lambda_name}{Style.RESET_ALL}")
        assert file_path.exists()
        assert file_path.suffix == ".py"
        assert file_path.stat().st_size > 0

        if LambdaClient.lambda_exists(lambda_name):
            print(f"lambda function {lambda_name} already exists, deleting first")
            LambdaClient.delete_lambda(lambda_name, file_path)
            print(f"deleted existing lambda function - back to creating")

        def zip_file(file_path: Path) -> Path:
            zip_file_path = file_path.with_suffix(".zip")
            if zip_file_path.exists():
                zip_file_path.unlink()
                print(f"deleted existing lambda zip")

            with zipfile.ZipFile(zip_file_path, "w") as z:
                z.write(file_path, file_path.name)
            os.chmod(file_path, 0o777)
            print(f"created lambda zip")
            return zip_file_path

        zip_file_path = zip_file(file_path)

        with open(zip_file_path, "rb") as f:
            accountid = boto3.client("sts").get_caller_identity()["Account"]
            role = "LabRole"
            response = LambdaClient.c.create_function(
                FunctionName=lambda_name,
                Runtime="python3.10",
                Role=f"arn:aws:iam::{accountid}:role/{role}",
                Handler="lambda_function.main",
                Code={"ZipFile": f.read()},
                Layers=[layer_name],
                Timeout=900,
                MemorySize=1024,
            )
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        print(json.dumps(response, indent=2))

        assert LambdaClient.lambda_exists(lambda_name)

        LambdaClient.__add_invoke_permission(lambda_name, bucket_name)

        return response["FunctionArn"]

    @staticmethod
    def delete_layer(layer_name: str) -> None:
        print(f"{Fore.GREEN}deleting lambda layer {layer_name}{Style.RESET_ALL}")
        assert LambdaClient.layer_exists(layer_name)

        response = LambdaClient.c.list_layer_versions(LayerName=layer_name)
        for version in response["LayerVersions"]:
            response = LambdaClient.c.delete_layer_version(LayerName=layer_name, VersionNumber=version["Version"])
            assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        assert not LambdaClient.layer_exists(layer_name)

    @staticmethod
    def publish_layer(layer_name: str, bucket_name: str, file_name: str) -> str:
        print(f"{Fore.GREEN}publishing lambda layer {layer_name}{Style.RESET_ALL}")

        if LambdaClient.layer_exists(layer_name):
            print(f"layer function {layer_name} already exists, deleting first")
            LambdaClient.delete_layer(layer_name)
            print(f"deleted existing layer function - back to creating")

        response = LambdaClient.c.publish_layer_version(
            LayerName=layer_name,
            Content={"S3Bucket": bucket_name, "S3Key": file_name},
            CompatibleRuntimes=["python3.10"],
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        print(json.dumps(response, indent=2))

        assert LambdaClient.layer_exists(layer_name)
        return response["LayerVersionArn"]

    @staticmethod
    def invoke_lambda(lambda_name: str, payload: dict) -> None:
        print(f"{Fore.GREEN}invoking lambda function {lambda_name}{Style.RESET_ALL}")
        assert LambdaClient.lambda_exists(lambda_name)

        def wait_until_ready(lambda_name):
            while True:
                try:
                    response = LambdaClient.c.get_function(FunctionName=lambda_name)
                    if response["Configuration"]["State"] == "Active":
                        break
                    print(f"waiting for lambda function {lambda_name} to be ready")
                except botocore.ClientError:
                    pass

        wait_until_ready(lambda_name)

        response = LambdaClient.c.invoke(FunctionName=lambda_name, Payload=json.dumps(payload))

        decoded_response = json.loads(response["Payload"].read().decode("utf-8"))
        print(json.dumps(decoded_response, indent=2))


if __name__ == "__main__":
    assert_user_authenticated()

    table_name = TABLE_NAME

    bucket_name = "wolke-sieben-bucket-raquel"
    data_path = Path.cwd() / "data" / "input_folder"

    layer_name = "wolke-sieben-layer"
    layer_path = Path.cwd() / "src" / "aws" / "packages.zip"

    lambda_name = "wolke-sieben-lambda"
    lambda_path = Path.cwd() / "src" / "aws" / "lambda_function.py"

    yolo_tiny_configs = Path.cwd() / "yolo_tiny_configs"

    # Create services
    DynamoDBClient.create_table(table_name)
    S3Client.create_bucket(bucket_name)

    # Upload dependencies to S3
    S3Client.upload_file(bucket_name, layer_path)
    layer_arn_name = LambdaClient.publish_layer(layer_name, bucket_name, layer_path.name)
    lambda_arn_name = LambdaClient.create_lambda(lambda_name, bucket_name, layer_arn_name, lambda_path)

    # Upload Model Configs
    S3Client.upload_folder(bucket_name, yolo_tiny_configs, yolo_tiny_configs.name)

    # Hooking up Lambda to S3
    S3Client.add_invoke_permission(lambda_arn_name, bucket_name)
    S3Client.set_bucket_notification(bucket_name, lambda_arn_name)
    S3Client.get_bucket_notification(bucket_name)

    # Invoke lambda with s3 event for each file in the data folder
    for file in data_path.rglob("*"):
        S3Client.upload_file(bucket_name, file)
       

    # Show results in dynamodb --> this doesn't work because it's async, results can be seen in the AWS console
    # DynamoDBClient.list_tables()

    # Do not delete resources, they are part of the submission
    """DynamoDBClient.delete_table(table_name)
    S3Client.delete_bucket(bucket_name)
    LambdaClient.delete_lambda(lambda_name, lambda_path)"""
