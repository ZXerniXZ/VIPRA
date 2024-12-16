from ultralytics import YOLO

model = YOLO("best.pt")

model.predict(source = "video.mp4", show=True, save=True, conf=0.1, line_width = 2, save_crop = True,
              save_txt = True, show_labels = True, show_conf = True, classes=[0, 1])
