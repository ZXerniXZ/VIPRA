#!/usr/bin/env python3
import time
import json
import argparse
import cv2
import numpy as np
import sys
import subprocess
from functools import lru_cache
import paho.mqtt.client as mqtt

# Importa le librerie della fotocamera e del modello
from picamera2 import Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics, postprocess_nanodet_detection

# Variabile globale per i rilevamenti
last_detections = []

class Detection:
    def __init__(self, coords, category, conf, metadata, picam2, imx500):
        """Crea un oggetto Detection con bounding box (x,y,w,h), categoria e confidenza."""
        self.category = category
        self.conf = conf
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)

def parse_detections(metadata, imx500, intrinsics, picam2, args):
    """Estrae bounding box, categoria e punteggio di confidenza dall'inferenza."""
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
            outputs=np_outputs[0],
            conf=threshold,
            iou_thres=iou,
            max_out_dets=max_detections
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
    """Restituisce la lista di label, filtrando eventuali '-'."""
    labels = intrinsics.labels
    if intrinsics.ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str,
                        default="/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk",
                        help="Percorso del file del modello (rpk)")
    parser.add_argument("--threshold", type=float, default=0.55, help="Soglia per le rilevazioni")
    parser.add_argument("--iou", type=float, default=0.65, help="Soglia IOU")
    parser.add_argument("--max-detections", type=int, default=10, help="Numero massimo di rilevazioni")
    # Argomenti per MQTT
    parser.add_argument("--mqtt-host", type=str, default="localhost", help="Hostname del broker MQTT")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="Porta del broker MQTT")
    parser.add_argument("--mqtt-topic", type=str, default="imx500/detections", help="Topic MQTT per i dati di rilevamento")
    return parser.parse_args()

def main():
    args = get_args()

    # Inizializza il modello IMX500
    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"
    elif intrinsics.task != "object detection":
        print("Errore: il modello non è configurato per object detection", file=sys.stderr)
        sys.exit(1)
    # Carica le label, se non presenti usa un file di default
    if intrinsics.labels is None:
        try:
            with open("assets/coco_labels.txt", "r") as f:
                intrinsics.labels = f.read().splitlines()
        except Exception as e:
            print("Errore nel caricamento delle label:", e)
            intrinsics.labels = []
    intrinsics.update_with_defaults()

    # Inizializza la fotocamera in modalità headless
    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(buffer_count=12)
    picam2.start(config, show_preview=False)

    # Inizializza il client MQTT
    mqtt_client = mqtt.Client()
    try:
        mqtt_client.connect(args.mqtt_host, args.mqtt_port, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Connesso a {args.mqtt_host}:{args.mqtt_port} su topic '{args.mqtt_topic}'")
    except Exception as e:
        print(f"[MQTT] Errore di connessione: {e}")
        mqtt_client = None

    while True:
        # Cattura metadata per l'inferenza
        metadata = picam2.capture_metadata()
        detections = parse_detections(metadata, imx500, intrinsics, picam2, args)
        detection_data = []
        for d in detections:
            x, y, w, h = d.box
            detection_data.append({
                "category": int(d.category),
                "confidence": float(f"{d.conf:.2f}"),
                "box": [x, y, w, h]
            })
        payload = json.dumps({"detections": detection_data})
        if mqtt_client:
            mqtt_client.publish(args.mqtt_topic, payload)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
