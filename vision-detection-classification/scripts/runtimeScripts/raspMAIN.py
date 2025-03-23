#!/usr/bin/env python3
import time
import json
import cv2
import numpy as np
import sys
import subprocess
import argparse
from functools import lru_cache
from flask import Flask, Response
import paho.mqtt.client as mqtt

# Picamera2 e IMX500
from picamera2 import Picamera2, MappedArray
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics, postprocess_nanodet_detection

app = Flask(__name__)

# Variabile globale per mantenere l'ultima lista di rilevamenti
last_detections = []

class Detection:
    def __init__(self, coords, category, conf, metadata, picam2, imx500):
        """Crea un oggetto Detection con bounding box (x,y,w,h), categoria e confidenza."""
        self.category = category
        self.conf = conf
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)

def parse_detections(metadata, imx500, intrinsics, picam2, args):
    """Estrae i bounding box, la categoria e il punteggio di confidenza dall'inferenza."""
    global last_detections
    bbox_normalization = intrinsics.bbox_normalization
    bbox_order = intrinsics.bbox_order
    threshold = args.threshold
    iou = args.iou
    max_detections = args.max_detections

    np_outputs = imx500.get_outputs(metadata, add_batch=True)
    input_w, input_h = imx500.get_input_size()
    if np_outputs is None:
        return last_detections

    if intrinsics.postprocess == "nanodet":
        boxes, scores, classes = postprocess_nanodet_detection(
            outputs=np_outputs[0], conf=threshold, iou_thres=iou, max_out_dets=max_detections
        )[0]
        from picamera2.devices.imx500.postprocess import scale_boxes
        boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
    else:
        boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]
        if bbox_normalization:
            boxes = boxes / input_h
        if bbox_order == "xy":
            boxes = boxes[:, [1, 0, 3, 2]]
        boxes = np.array_split(boxes, 4, axis=1)
        boxes = zip(*boxes)
    last_detections = [
        Detection(box, category, score, metadata, picam2, imx500)
        for box, score, category in zip(boxes, scores, classes) if score > threshold
    ]
    return last_detections

@lru_cache
def get_labels(intrinsics):
    """Restituisce la lista di label (filtrando eventuali '-')"""
    labels = intrinsics.labels
    if intrinsics.ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels

def draw_detections(frame, detections, intrinsics, imx500):
    """Disegna i bounding box e le label sul frame e restituisce il frame modificato."""
    if not detections:
        return frame
    labels = get_labels(intrinsics)
    for detection in detections:
        x, y, w, h = detection.box
        cat_idx = int(detection.category)
        label_str = labels[cat_idx] if 0 <= cat_idx < len(labels) else f"Label{cat_idx}"
        conf_str = f"({detection.conf:.2f})"
        text = f"{label_str} {conf_str}"
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), thickness=2)
        (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        text_x, text_y = x + 5, y + 15
        overlay = frame.copy()
        cv2.rectangle(overlay, (text_x, text_y - text_h), (text_x+text_w, text_y+baseline), (255, 255, 255), cv2.FILLED)
        alpha = 0.3
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return frame

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str,
                        default="/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk",
                        help="Path of the model rpk file")
    parser.add_argument("--threshold", type=float, default=0.55, help="Detection threshold")
    parser.add_argument("--iou", type=float, default=0.65, help="Set IOU threshold")
    parser.add_argument("--max-detections", type=int, default=10, help="Set max detections")
    # Argomenti per MQTT
    parser.add_argument("--mqtt-host", type=str, default="localhost", help="Hostname del broker MQTT")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="Porta del broker MQTT")
    parser.add_argument("--mqtt-topic", type=str, default="imx500/detections", help="Topic MQTT")
    return parser.parse_args()

# Inizializza argomenti e componenti
args = get_args()
imx500 = IMX500(args.model)
intrinsics = imx500.network_intrinsics or NetworkIntrinsics(task="object detection")
if not intrinsics:
    print("Errore: Intrinsics non trovati", file=sys.stderr)
    sys.exit(1)
if intrinsics.labels is None:
    with open("assets/coco_labels.txt", "r") as f:
        intrinsics.labels = f.read().splitlines()
intrinsics.update_with_defaults()

# Inizializza la camera in modalità headless
picam2 = Picamera2(imx500.camera_num)
config = picam2.create_preview_configuration(buffer_count=12)
picam2.start(config, show_preview=False)

# Inizializza il client MQTT
mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(args.mqtt_host, args.mqtt_port, 60)
    mqtt_client.loop_start()
    print(f"[MQTT] Connesso a {args.mqtt_host}:{args.mqtt_port}, topic='{args.mqtt_topic}'")
except Exception as e:
    print(f"[MQTT] Errore di connessione: {e}")
    mqtt_client = None

def gen_frames():
    """Genera frame JPEG per lo streaming video e pubblica in tempo reale i dati sul server MQTT."""
    global last_detections
    while True:
        # Cattura il frame come immagine
        frame = picam2.capture_array()
        # Cattura metadata per l'inferenza
        metadata = picam2.capture_metadata()
        detections = parse_detections(metadata, imx500, intrinsics, picam2, args)
        # Pubblica i dati di rilevamento su MQTT (se ci sono rilevamenti)
        detection_data = []
        for d in detections:
            x, y, w, h = d.box
            detection_data.append({
                "category": int(d.category),
                "confidence": float(f"{d.conf:.2f}"),
                "box": [x, y, w, h]
            })
        if mqtt_client and detection_data:
            payload = {"num_detections": len(detection_data), "detections": detection_data}
            mqtt_client.publish(args.mqtt_topic, json.dumps(payload))
        # Disegna i rilevamenti sul frame
        frame = draw_detections(frame, detections, intrinsics, imx500)
        # Codifica il frame in JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    """Endpoint per lo streaming video."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Avvia l'app Flask per lo streaming video sulla porta 5000
    app.run(host="0.0.0.0", port=5000)
