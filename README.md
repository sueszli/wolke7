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

store your aws credentials from "AWS Details" in `~/.aws/credentials` or use `aws configure`:

```bash
brew install awscli
aws configure
```

iii. use the cli or boto3 to access aws services:

-   cli docs: https://docs.aws.amazon.com/cli/latest/
-   boto3 docs: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
