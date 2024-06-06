import boto3
from botocore.exceptions import ClientError
from botocore import exceptions as botocore
from botocore.response import StreamingBody

import zipfile
import json
from pathlib import Path
from tqdm import tqdm
from colorama import Fore, Style


class LambdaClient:
    c = boto3.client("lambda")

    @staticmethod
    def lambda_exists(function_name: str) -> bool:
        existing_functions = LambdaClient.c.list_functions()["Functions"]
        for function in existing_functions:
            if function_name == function["FunctionName"]:
                return True
        return False

    @staticmethod
    def create_lambda(function_name: str, file_path: Path) -> None:
        print(f"{Fore.GREEN}creating lambda function {function_name}{Style.RESET_ALL}")
        assert not LambdaClient.lambda_exists(function_name)
        assert file_path.exists()
        assert file_path.suffix == ".py"
        assert file_path.stat().st_size > 0

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
                FunctionName=function_name,
                Runtime="python3.8",
                Role=f"arn:aws:iam::{accountid}:role/{role}",
                Handler="lambda_function.main",
                Code={"ZipFile": f.read()},
            )
        print(json.dumps(response, indent=2))

    @staticmethod
    def invoke_lambda(function_name):
        print(f"{Fore.GREEN}invoking lambda function {function_name}{Style.RESET_ALL}")
        assert LambdaClient.lambda_exists(function_name)

        def wait_until_ready(function_name):
            while True:
                try:
                    response = LambdaClient.c.get_function(FunctionName=function_name)
                    if response["Configuration"]["State"] == "Active":
                        break
                    print(f"waiting for lambda function {function_name} to be ready")
                except botocore.ClientError:
                    pass

        wait_until_ready(function_name)

        # todo: update this
        payload = {"hello": "world"}
        response = LambdaClient.c.invoke(FunctionName=function_name, Payload=json.dumps(payload))

        decoded_response = json.loads(response["Payload"].read().decode("utf-8"))
        print(json.dumps(decoded_response, indent=2))

    @staticmethod
    def list_lambdas():
        print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

        response = LambdaClient.c.list_functions()
        for function in response["Functions"]:
            print(f"\t{function['FunctionName']}")

    @staticmethod
    def delete_lambda(function_name, file_path):
        print(f"{Fore.GREEN}deleting lambda function {function_name}{Style.RESET_ALL}")
        assert LambdaClient.lambda_exists(function_name)
        assert file_path.exists()

        response = LambdaClient.c.delete_function(FunctionName=function_name)
        print(json.dumps(response, indent=2))

        def delete_zip(file_path):
            zip_file_path = file_path.with_suffix(".zip")
            assert zip_file_path.exists(), f"zip file {zip_file_path} does not exist"
            zip_file_path.unlink()
            print(f"deleted lambda zip")

        delete_zip(file_path)


class S3Client:
    c = boto3.client("s3")

    @staticmethod
    def bucket_exists(bucket_name: str) -> bool:
        response = S3Client.c.list_buckets()
        for bucket in response["Buckets"]:
            if bucket["Name"] == bucket_name:
                return True
        return False

    @staticmethod
    def create_bucket(bucket_name: str) -> None:
        print(f"{Fore.GREEN}creating bucket {bucket_name}{Style.RESET_ALL}")
        assert not S3Client.bucket_exists(bucket_name)

        S3Client.c.create_bucket(Bucket=bucket_name)
        print(f"created bucket {bucket_name}")

    @staticmethod
    def list_buckets() -> None:
        print(f"{Fore.GREEN}listing bucket content{Style.RESET_ALL}")

        response = S3Client.c.list_buckets()
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

    @staticmethod
    def delete_bucket(bucket_name: str) -> None:
        print(f"{Fore.GREEN}deleting bucket {bucket_name}{Style.RESET_ALL}")
        assert S3Client.bucket_exists(bucket_name)

        response = S3Client.c.list_objects_v2(Bucket=bucket_name)
        if response["KeyCount"] > 0:
            S3Client.c.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": obj["Key"]} for obj in response["Contents"]]})
        S3Client.c.delete_bucket(Bucket=bucket_name)


def assert_user_authenticated():
    sts = boto3.client("sts")
    assert sts.get_caller_identity(), "unable to authenticate"

    uid = sts.get_caller_identity()["Account"]
    secret = boto3.session.Session().get_credentials().secret_key
    access = boto3.session.Session().get_credentials().access_key
    session = boto3.session.Session().get_credentials().token
    region = boto3.session.Session().region_name
    assert uid and secret and access and session, "credentials must be set"
    assert region == "us-east-1", "region must be set to us-east-1"
    # print(f"credentials:\n\tacc id: {uid}\n\tsecret: {secret}\n\taccess: {access}\n\tsession: {session}\n\tnregion: {region}\n")

    try:
        ec2 = boto3.client("ec2")
        _ = ec2.describe_instances()
    except ClientError as e:
        print(f"{Fore.RED}ec2 instance not accessible - start lab, update credentials{Style.RESET_ALL}")
        exit(1)


def hook_lambda_to_s3(function_name, bucket_name):
    print(f"{Fore.GREEN}hooking lambda function {function_name} to bucket {bucket_name}{Style.RESET_ALL}")

    client = boto3.client("s3")

    def assert_exists(bucket_name):
        response = client.list_buckets()
        for bucket in response["Buckets"]:
            if bucket_name == bucket["Name"]:
                return
        assert False, f"bucket {bucket_name} does not exist"


if __name__ == "__main__":
    assert_user_authenticated()

    def demo_lambda():
        function_name = "wolke-sieben-lambda"
        file_path = Path.cwd() / "src" / "aws" / "lambda_function.py"
        LambdaClient.create_lambda(function_name, file_path)
        LambdaClient.list_lambdas()

        LambdaClient.invoke_lambda(function_name)

        LambdaClient.delete_lambda(function_name, file_path)
        LambdaClient.list_lambdas()

    def demo_s3():
        bucket_name = "wolke-sieben-bucket"

        S3Client.create_bucket(bucket_name)
        S3Client.list_buckets()

        datapath = Path.cwd() / "data" / "input_folder"
        S3Client.upload_folder(bucket_name, datapath)
        S3Client.list_buckets()

        S3Client.delete_bucket(bucket_name)
        S3Client.list_buckets()

    # 1. create bucket
    bucket_name = "wolke-sieben-bucket"
    S3Client.create_bucket(bucket_name)
    assert S3Client.bucket_exists(bucket_name)

    # 2. create lambda function
    function_name = "wolke-sieben-lambda"
    file_path = Path.cwd() / "src" / "aws" / "lambda_function.py"
    LambdaClient.create_lambda(function_name, file_path)
    assert LambdaClient.lambda_exists(function_name)

    # 3. hook up lambda function to s3 bucket

    # 4. upload file to s3 bucket and trigger lambda function

    # 5. delete bucket
    S3Client.delete_bucket(bucket_name)
    assert not S3Client.bucket_exists(bucket_name)

    # 6. delete lambda function
    LambdaClient.delete_lambda(function_name, file_path)
    assert not LambdaClient.lambda_exists(function_name)
