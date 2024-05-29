import boto3
from pathlib import Path
from colorama import Fore, Style
from tqdm import tqdm


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


def upload_file(bucket_name, file_path):
    print(f"{Fore.GREEN}uploading file {file_path} to bucket {bucket_name}{Style.RESET_ALL}")

    s3 = boto3.client("s3")
    s3.upload_file(str(file_path), bucket_name, file_path.name)
    print(f"successfully uploaded file {file_path} to bucket {bucket_name}")


def upload_folder(bucket_name, folder_path):
    print(f"{Fore.GREEN}uploading folder {folder_path} to bucket {bucket_name}{Style.RESET_ALL}")

    s3 = boto3.client("s3")

    def upload_file(bucket_name, file_path):
        key = file_path.relative_to(folder_path)
        s3.upload_file(str(file_path), bucket_name, str(key))

    for file_path in tqdm(folder_path.rglob("*")):
        if file_path.is_file():
            upload_file(bucket_name, file_path)

    print(f"successfully uploaded folder {folder_path} to bucket {bucket_name}")


def delete_bucket(bucket_name):
    print(f"{Fore.GREEN}deleting bucket {bucket_name}{Style.RESET_ALL}")

    s3 = boto3.client("s3")

    response = s3.list_objects_v2(Bucket=bucket_name)
    if response["KeyCount"] > 0:
        s3.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": obj["Key"]} for obj in response["Contents"]]})

    s3.delete_bucket(Bucket=bucket_name)
    print(f"successfully deleted bucket {bucket_name}")


if __name__ == "__main__":
    """
    # create a bucket
    aws s3api create-bucket --bucket wolke-sieben --region us-east-1

    # show buckets and objects
    aws s3api list-buckets
    aws s3api list-objects --bucket wolke-sieben

    # upload a directory
    aws s3 cp ./data/input_folder s3://wolke-sieben/input_folder --recursive

    # empty bucket and delete it
    aws s3 rm s3://wolke-sieben --recursive
    aws s3api delete-bucket --bucket wolke-sieben
    """

    bucket_name = "wolke-sieben"

    create_bucket(bucket_name)
    list_buckets()

    datapath = Path.cwd() / "data" / "input_folder"
    upload_folder(bucket_name, datapath)
    list_buckets()

    delete_bucket(bucket_name)
    list_buckets()
