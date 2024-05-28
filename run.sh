# ------------------------------------------ untar data

tar -xvf ./data/input_folder.tar.gz -C ./data/

# ------------------------------------------ install deps

python3 -m pip install --upgrade pip

pip install black

# rm -rf requirements.txt
# pip install pipreqs
# pipreqs .
pip install -r requirements.txt

# ------------------------------------------ run program

# start server
python3 ./src/server.py

# start client
python3 ./src/client.py ./data/input_folder http://127.0.0.1:5000/api/object_detection
