from flask import Flask, request, jsonify
import base64
import cv2
import numpy as np
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
        outs = self.net.forward(self.output_layers)

        class_ids = []
        confidences = []
        boxes = []

        # Extract the bounding boxes, confidences, and class IDs
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
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

                # filter out low confidence detections
                threshold = 0.5
                if confidence > threshold:
                    detected_objects.append({"label": label, "accuracy": confidence})

        return detected_objects


detector = ObjectDetection()


@app.route("/api/object_detection", methods=["POST"])
def object_detection():
    data = request.get_json()
    img_id = data["id"]  # return the UUID sent by the client as is
    img_data = base64.b64decode(data["image_data"])  # detect objects in base64 encoded image data
    detected_objects = detector.detect_objects(img_data)
    return jsonify({"id": img_id, "objects": detected_objects})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
