#!/usr/bin/env python3
"""
imx500.py
──────────────────────────────────────────────────────────────────────────────
• Rileva oggetti con la Raspberry Pi AI Camera (Sony IMX500) su Pi 5.
• Pubblica le nuove detection via MQTT.
• Se la detection appartiene alle classi richieste:
    1. Salva l’intero frame JPEG in --savedir (richiede --save-images).
    2. Sospende l’acquisizione finché ServerAI torna *idle* (topic --status-topic).
    3. Invia il file a http://localhost:8002/analyze (multipart, MIME corretto).

Opzioni principali
──────────────────
  --model            Percorso al .rpk (obbligatorio)
  --broker           Host broker MQTT (default localhost)
  --topic            Topic detection (default imx500/detections)
  --status-topic     Topic stato ServerAI (default serverai/status)
  --classes 3 5 ...  Classi da considerare (default tutte)
  --save-images      Abilita il salvataggio + callback HTTP
  --savedir DIR      Cartella snapshot (default captures)
"""

from __future__ import annotations
import argparse, json, logging, os, signal, sys, time, threading, requests
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500

# ────────── utility ─────────────────────────────────────────────────────────
def iou(a: tuple[float, float, float, float],
        b: tuple[float, float, float, float]) -> float:
    """Intersection‑over‑Union fra due box (x1,y1,x2,y2)."""
    xA, yA = max(a[0], b[0]), max(a[1], b[1])
    xB, yB = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0:
        return 0.0
    areaA = (a[2] - a[0]) * (a[3] - a[1])
    areaB = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (areaA + areaB - inter)

def build_camera(picam2: Picamera2, model_path: Path) -> IMX500:
    imx = IMX500(str(model_path))
    cfg = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "XBGR8888"},
        raw={"size": (2028, 1520), "format": "SRGGB10"},
    )
    picam2.configure(cfg)
    imx.set_auto_aspect_ratio()
    return imx

def connect_mqtt(host: str, port: int, user: str | None, pwd: str | None) -> mqtt.Client:
    client = mqtt.Client(transport="tcp", protocol=mqtt.MQTTv311)
    if user:
        client.username_pw_set(user, pwd or "")
    client.connect(host, port, 60)
    client.loop_start()          # thread di rete
    return client

# ────────── main ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--broker", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="imx500/detections")
    ap.add_argument("--status-topic", default="serverai/status")
    ap.add_argument("--user"); ap.add_argument("--password")
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--max-boxes", type=int, default=0)
    ap.add_argument("--iou-threshold", type=float, default=0.5)
    ap.add_argument("--classes", type=int, nargs="+")
    ap.add_argument("--savedir", default="captures")
    ap.add_argument("--save-images", action="store_true")
    ap.add_argument("--loglevel", default="INFO",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    args = ap.parse_args()

    logging.basicConfig(level=getattr(logging, args.loglevel),
                        format="[%(asctime)s] %(levelname)s: %(message)s")
    os.makedirs(args.savedir, exist_ok=True)

    picam2 = Picamera2()
    imx = build_camera(picam2, Path(args.model))
    logging.info("Firmware upload – attendere 1‑2 minuti al primo avvio…")
    picam2.start()

    pub = connect_mqtt(args.broker, args.port, args.user, args.password)
    sub = connect_mqtt(args.broker, args.port, args.user, args.password)

    idle_evt = threading.Event()

    def on_msg(_, __, msg):
        if msg.topic == args.status_topic and msg.payload.decode().strip() == "idle":
            idle_evt.set()
    sub.on_message = on_msg
    sub.subscribe(args.status_topic)

    stop_evt = threading.Event()
    signal.signal(signal.SIGINT,  lambda *_: stop_evt.set())
    signal.signal(signal.SIGTERM, lambda *_: stop_evt.set())

    active: list[tuple[int, float, float, float, float]] = []

    while not stop_evt.is_set():
        req = picam2.capture_request()
        frame = req.make_array("main")          # XBGR8888
        meta  = req.get_metadata()
        req.release()

        outputs = imx.get_outputs(meta)
        if outputs is None:
            continue
        boxes, scores, classes, *_ = outputs
        boxes   = np.asarray(boxes).reshape(-1, 4)
        scores  = np.asarray(scores).reshape(-1)
        classes = np.asarray(classes).reshape(-1)

        dets = []
        for box, score, cls in zip(boxes, scores, classes):
            if score < args.threshold:
                continue
            if args.classes and cls not in args.classes:
                continue
            x1, y1, w, h = box
            x2, y2 = x1 + w, y1 + h
            dets.append((int(cls), x1, y1, x2, y2, float(score)))
        dets.sort(key=lambda d: d[5], reverse=True)
        if args.max_boxes:
            dets = dets[: args.max_boxes]

        new_objs = [
            d for d in dets
            if not any(ac[0] == d[0] and iou(ac[1:], d[1:5]) >= args.iou_threshold
                       for ac in active)
        ]
        active = [(c, x1, y1, x2, y2) for c, x1, y1, x2, y2, _ in dets]

        if not new_objs:
            continue

        # ── publish detection JSON ────────────────────────────────
        payload = [
            {"cls": c, "score": round(s, 3),
             "bbox": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]}
            for c, x1, y1, x2, y2, s in new_objs
        ]
        pub.publish(args.topic,
                    json.dumps({"ts": time.time(), "detections": payload}),
                    qos=0)

        # ── snapshot + callback ───────────────────────────────────
        if not args.save_images:
            continue

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        img_path = Path(args.savedir) / f"{ts}.jpg"
        cv2.imwrite(str(img_path), frame[..., :3])  # XBGR -> BGR
        logging.info("Snapshot salvato: %s", img_path)

        idle_evt.clear()
        try:
            with open(img_path, "rb") as fh:
                r = requests.post(
                    "http://localhost:8002/analyze",
                    files={"file": (img_path.name, fh, "image/jpeg")},  # MIME esplicito
                    headers={"Accept": "application/json"},
                    timeout=300,
                )
                logging.info("POST /analyze → %s", r.status_code)
        except Exception as e:
            logging.error("Errore HTTP: %s", e)

        logging.info("In attesa che ServerAI torni idle …")
        while not stop_evt.is_set() and not idle_evt.wait(0.5):
            pass
        logging.info("Idle ricevuto, riprendo l’acquisizione")

    logging.info("Uscita")
    picam2.stop()
    pub.loop_stop();  sub.loop_stop()
    pub.disconnect(); sub.disconnect()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Errore non gestito – uscita")
        sys.exit(1)
