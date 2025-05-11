#!/usr/bin/env python3
"""
imx500.py
──────────────────────────────────────────────────────────────────────────────
• Rileva oggetti con la Raspberry Pi AI Camera (Sony IMX500).
• Pubblica le nuove detection via MQTT.
• Se una detection appartiene alle classi richieste:
  1. Salva l’intero frame JPEG in `--savedir`.
  2. **Sospende** l’acquisizione finché il servizio ServerAI torna *idle*.
  3. Invia il file al servizio HTTP `http://localhost:8002/analyze`.

Parametri aggiuntivi
────────────────────
--status-topic   Topic MQTT su cui il ServerAI pubblica lo stato (default: serverai/status)

Il broker MQTT per lo stato è lo stesso usato per pubblicare le detection.
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

# ────────── utility ──────────

def iou(a, b):  # (x1,y1,x2,y2)
    xA, yA = max(a[0], b[0]), max(a[1], b[1])
    xB, yB = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = (a[2]-a[0])*(a[3]-a[1])
    areaB = (b[2]-b[0])*(b[3]-b[1])
    union = areaA + areaB - inter
    return inter/union if union else 0.0


def build_camera(picam2: Picamera2, model: Path):
    imx = IMX500(str(model))
    cfg = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "XBGR8888"},
        raw={"size": (2028, 1520), "format": "SRGGB10"})
    picam2.configure(cfg)
    imx.set_auto_aspect_ratio()
    return imx


def connect_mqtt(host, port, user, pw):
    c = mqtt.Client("imx500-pi5")
    if user:
        c.username_pw_set(user, pw or "")
    c.connect(host, port, keepalive=60)
    return c

# ────────── main ──────────

def main():
    p = argparse.ArgumentParser("IMX500 detection → MQTT + HTTP callback")
    p.add_argument("--model", required=True)
    p.add_argument("--broker", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--topic", default="imx500/detections")
    p.add_argument("--status-topic", default="serverai/status")
    p.add_argument("--user")
    p.add_argument("--password")
    p.add_argument("--threshold", type=float, default=0.4)
    p.add_argument("--max-boxes", type=int, default=0)
    p.add_argument("--iou-threshold", type=float, default=0.5)
    p.add_argument("--classes", type=int, nargs='+')
    p.add_argument("--savedir", default="captures")
    p.add_argument("--save-images", action="store_true")
    p.add_argument("--loglevel", default="INFO",
                   choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"])
    args = p.parse_args()

    logging.basicConfig(level=getattr(logging, args.loglevel),
                        format="[%(asctime)s] %(levelname)s: %(message)s")
    os.makedirs(args.savedir, exist_ok=True)

    picam2 = Picamera2()
    imx = build_camera(picam2, Path(args.model))
    logging.info("Uploading firmware …")
    picam2.start()

    pub = connect_mqtt(args.broker, args.port, args.user, args.password)
    sub = connect_mqtt(args.broker, args.port, args.user, args.password)

    # event che si sblocca quando lo status torna idle
    idle_evt = threading.Event()

    def on_msg(c, u, m):
        if m.topic == args.status_topic and m.payload.decode() == "idle":
            idle_evt.set()
    sub.on_message = on_msg
    sub.subscribe(args.status_topic)
    sub.loop_start()

    active = []
    running = True
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, lambda *_: globals().update(running=False))

    while running:
        req = picam2.capture_request()
        frame = req.make_array("main")
        meta = req.get_metadata(); req.release()
        out = imx.get_outputs(meta)
        if out is None: continue
        boxes, scores, classes, *_ = out
        boxes = np.asarray(boxes).reshape(-1,4)
        scores = np.asarray(scores).reshape(-1)
        classes = np.asarray(classes).reshape(-1)

        dets = []
        for b, s, c in zip(boxes, scores, classes):
            if s < args.threshold: continue
            if args.classes and c not in args.classes: continue
            x1, y1, w, h = b; x2, y2 = x1+w, y1+h
            dets.append((int(c), x1, y1, x2, y2, float(s)))
        dets.sort(key=lambda x: x[5], reverse=True)
        if args.max_boxes: dets = dets[:args.max_boxes]

        # nuovo oggetto?
        new_objs = []
        for d in dets:
            c,x1,y1,x2,y2,s = d
            if not any(ac[0]==c and iou(ac[1:], (x1,y1,x2,y2))>=args.iou_threshold for ac in active):
                new_objs.append(d)
        active = [(c,x1,y1,x2,y2) for c,x1,y1,x2,y2,_ in dets]

        if not new_objs:
            continue

        # 1. pubblica detection sul broker
        pub_payload = [{"cls":c, "score":round(s,3),
                        "bbox":[int(x1),int(y1),int(x2-x1),int(y2-y1)]}
                       for c,x1,y1,x2,y2,s in new_objs]
        pub.publish(args.topic, json.dumps({"ts": time.time(), "detections": pub_payload}))
        pub.loop(0)

        # 2. salva immagine intera se richiesto
        if args.save_images:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            img_path = Path(args.savedir) / f"{ts}.jpg"
            cv2.imwrite(str(img_path), frame[...,:3])
            logging.info("Snapshot salvato: %s", img_path)

            # 3. blocca acquisizione, manda richiesta HTTP
            idle_evt.clear()
            try:
                with open(img_path, 'rb') as f:
                    resp = requests.post("http://localhost:8002/analyze",
                                         files={"file": f}, headers={"Accept":"application/json"}, timeout=120)
                    logging.info("/analyze risposta: %s", resp.status_code)
            except Exception as e:
                logging.error("Errore POST /analyze: %s", e)

            # 4. aspetta che serverai torni idle
            logging.info("Attendo status idle …")
            while running and not idle_evt.wait(0.5):
                pass  # loop finché non ricevo idle
            logging.info("Status idle ricevuto, riprendo analisi")

    logging.info("Stopping …")
    picam2.stop(); pub.disconnect(); sub.disconnect()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Unhandled error – exiting")
        sys.exit(1)
