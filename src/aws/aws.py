import boto3
from botocore.exceptions import ClientError
from botocore import exceptions as botocore
from botocore.response import StreamingBody

import zipfile
import json
from pathlib import Path
from tqdm import tqdm
from colorama import Fore, Style


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


class LambdaClient:
    @staticmethod
    def create_lambda_function(function_name, file_path):
        print(f"{Fore.GREEN}creating lambda function {function_name}{Style.RESET_ALL}")

        client = boto3.client("lambda")
        accountid = boto3.client("sts").get_caller_identity()["Account"]
        role = "LabRole"

        def lambda_function_exists(function_name):
            existing_functions = client.list_functions()["Functions"]
            for function in existing_functions:
                if function_name == function["FunctionName"]:
                    return True
            return False

        if lambda_function_exists(function_name):
            print(f"lambda function {function_name} already exists")
            return

        def get_lambda_zip_file(file_path):
            assert file_path.exists(), f"file {file_path} does not exist"
            assert file_path.suffix == ".py", f"file {file_path} must have .py extension"
            assert file_path.stat().st_size > 0, f"file {file_path} must not be empty"

            zip_file_path = file_path.with_suffix(".zip")
            if zip_file_path.exists():
                zip_file_path.unlink()
                print(f"deleted lambda zip")

            with zipfile.ZipFile(zip_file_path, "w") as z:
                z.write(file_path, file_path.name)
            print(f"created lambda zip")
            return zip_file_path

        zip_file_path = get_lambda_zip_file(file_path)

        with open(zip_file_path, "rb") as f:
            response = client.create_function(
                FunctionName=function_name,
                Runtime="python3.8",
                Role=f"arn:aws:iam::{accountid}:role/{role}",
                Handler="lambda_function.main",
                Code={"ZipFile": f.read()},
            )
        print(json.dumps(response, indent=2))

        print(f"created lambda function {function_name}")

    @staticmethod
    def invoke_lambda_function(function_name):
        print(f"{Fore.GREEN}invoking lambda function {function_name}{Style.RESET_ALL}")

        client = boto3.client("lambda")

        def assert_exists(function_name):
            existing_functions = client.list_functions()["Functions"]
            for function in existing_functions:
                if function_name == function["FunctionName"]:
                    return
            assert False, f"lambda function {function_name} does not exist"

        def wait_until_ready(function_name):
            while True:
                try:
                    response = client.get_function(FunctionName=function_name)
                    if response["Configuration"]["State"] == "Active":
                        break
                    print(f"waiting for lambda function {function_name} to be ready")
                except botocore.ClientError:
                    pass

        assert_exists(function_name)
        wait_until_ready(function_name)

        # todo: update this
        payload = {"hello": "world"}
        response = client.invoke(FunctionName=function_name, Payload=json.dumps(payload))

        decoded_response = json.loads(response["Payload"].read().decode("utf-8"))
        print(json.dumps(decoded_response, indent=2))

    @staticmethod
    def list_lambda_functions():
        print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

        client = boto3.client("lambda")
        response = client.list_functions()
        for function in response["Functions"]:
            print(f"\t{function['FunctionName']}")

    @staticmethod
    def delete_lambda_function(function_name, file_path):
        print(f"{Fore.GREEN}deleting lambda function {function_name}{Style.RESET_ALL}")

        client = boto3.client("lambda")
        response = client.delete_function(FunctionName=function_name)
        print(json.dumps(response, indent=2))

        zip_file_path = file_path.with_suffix(".zip")
        assert zip_file_path.exists(), f"zip file {zip_file_path} does not exist"
        zip_file_path.unlink()
        print(f"deleted lambda zip")


class S3Client:
    @staticmethod
    def create_bucket(bucket_name):
        print(f"{Fore.GREEN}creating bucket {bucket_name}{Style.RESET_ALL}")
        s3 = boto3.client("s3")

        def bucket_exists(bucket_name):
            response = s3.list_buckets()
            for bucket in response["Buckets"]:
                if bucket["Name"] == bucket_name:
                    return True
            return False

        if bucket_exists(bucket_name):
            print(f"bucket {bucket_name} already exists")
            return

        s3.create_bucket(Bucket=bucket_name)
        print(f"created bucket {bucket_name}")

    @staticmethod
    def list_buckets():
        print(f"{Fore.GREEN}listing bucket content{Style.RESET_ALL}")
        s3 = boto3.client("s3")
        response = s3.list_buckets()

        if len(response["Buckets"]) == 0:
            print("no buckets")
            return

        for bucket in response["Buckets"]:
            print(bucket["Name"])

            response = s3.list_objects_v2(Bucket=bucket["Name"])
            if response["KeyCount"] > 0:
                for obj in response["Contents"]:
                    print(f"\t{obj['Key']}")
            else:
                print("\tempty")

    @staticmethod
    def upload_file(bucket_name, file_path):
        print(f"{Fore.GREEN}uploading file {file_path} to bucket {bucket_name}{Style.RESET_ALL}")
        s3 = boto3.client("s3")
        s3.upload_file(str(file_path), bucket_name, file_path.name)
        print(f"successfully uploaded file {file_path} to bucket {bucket_name}")

    @staticmethod
    def upload_folder(bucket_name, folder_path):
        print(f"{Fore.GREEN}uploading folder {folder_path} to bucket {bucket_name}{Style.RESET_ALL}")
        s3 = boto3.client("s3")

        def _upload_file(bucket_name, file_path):
            key = file_path.relative_to(folder_path)
            s3.upload_file(str(file_path), bucket_name, str(key))

        for file_path in tqdm(folder_path.rglob("*")):
            if file_path.is_file():
                _upload_file(bucket_name, file_path)

        print(f"successfully uploaded folder {folder_path} to bucket {bucket_name}")

    @staticmethod
    def delete_bucket(bucket_name):
        print(f"{Fore.GREEN}deleting bucket {bucket_name}{Style.RESET_ALL}")
        s3 = boto3.client("s3")

        response = s3.list_objects_v2(Bucket=bucket_name)
        if response["KeyCount"] > 0:
            s3.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": obj["Key"]} for obj in response["Contents"]]})

        s3.delete_bucket(Bucket=bucket_name)
        print(f"successfully deleted bucket {bucket_name}")


if __name__ == "__main__":
    assert_user_authenticated()

    def demo_lambda():
        function_name = "wolke-sieben-lambda"
        file_path = Path.cwd() / "src" / "aws" / "lambda_function.py"
        LambdaClient.create_lambda_function(function_name, file_path)
        LambdaClient.list_lambda_functions()

        LambdaClient.invoke_lambda_function(function_name)

        LambdaClient.delete_lambda_function(function_name, file_path)
        LambdaClient.list_lambda_functions()

    def demo_s3():
        bucket_name = "wolke-sieben-bucket"

        S3Client.create_bucket(bucket_name)
        S3Client.list_buckets()

        datapath = Path.cwd() / "data" / "input_folder"
        S3Client.upload_folder(bucket_name, datapath)
        S3Client.list_buckets()

        S3Client.delete_bucket(bucket_name)
        S3Client.list_buckets()
