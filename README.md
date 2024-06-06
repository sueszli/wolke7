# running local code

```bash
# unzip input folder
tar -xvf ./data/input_folder.tar.gz -C ./data/

# install dependencies
python3 -m pip install --upgrade pip
pip install black
# rm -rf requirements.txt && pip install pipreqs && pipreqs .
pip install -r requirements.txt

# start client and server locally
python3 ./src/local/server.py
python3 ./src/local/client.py ./data/input_folder http://127.0.0.1:5000/api
```

# deploying to aws

i. sign up through the email you received from "AWS academy"

ii. open up your aws console:

-   ignore all tutorials, they're useless
-   open `Courses` > `Modules` > `AWS Academy Learner Lab Resources` > `Launch AWS Academy Learner Lab` > `Start Lab`
    -   see: https://awsacademy.instructure.com/courses/82630/modules/items/7490502
-   wait until the lab is ready
-   click on `AWS Details`

store your aws credentials from "AWS Details" in `~/.aws/credentials` or run `aws configure`:

```bash
brew install awscli
aws configure
```

iii. use the cli or boto3 to access aws services:

-   cli docs: https://docs.aws.amazon.com/cli/latest/
-   boto3 docs: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

```bash
python3 ./src/aws/<...>.py
```
