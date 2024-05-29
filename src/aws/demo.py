import boto3
from colorama import Fore, Style


# # enter stuff based on what you read on `AWS Details`
# aws configure

# # create a bucket
# aws s3api create-bucket --bucket wolke-sieben --region us-east-1

# # show buckets and objects
# aws s3api list-buckets
# aws s3api list-objects --bucket wolke-sieben

# # upload a directory
# aws s3 cp ./data/input_folder s3://wolke-sieben/input_folder --recursive

# # empty bucket and delete it
# aws s3 rm s3://wolke-sieben --recursive
# aws s3api delete-bucket --bucket wolke-sieben


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

    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "us-east-1"})
    print(f"created bucket {bucket_name}")


def list_buckets():
    s3 = boto3.client("s3")

    print(f"{Fore.GREEN}bucket content:{Style.RESET_ALL}")
    response = s3.list_buckets()
    for bucket in response["Buckets"]:
        print(bucket["Name"])

        response = s3.list_objects_v2(Bucket=bucket["Name"])
        if response["KeyCount"] == 0:
            print("\tempty")
        else:
            response = s3.list_objects_v2(Bucket=bucket["Name"])
            for obj in response["Contents"]:
                print(f"\t{obj['Key']}")

    print()


if __name__ == "__main__":
    bucket_name = "wolke-sieben"

    create_bucket(bucket_name)
    list_buckets()
