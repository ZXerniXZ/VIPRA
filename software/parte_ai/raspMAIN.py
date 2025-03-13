#!/usr/bin/env python3
import argparse
import sys
import time
import json
import threading
import asyncio

import cv2
import numpy as np
from functools import lru_cache

# Client MQTT (paho-mqtt)
import paho.mqtt.client as paho

# Broker MQTT (HBMQTT)
from hbmqtt.broker import Broker

# Picamera2 e IMX500
from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import (
    NetworkIntrinsics,
    postprocess_nanodet_detection
)

# --------------------------------------------------------------------------------
#                     SEZIONE 1: CLASSE DETECTION E PARSING
# --------------------------------------------------------------------------------
last_detections = []

class Detection:
    def __init__(self, coords, category, conf, metadata, picam2, imx500):
        """Crea un oggetto Detection con bounding box (x,y,w,h), categoria e confidenza."""
        self.category = category
        self.conf = conf
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)


def parse_detections(metadata: dict, imx500, intrinsics, picam2, args):
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
        # Postprocess con Nanodet
        boxes, scores, classes = postprocess_nanodet_detection(
            outputs=np_outputs[0],
            conf=threshold,
            iou_thres=iou,
            max_out_dets=max_detections
        )[0]
        from picamera2.devices.imx500.postprocess import scale_boxes
        boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
    else:
        # Postprocess di default
        boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]
        if bbox_normalization:
            boxes = boxes / input_h

        if bbox_order == "xy":
            # Se era (y0, x0, y1, x1), lo riassembliamo in (x0, y0, x1, y1)
            boxes = boxes[:, [1, 0, 3, 2]]

        # Spezziamo l'array in 4 colonne
        boxes = np.array_split(boxes, 4, axis=1)
        boxes = zip(*boxes)

    last_detections = [
        Detection(box, category, score, metadata, picam2, imx500)
        for box, score, category in zip(boxes, scores, classes)
        if score > threshold
    ]
    return last_detections


@lru_cache
def get_labels(intrinsics):
    labels = intrinsics.labels
    if intrinsics.ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels


