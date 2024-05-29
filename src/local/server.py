from flask import Flask, request, jsonify
import base64
import cv2
import numpy as np
import time
import psutil
import GPUtil
from pathlib import Path

app = Flask(__name__)


class ObjectDetection:
    def __init__(self):
        self.MODEL_CONFIG = Path.cwd() / "yolo_tiny_configs" / "yolov3-tiny.cfg"
        self.MODEL_WEIGHTS = Path.cwd() / "yolo_tiny_configs" / "yolov3-tiny.weights"
        self.COCO_NAMES = Path.cwd() / "yolo_tiny_configs" / "coco.names"

        self.net = cv2.dnn.readNet(str(self.MODEL_WEIGHTS), str(self.MODEL_CONFIG))
        with open(self.COCO_NAMES, "r") as f:
            self.classes = [line.strip() for line in f.readlines()]

        self.output_layers = self.net.getUnconnectedOutLayersNames()

    def detect_objects(self, image_data):
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
                if confidence > 0.5:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

        detected_objects = []
        if len(indexes) > 0:
            for i in indexes:
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                detected_objects.append({"label": label, "accuracy": confidence})

        return detected_objects, inference_time


detector = ObjectDetection()


@app.route("/api/object_detection", methods=["POST"])
def object_detection():
    data = request.get_json()
    img_id = data["id"]  # return the UUID sent by the client as is
    img_data = base64.b64decode(data["image_data"])  # decode base64 image data
    detected_objects, inference_time = detector.detect_objects(img_data)

    return jsonify({"id": img_id, "objects": detected_objects, "inference_time": inference_time})


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


if __name__ == "__main__":
    app.run(port=5000, debug=True)
