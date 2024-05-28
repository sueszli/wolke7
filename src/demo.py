"""
Utils script to visualize the output of the YOLO object detection model.

see: https://github.com/opencv/opencv/blob/4.x/samples/dnn/object_detection.py
"""

import cv2
import argparse
import numpy as np

# YOLO configuration
MODEL_CONFIG = "yolo_tiny_configs/yolov3-tiny.cfg"
MODEL_WEIGHTS = "yolo_tiny_configs/yolov3-tiny.weights"
COCO_NAMES = "yolo_tiny_configs/coco.names"


def get_args():
    parser = argparse.ArgumentParser(description="YOLO Object Detection")
    parser.add_argument("-i", "--image-path", required=True, help="Path to image file")
    parser.add_argument("-c", "--conf-threshold", type=float, default=0.2, help="Confidence threshold")
    parser.add_argument("--apply-nms", type=bool, default=True, help="Apply non-max suppression")
    parser.add_argument("--nms-threshold", type=float, default=0.2, help="NMS threshold")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    # Load YOLO
    net = cv2.dnn.readNet(MODEL_WEIGHTS, MODEL_CONFIG)
    with open(COCO_NAMES, "r") as f:
        classes = [line.strip() for line in f.readlines()]

    # Get the output layers
    output_layers = net.getUnconnectedOutLayersNames()

    # Read the image
    image = cv2.imread(args.image_path)
    height, width, channels = image.shape

    # Prepare the image for YOLO
    # https://github.com/opencv/opencv/blob/4.x/samples/dnn/models.yml
    blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

    # Run the YOLO network
    classIds = []
    confidences = []
    boxes = []
    net.setInput(blob)
    outs = net.forward(output_layers)
    """ 
    Both output layers are of type `Region`:
        Network produces output blob with a shape NxC where N is a number of
        detected objects and C is a number of classes + 5 where the first 5
        numbers are [box_confidence, center_x, center_y, width, height]
    """

    # Extract the bounding boxes, confidences, and class IDs
    for out in outs:
        for detection in out:
            scores = detection[5:]
            classId = np.argmax(scores)
            confidence = scores[classId]
            if confidence > args.conf_threshold:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                width_box = int(detection[2] * width)
                height_box = int(detection[3] * height)
                left = int(center_x - width_box / 2)
                top = int(center_y - height_box / 2)
                classIds.append(classId)
                confidences.append(float(confidence))
                boxes.append([left, top, width_box, height_box])

    # Non-max suppression
    if args.apply_nms:
        indices = cv2.dnn.NMSBoxes(boxes, confidences, args.conf_threshold, args.nms_threshold)
        boxes = [boxes[i] for i in indices]
        classIds = [classIds[i] for i in indices]
        confidences = [confidences[i] for i in indices]

    # Draw the bounding boxes
    COLORS = np.random.randint(0, 255, size=(len(classes), 3))
    print(boxes, [classes[i] for i in classIds], confidences)
    if len(boxes) > 0:
        # loop over the indexes we are keeping
        for i, box in enumerate(boxes):
            # extract the bounding box coordinates
            (x, y) = (box[0], box[1])
            (w, h) = (box[2], box[3])
            # draw a bounding box rectangle and label on the image
            color = COLORS[i].tolist()
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            text = "{}: {:.4f}".format(classes[classIds[i]], confidences[i])
            cv2.putText(image, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    # show the output image
    cv2.imshow("Image", image)
    cv2.waitKey(0)
