import boto3
from botocore.exceptions import ClientError
from botocore import exceptions as botocore
from botocore.response import StreamingBody

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


class LambdaClient:
    c = boto3.client("lambda")

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
    def create_lambda(lambda_name: str, file_path: Path) -> None:
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
            print(f"created lambda zip")
            return zip_file_path

        zip_file_path = zip_file(file_path)

        with open(zip_file_path, "rb") as f:
            accountid = boto3.client("sts").get_caller_identity()["Account"]
            role = "LabRole"
            response = LambdaClient.c.create_function(
                FunctionName=lambda_name,
                Runtime="python3.8",
                Role=f"arn:aws:iam::{accountid}:role/{role}",
                Handler="lambda_function.main",
                Code={"ZipFile": f.read()},
            )
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2
        print(json.dumps(response, indent=2))

        assert LambdaClient.lambda_exists(lambda_name)

    @staticmethod
    def invoke_lambda(lambda_name: str) -> None:
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

        # TODO: customize payload
        payload = {"hello": "world"}
        response = LambdaClient.c.invoke(FunctionName=lambda_name, Payload=json.dumps(payload))

        decoded_response = json.loads(response["Payload"].read().decode("utf-8"))
        print(json.dumps(decoded_response, indent=2))


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
    def upload_file(bucket_name: str, file_path: Path) -> None:
        print(f"{Fore.GREEN}uploading file {file_path} to bucket {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)
        assert file_path.exists()

        S3Client.c.upload_file(str(file_path), bucket_name, file_path.name)

    @staticmethod
    def upload_folder(bucket_name: str, folder_path: Path) -> None:
        print(f"{Fore.GREEN}uploading folder {folder_path} to bucket {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)

        for file_path in tqdm(folder_path.rglob("*")):
            if file_path.is_file():
                upload_path = file_path.relative_to(folder_path)
                S3Client.c.upload_file(str(file_path), bucket_name, str(upload_path))


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

        args = {
            "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        }
        response = DynamoDBClient.c.create_table(TableName=table_name, **args)
        assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2

        # wait for status to change to active
        while True:
            response = DynamoDBClient.c.describe_table(TableName=table_name)
            if response["Table"]["TableStatus"] == "ACTIVE":
                break
            time.sleep(1)

        print(json.dumps(response, cls=DateTimeEncoder, indent=2))
        assert DynamoDBClient.table_exists(table_name)


def hook_lambda_to_s3(lambda_name: str, bucket_name: str) -> None:
    print(f"{Fore.GREEN}hooking lambda function {lambda_name} to bucket {bucket_name}{Style.RESET_ALL}")

    lambda_client = boto3.client("lambda")
    s3_client = boto3.client("s3")
    account_id = boto3.client("sts").get_caller_identity()["Account"]

    lambda_client.add_permission(
        FunctionName=lambda_name,
        StatementId="s3-invoke-lambda-statement",
        Action="lambda:InvokeFunction",
        Principal="s3.amazonaws.com",
        SourceArn=f"arn:aws:s3:::{bucket_name}",
    )

    region = boto3.session.Session().region_name  # type: ignore
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": f"arn:aws:lambda:{region}:{account_id}:function:{lambda_name}",
                    "Events": ["s3:ObjectCreated:*"],
                }
            ]
        },
    )

    response = s3_client.get_bucket_notification_configuration(Bucket=bucket_name)
    print(json.dumps(response, indent=2))
    assert response["ResponseMetadata"]["HTTPStatusCode"] // 100 == 2


# if __name__ == "__main__":
#     assert_user_authenticated()

#     lambda_name = "wolke-sieben-lambda"
#     lambda_path = Path.cwd() / "src" / "aws" / "lambda_function.py"

#     bucket_name = "wolke-sieben-bucket"
#     data_path = Path.cwd() / "data" / "input_folder"

#     table_name = "wolke-sieben-table"

#     # create services
#     LambdaClient.create_lambda(lambda_name, lambda_path)
#     S3Client.create_bucket(bucket_name)
#     DynamoDBClient.create_table(table_name)

#     # list services
#     LambdaClient.list_lambdas()
#     S3Client.list_buckets()
#     DynamoDBClient.list_tables()

#     # hook lambda to s3
#     # hook lambda to dynamodb
#     # invoke and test whether results are stored in dynamodb

#     #     # trigger lambda
#     #     random_file = next(datapath.rglob("*"))
#     #     S3Client.upload_file(bucket_name, random_file)

#     # delete services
#     DynamoDBClient.delete_table(table_name)
#     S3Client.delete_bucket(bucket_name)
#     LambdaClient.delete_lambda(lambda_name, lambda_path)


if __name__ == "__main__":
    assert_user_authenticated()

    table_name = "wolke-sieben-table"
    DynamoDBClient.create_table(table_name)

    DynamoDBClient.list_tables()

    DynamoDBClient.delete_table(table_name)
