from ultralytics import YOLO

model = YOLO("yolov8n-face.pt")  # Load your model
model.export(format="onnx", dynamic=True)  # Export to ONNX
