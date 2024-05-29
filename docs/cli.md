# s3

```bash
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
```

# lambda

```bash
brew install jq

# create demo lambda function
echo 'def lambda_handler(event, context): print(event)' > lambda_function.py
zip lambda_function.zip lambda_function.py

# note your own account id
aws sts get-caller-identity --output json

# create a lambda function
# change `<YOUR ACCOUNT ID HERE>` with your own account id
# notice how we're using the existing `LabRole` role
aws lambda create-function --function-name my-function --runtime python3.8 --role arn:aws:iam::<YOUR ACCOUNT ID HERE>:role/LabRole --handler lambda_function.lambda_handler --zip-file fileb://lambda_function.zip --output json

# invoke the lambda function without any arguments and print the output as json
aws lambda invoke --function-name my-function --output json /dev/stdout

# show existing lambda functions
aws lambda list-functions --output json | jq '.Functions[].FunctionName'

# delete the lambda function
aws lambda delete-function --function-name my-function --output json
```
