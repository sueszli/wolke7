from flask import Flask, request, jsonify, render_template_string
import base64
import cv2
import numpy as np
import time
import psutil
import GPUtil
from pathlib import Path
import requests
import pdb

app = Flask(__name__)


class ObjectDetection:
    def __init__(self):
        self.MODEL_CONFIG = Path.cwd() / "yolo_tiny_configs" / "yolov3-tiny.cfg"
        self.MODEL_WEIGHTS = Path.cwd() / "yolo_tiny_configs" / "yolov3-tiny.weights"
        self.COCO_NAMES = Path.cwd() / "yolo_tiny_configs" / "coco.names"

        self.net = cv2.dnn.readNet(str(self.MODEL_WEIGHTS), str(self.MODEL_CONFIG))

        # Check if CUDA is available and set the preferable backend and target
        # Note: could not get the openCV running on CUDA
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            print("CUDA is available. Using GPU.")
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        else:
            print("CUDA is not available. Using CPU.")
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        with open(self.COCO_NAMES, "r") as f:
            self.classes = [line.strip() for line in f.readlines()]

        self.output_layers = self.net.getUnconnectedOutLayersNames()

    def detect_objects(self, image_data, confidence_threshold=0.5, return_image=False):
        # Convert to a numpy array and decode to an image
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height, width, _ = img.shape

        # Prepare the image for YOLO
        blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

        # Run the YOLO network
        self.net.setInput(blob)
        start_time = time.time()
        outs = self.net.forward(self.output_layers)
        end_time = time.time()
        inference_time = end_time - start_time

        class_ids = []
        confidences = []
        boxes = []

        # Extract the bounding boxes, confidences, and class IDs
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                # filter out low confidence detections
                if confidence > confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, 0.4)

        detected_objects = []
        if len(indexes) > 0:
            COLORS = np.random.randint(0, 255, size=(len(self.classes), 3))
            for i in indexes:
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                if confidence > confidence_threshold:
                    detected_objects.append({"label": label, "accuracy": confidence})

                    if return_image:
                        (x, y) = (boxes[i][0], boxes[i][1])
                        (w, h) = (boxes[i][2], boxes[i][3])
                        color = COLORS[class_ids[i]].tolist()
                        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                        text = "{}: {:.4f}".format(label, confidence)
                        cv2.putText(img, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Encode the image to return
        img_base64 = None
        if return_image:
            _, img_encoded = cv2.imencode(".jpg", img)
            img_base64 = base64.b64encode(img_encoded).decode("utf-8")

        return detected_objects, inference_time, img_base64


detector = ObjectDetection()


@app.route("/api/object_detection", methods=["POST"])
def object_detection():
    try:
        data = request.get_json()
        img_id = data["id"]
        img_data = base64.b64decode(data["image_data"])
        confidence_threshold = data.get("confidence", 0.5)
        return_image = data.get("return_image", False)
        detected_objects, inference_time, img_base64 = detector.detect_objects(img_data, confidence_threshold, return_image)
        if return_image:
            return jsonify({"id": img_id, "objects": detected_objects, "inference_time": inference_time, "image": img_base64})
        else:
            return jsonify({"id": img_id, "objects": detected_objects, "inference_time": inference_time})
    except Exception as e:
        return jsonify({"error": "An error occurred during object detection", "details": str(e)}), 500


@app.route("/api/system_info", methods=["GET"])
def system_info():
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "max_frequency": psutil.cpu_freq().max,
        "min_frequency": psutil.cpu_freq().min,
        "current_frequency": psutil.cpu_freq().current,
        "cpu_usage": psutil.cpu_percent(interval=1),
    }

    gpus = GPUtil.getGPUs()
    gpu_info = []
    for gpu in gpus:
        gpu_info.append(
            {
                "id": gpu.id,
                "name": gpu.name,
                "load": gpu.load,
                "memory_free": gpu.memoryFree,
                "memory_used": gpu.memoryUsed,
                "memory_total": gpu.memoryTotal,
                "temperature": gpu.temperature,
                "driver_version": gpu.driver,
            }
        )

    net_info = {k: v._asdict() for k, v in psutil.net_if_stats().items()}

    return jsonify({"cpu_info": cpu_info, "gpu_info": gpu_info, "net_info": net_info})


@app.route("/api/debug", methods=["GET"])
def debug():
    """
    In order to debug the server side, you can use this endpoint to trigger a breakpoint in the server code by using pdb.set_trace() where you want to pause the execution and inspect the variables.

    To enable the debug mode just enter `http://127.0.0.1:5000/api/debug?image_path=data\input_folder\000000003111.jpg&confidence=0.2` where you can add the image_path and the confidence level as query parameters.

    It also returns the image with the detected objects.
    """
    image_path_param = request.args.get("image_path")
    confidence_param = request.args.get("confidence", default=0.3, type=float)

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    image_path = BASE_DIR / str(image_path_param)

    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {"id": "unique_image_id", "image_data": encoded_image, "confidence": confidence_param, "return_image": True}

        url = "http://127.0.0.1:5000/api/object_detection"
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            return jsonify({"error": f"Request failed with status code {response.status_code}"}), response.status_code

        print("Response Text:", response.text)

        response_data = response.json()
        img_base64 = response_data.get("image")

        html_content = f"""
        <html>
        <body>
            <h1>Object Detection Result</h1>
            <img src="data:image/jpeg;base64,{img_base64}" alt="Detected Objects">
        </body>
        </html>
        """
        return render_template_string(html_content)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except requests.exceptions.JSONDecodeError as e:
        return jsonify({"error": "Failed to decode JSON response", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
