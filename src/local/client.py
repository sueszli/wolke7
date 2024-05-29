import requests
import base64
import json
import os
import uuid
import argparse
import time


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

    total_transfer_time = 0
    total_inference_time = 0
    num_images = 0

    for image_name in os.listdir(args.input_folder):
        if image_name.endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(args.input_folder, image_name)
            image_id = str(uuid.uuid4())
            image_data = encode_image(image_path)
            payload = {"id": image_id, "image_data": image_data}

            start_transfer_time = time.time()
            response = requests.post(f"{args.endpoint}/object_detection", json=payload)
            end_transfer_time = time.time()
            transfer_time = end_transfer_time - start_transfer_time

            assert response.status_code == 200, f"Status code: {response.status_code}"
            assert response.json()["id"] == image_id, f"Image ID mismatch for {image_id}"

            response_data = response.json()
            print(json.dumps(response_data, indent=4))

            inference_time = response_data["inference_time"]
            total_transfer_time += transfer_time
            total_inference_time += inference_time
            num_images += 1

            print(json.dumps(response_data, indent=4))
            print(f"Transfer Time: {transfer_time:.4f} seconds")
            print(f"Inference Time: {inference_time:.4f} seconds")

    print("\n\n**** Local Execution Summary ****")
    print(f"Total Transfer Time: {total_transfer_time:.4f} seconds")
    if num_images > 0:
        avg_transfer_time = total_transfer_time / num_images
        avg_inference_time = total_inference_time / num_images
        print(f"Average Transfer Time: {avg_transfer_time:.4f} seconds")
        print(f"Average Inference Time: {avg_inference_time:.4f} seconds")

    # Fetch system info
    response = requests.get(f"{args.endpoint}/system_info")
    assert response.status_code == 200, f"Status code: {response.status_code}"

    system_info = response.json()
    print("System Information:", json.dumps(system_info, indent=4))