def draw_detections(request, stream, last_results, intrinsics, imx500):
    if not last_results:
        return
    labels = get_labels(intrinsics)
    with MappedArray(request, stream) as m:
        for detection in last_results:
            x, y, w, h = detection.box
            cat_idx = int(detection.category)
            if 0 <= cat_idx < len(labels):
                label_str = labels[cat_idx]
            else:
                label_str = f"Label{cat_idx}"

            conf_str = f"({detection.conf:.2f})"
            text = f"{label_str} {conf_str}"

            # Disegno bounding box
            cv2.rectangle(m.array, (x, y), (x + w, y + h), (0, 255, 0), thickness=2)

            # Disegno etichetta
            (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            text_x, text_y = x + 5, y + 15
            overlay = m.array.copy()
            cv2.rectangle(overlay,
                          (text_x, text_y - text_h),
                          (text_x + text_w, text_y + baseline),
                          (255, 255, 255), cv2.FILLED)
            alpha = 0.30
            cv2.addWeighted(overlay, alpha, m.array, 1 - alpha, 0, m.array)
            cv2.putText(m.array, text, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Se si preserva aspect ratio, disegno ROI
        if intrinsics.preserve_aspect_ratio:
            b_x, b_y, b_w, b_h = imx500.get_roi_scaled(request)
            color = (255, 0, 0)
            cv2.putText(m.array, "ROI", (b_x + 5, b_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.rectangle(m.array, (b_x, b_y), (b_x + b_w, b_y + b_h), color, thickness=2)


# --------------------------------------------------------------------------------
#                     SEZIONE 2: BROKER MQTT INCORPORATO (HBMQTT)
# --------------------------------------------------------------------------------
def make_broker_config(bind_port):
    """
    Crea una configurazione base per HBMQTT, in ascolto su 0.0.0.0:<bind_port>.
    Consente connessioni anonime per semplicità.
    """
    return {
        'listeners': {
            'default': {
                'type': 'tcp',
                'bind': f'0.0.0.0:{bind_port}'
            }
        },
        'sys_interval': 10,
        'auth': {
            'allow-anonymous': True  # Permettiamo a chiunque di connettersi
        }
    }


async def broker_task(bind_port):
    """
    Funzione asincrona principale del broker. Avvia HBMQTT sulla porta indicata
    e resta in esecuzione finché non viene terminata.
    """
    broker = Broker(make_broker_config(bind_port))
    await broker.start()
    print(f"[BROKER] MQTT Broker in ascolto su 0.0.0.0:{bind_port}")

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("[BROKER] Terminazione broker in corso...")
        await broker.shutdown()


def start_broker_in_thread(bind_port):
    """
    Avvia il broker HBMQTT su un thread separato con un loop asyncio dedicato.
    """
    def _broker_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Avviamo la coroutines broker_task in questo nuovo event loop
        task = broker_task(bind_port)
        try:
            loop.run_until_complete(task)
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    t = threading.Thread(target=_broker_thread, daemon=True)
    t.start()
    # Attendi un po' di tempo per dare modo al broker di avviarsi
    time.sleep(1)


# --------------------------------------------------------------------------------
#                     SEZIONE 3: MAIN + MQTT CLIENT LOCALE
# --------------------------------------------------------------------------------
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str,
                        default="/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk",
                        help="Path of the model rpk file")
    parser.add_argument("--fps", type=int, help="Frames per second")
    parser.add_argument("--bbox-normalization", action=argparse.BooleanOptionalAction,
                        help="Normalize bbox")
    parser.add_argument("--bbox-order", choices=["yx", "xy"], default="yx",
                        help="Set bbox order (yx-> y0x0y1x1, xy-> x0y0x1y1)")
    parser.add_argument("--threshold", type=float, default=0.55, help="Detection threshold")
    parser.add_argument("--iou", type=float, default=0.65, help="Set IOU threshold")
    parser.add_argument("--max-detections", type=int, default=10, help="Set max detections")
    parser.add_argument("--ignore-dash-labels", action=argparse.BooleanOptionalAction,
                        help="Remove '-' labels")
    parser.add_argument("--postprocess", choices=["", "nanodet"], default=None,
                        help="Run post process of type")
    parser.add_argument("-r", "--preserve-aspect-ratio", action=argparse.BooleanOptionalAction,
                        help="Preserve pixel aspect ratio of input tensor")
    parser.add_argument("--labels", type=str, help="Path to the labels file")
    parser.add_argument("--print-intrinsics", action="store_true",
                        help="Print JSON network_intrinsics then exit")

    # Nuovo argomento: ospitare un broker su --mqtt-port
    parser.add_argument("--mqtt-port", type=int, default=1883,
                        help="Porta su cui avviare il broker MQTT embedded")

    # Topic interno su cui pubblicare i rilevamenti
    parser.add_argument("--mqtt-topic", type=str, default="imx500/detections",
                        help="Topic MQTT per i rilevamenti")

    return parser.parse_args()


def main():
    args = get_args()

    # 1) Avvia il BROKER in un thread (async) sulla porta specificata
    start_broker_in_thread(args.mqtt_port)

    # 2) Inizializza IMX500 e intrinsics
    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"
    elif intrinsics.task != "object detection":
        print("Network is not an object detection task", file=sys.stderr)
        sys.exit(1)

    if args.labels:
        with open(args.labels, 'r') as f:
            lines = f.read().splitlines()
        intrinsics.labels = lines

    for key, value in vars(args).items():
        if key == 'labels':
            continue
        if hasattr(intrinsics, key) and value is not None:
            setattr(intrinsics, key, value)

    if intrinsics.labels is None:
        with open("assets/coco_labels.txt", "r") as f:
            intrinsics.labels = f.read().splitlines()

    intrinsics.update_with_defaults()

    if args.print_intrinsics:
        print(intrinsics)
        sys.exit(0)

    # 3) Inizializza la camera
    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12
    )

    imx500.show_network_fw_progress_bar()
    picam2.start(config, show_preview=True)

    if intrinsics.preserve_aspect_ratio:
        imx500.set_auto_aspect_ratio()

    global last_detections
    last_detections = []

    def user_callback(request):
        draw_detections(request, "main", last_detections, intrinsics, imx500)

    picam2.pre_callback = user_callback

    # 4) Prepara un CLIENT MQTT locale per pubblicare i rilevamenti sul broker appena avviato
    mqtt_client = paho.Client()
    try:
        mqtt_client.connect("localhost", args.mqtt_port, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Broker locale in esecuzione sulla porta {args.mqtt_port}")
        print(f"[MQTT] Pubblico i messaggi su topic '{args.mqtt_topic}'")
    except Exception as e:
        print(f"[MQTT] Impossibile connettersi al broker locale: {e}")
        mqtt_client = None

    # 5) Loop principale: inferenza e pubblicazione
    while True:
        metadata = picam2.capture_metadata()
        last_detections = parse_detections(metadata, imx500, intrinsics, picam2, args)

        if last_detections:
            print(f"Rilevati {len(last_detections)} oggetti:")
            detections_info = []
            for d in last_detections:
                (x, y, w, h) = d.box
                print(f"  - Categoria: {d.category}, Conf: {d.conf:.2f}, Box=({x},{y},{w},{h})")
                det_dict = {
                    "category": int(d.category),
                    "confidence": float(f"{d.conf:.2f}"),
                    "box": [x, y, w, h]
                }
                detections_info.append(det_dict)

            if mqtt_client:
                payload = {
                    "num_detections": len(detections_info),
                    "detections": detections_info
                }
                try:
                    mqtt_client.publish(args.mqtt_topic, json.dumps(payload))
                except Exception as e:
                    print(f"[MQTT] Errore pubblicazione: {e}")
        else:
            print("Nessun oggetto rilevato.")


if __name__ == "__main__":
    main()
