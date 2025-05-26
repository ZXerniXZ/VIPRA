from ultralytics import YOLO

# Load a model
model = YOLO("yolov8n")  # or yolov5m, yolov5l, yolov5x, custom
#model = YOLO("yolo8n.yaml").load("yolo8n.pt")  # build from YAML and transfer weights

# Train the model
results = model.train(data="/home/ares/localRepo/projectDayProject/software/parte_ai/train/project day.v2i.yolov8/data.yaml", epochs=100, imgsz=640)