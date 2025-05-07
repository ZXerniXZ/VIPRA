#!/usr/bin/env python3
"""
imx500.py
──────────────────────────────────────────────────────────────────────────────
Esegue inferenza on-sensor con la Raspberry Pi AI Camera (Sony IMX500) su
Raspberry Pi 5: pubblica i risultati via MQTT e salva snapshot. Gestisce:
  • --threshold   soglia di confidenza
  • --max-boxes   massimo bounding-box per frame
  • --iou-threshold  pubblicazione singola per oggetto finché rimane in scena

USO
────
    python3 imx500.py \
        --model    /usr/share/imx500-models/imx500_network_efficientdet_lite0_pp.rpk \
        --broker   192.168.1.10 \
        --topic    ai/camera \
        --savedir  captures \
        [--threshold 0.4] [--max-boxes 0] [--iou-threshold 0.5] [--loglevel INFO]

Opzioni:
    --model           Percorso al file .rpk del modello (obbligatorio)
    --broker          Hostname/IP del broker MQTT (default: localhost)
    --port            Porta broker MQTT (default: 1883)
    --topic           Topic MQTT (default: imx500/detections)
    --user            Username MQTT (opzionale)
    --password        Password MQTT (opzionale)
    --threshold       Soglia di confidenza (0–1, default 0.4)
    --max-boxes       Numero massimo di box per frame (0 = illimitato)
    --iou-threshold   Soglia IoU per matching oggetti (default 0.5)
    --savedir         Directory per snapshot (default: captures)
    --loglevel        Livello log (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Prerequisiti:
    sudo apt install imx500-all python3-picamera2 python3-opencv python3-paho-mqtt
"""

from __future__ import annotations
import argparse, json, logging, os, signal, sys, time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500


def iou(boxA: tuple[float, float, float, float], boxB: tuple[float, float, float, float]) -> float:
    """Intersection-over-Union tra due box (x1,y1,x2,y2)"""
    xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
    xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
    interW, interH = max(0, xB - xA), max(0, yB - yA)
    inter = interW * interH
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    uni = areaA + areaB - inter
    return inter / uni if uni > 0 else 0.0


def build_camera(picam2: Picamera2, model_path: Path) -> IMX500:
    """Inizializza IMX500 con preview e raw stream"""
    imx = IMX500(str(model_path))
    cfg = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "XBGR8888"},
        raw={"size": (2028, 1520), "format": "SRGGB10"}
    )
    picam2.configure(cfg)
    imx.set_auto_aspect_ratio()
    return imx


def connect_mqtt(broker: str, port: int, user: str|None, pwd: str|None) -> mqtt.Client:
    client = mqtt.Client("imx500-pi5")
    if user:
        client.username_pw_set(user, pwd or "")
    client.connect(broker, port, keepalive=60)
    return client


def main() -> None:
    parser = argparse.ArgumentParser("IMX500 → MQTT publisher")
    parser.add_argument("--model",        required=True)
    parser.add_argument("--broker",       default="localhost")
    parser.add_argument("--port",         type=int, default=1883)
    parser.add_argument("--topic",        default="imx500/detections")
    parser.add_argument("--user",         default=None)
    parser.add_argument("--password",     default=None)
    parser.add_argument("--threshold",    type=float, default=0.4)
    parser.add_argument("--max-boxes",    type=int,   default=0)
    parser.add_argument("--iou-threshold",type=float, default=0.5)
    parser.add_argument("--savedir",      default="captures")
    parser.add_argument("--loglevel",     default="INFO",
        choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel),
        format="[%(asctime)s] [%(levelname)s] %(message)s"
    )
    os.makedirs(args.savedir, exist_ok=True)

    # setup camera
    picam2 = Picamera2()
    imx = build_camera(picam2, Path(args.model))
    logging.info("Uploading firmware to IMX500 (1–2 min)…")
    picam2.start()

    # mqtt
    mqttc = connect_mqtt(args.broker, args.port, args.user, args.password)
    logging.info("MQTT connected %s:%d topic='%s'",
                 args.broker, args.port, args.topic)

    # stato oggetti attivi
    active: list[tuple[int, float, float, float, float]] = []
    running = True
    def stop(sig, frame): nonlocal running; running=False
    for s in (signal.SIGINT, signal.SIGTERM): signal.signal(s, stop)

    while running:
        # cattura inferenza
        req = picam2.capture_request()
        frame = req.make_array("main")
        meta  = req.get_metadata()
        req.release()

        outputs = imx.get_outputs(meta)
        if outputs is None:
            continue
        boxes, scores, classes, *_ = outputs
        boxes   = np.asarray(boxes).reshape(-1,4)
        scores  = np.asarray(scores).reshape(-1)
        classes = np.asarray(classes).reshape(-1)

        # filtra e ordina
        dets: list[tuple[int, float, float, float, float, float]] = []
        for box, score, cls in zip(boxes, scores, classes):
            if score < args.threshold: continue
            x1, y1, w, h = box
            x2, y2 = x1 + w, y1 + h
            dets.append((int(cls), x1, y1, x2, y2, float(score)))
        dets.sort(key=lambda x: x[5], reverse=True)
        if args.max_boxes > 0:
            dets = dets[: args.max_boxes]

        # identifica nuovi oggetti
        new_objs: list[tuple[int, float, float, float, float, float]] = []
        for det in dets:
            cls, x1, y1, x2, y2, score = det
            found = False
            for ac in active:
                if ac[0] == cls and iou(ac[1:], (x1, y1, x2, y2)) >= args.iou_threshold:
                    found = True; break
            if not found:
                new_objs.append(det)

        # aggiorna active con detections attuali
        active = [(cls, x1, y1, x2, y2) for cls, x1, y1, x2, y2, _ in dets]

        if new_objs:
            # prepara payload JSON
            payload = []
            for cls, x1, y1, x2, y2, score in new_objs:
                payload.append({
                    "cls": cls,
                    "score": round(score, 3),
                    "bbox": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                })
            mqttc.publish(
                args.topic,
                json.dumps({"ts": time.time(), "detections": payload}),
                qos=0
            )
            mqttc.loop(0)

            # salva snapshot
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            img = frame[..., :3]
            path = Path(args.savedir) / f"{ts}.jpg"
            cv2.imwrite(str(path), img)
            logging.debug("Published %d new objects, saved %s", len(new_objs), path)

    logging.info("Stopping…")
    picam2.stop()
    mqttc.disconnect()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Unhandled error, exiting")
        sys.exit(1)
