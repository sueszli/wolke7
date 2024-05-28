# how to run

i. check your emails for "AWS academy", sign up

ii. open your aws console:

-   ignore all tutorials, they're useless
-   `Courses` > `Modules` > `AWS Academy Learner Lab Resources` > `Launch AWS Academy Learner Lab` > `Start Lab`
-   wait until the lab is ready
-   click on `AWS Details`

```bash
# install aws cli
brew install awscli

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
```
