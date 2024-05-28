import requests
import base64
import json
import os
import uuid
import argparse
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(description="YOLO Object Detection Client")
    parser.add_argument("input_folder", type=str, help="Path to the input folder")
    parser.add_argument("endpoint", type=str, help="API endpoint")
    args = parser.parse_args()

    if not args.input_folder:
        parser.error("Invalid input folder")
    if not os.path.isdir(args.input_folder):
        parser.error("Invalid input folder")
    if not os.listdir(args.input_folder):
        parser.error("Input folder is empty")

    if not args.endpoint:
        parser.error("Invalid endpoint URL")
    if not args.endpoint.startswith("http"):
        parser.error("Invalid endpoint URL. It should start with http")

    return args


def encode_image(image_path) -> str:
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


if __name__ == "__main__":
    args = get_args()
    print(f"{args=}")

    for image_name in os.listdir(args.input_folder):
        if image_name.endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(args.input_folder, image_name)
            image_id = str(uuid.uuid4())
            image_data = encode_image(image_path)
            payload = {"id": image_id, "image_data": image_data}
            response = requests.post(args.endpoint, json=payload)

            assert response.status_code == 200, f"Status code: {response.status_code}"
            assert response.json()["id"] == image_id, f"Image ID mismatch for {image_id}"

            print(json.dumps(response.json(), indent=4))
