# running local code

```bash
# unzip input folder
tar -xvf ./data/input_folder.tar.gz -C ./data/

# install dependencies
python3 -m pip install --upgrade pip
pip install black
# rm -rf requirements.txt && pip install pipreqs && pipreqs .
pip install -r requirements.txt

# start server
python3 ./src/local/app.py

# start client
python3 ./src/local/client.py ./data/input_folder http://127.0.0.1:5000/api/object_detection
```

# deploying to aws

i. check your emails for "AWS academy", sign up

-   https://awsacademy.instructure.com/courses/82630/modules/items/7490502

ii. open your aws console:

-   ignore all tutorials, they're useless
-   `Courses` > `Modules` > `AWS Academy Learner Lab Resources` > `Launch AWS Academy Learner Lab` > `Start Lab`
-   wait until the lab is ready
-   click on `AWS Details`

```bash
brew install jq
brew install awscli

# ------------------------------------------------------------------ s3 stuff

# enter stuff based on what you read on `AWS Details`
aws configure

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

# ------------------------------------------------------------------ lambda stuff

# create demo lambda function
echo 'def lambda_handler(event, context): print(event)' > lambda_function.py
zip lambda_function.zip lambda_function.py

# note your own account id
aws sts get-caller-identity

# create a lambda function
# change `<YOUR ACCOUNT ID HERE>` with your own account id
# notice how we're using the existing `LabRole` role
aws lambda create-function --function-name my-function --runtime python3.8 --role arn:aws:iam::<YOUR ACCOUNT ID HERE>:role/LabRole --handler lambda_function.lambda_handler --zip-file fileb://lambda_function.zip

# invoke the lambda function and print the output
aws lambda invoke --function-name my-function response.json && rm -rf response.json

# show existing lambda functions
aws lambda list-functions | jq '.Functions[].FunctionName'

# delete the lambda function
aws lambda delete-function --function-name my-function
```

cli docs: https://docs.aws.amazon.com/cli/latest/

boto3 docs: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
