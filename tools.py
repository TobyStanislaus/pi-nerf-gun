from ultralytics import YOLO
import cv2


def load_model(path):
    model = YOLO(path) 
    return model


def detect_image(model, image):
    results = model(image, verbose=False)[0]
    for result in results.boxes.data.tolist():
        x1, y1, x2, y2, conf, type = result
        if conf>0.5:
            return True

    return False

