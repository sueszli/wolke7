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

# server:
# {
#   "id":"UUID (from client)", 
#   "objects": [ 
#       { 
#           "label": "...",  
#           "accuracy": ...
#       } 
#       ... 
#   ] 
# }
python3 ./src/server.py

# client:
# { 
#   "id": "UUID", 
#   "image_data": "base64_encoded_image" 
# } 
python3 ./src/client.py ./data/input_folder/ http://localhost:5000/api/object_detection