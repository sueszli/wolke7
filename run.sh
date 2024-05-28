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

