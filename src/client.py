import requests
import base64
import json
import os
import uuid
import argparse


def get_args():
    parser = argparse.ArgumentParser(description="YOLO Object Detection")
    parser.add_argument("input_folder", help="Path to the input folder")
    parser.add_argument("endpoint", help="API endpoint")
    return parser.parse_args()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


def main(input_folder, endpoint):
    for image_name in os.listdir(input_folder):
        if image_name.endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(input_folder, image_name)
            image_id = str(uuid.uuid4())
            image_data = encode_image(image_path)
            payload = {"id": image_id, "image_data": image_data}
            response = requests.post(endpoint, json=payload)
            print(json.dumps(response.json(), indent=4))


if __name__ == "__main__":
    args = get_args()
    print(args)
    main(input_folder=args.input_folder, endpoint=args.endpoint)
