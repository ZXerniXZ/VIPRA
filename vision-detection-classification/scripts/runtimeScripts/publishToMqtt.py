#!/usr/bin/env python3
import time
import json
import argparse
import cv2
import numpy as np
from picamera2 import Picamera2
import paho.mqtt.client as mqtt

def parse_detections(frame):
    """
    Simula il processo di inferenza.
    In un caso reale, qui esegui il modello di detection e restituisci i rilevamenti.
    In questo esempio restituiamo una dummy detection se il frame non è vuoto.
    """
    # Esempio dummy: se il frame ha almeno una dimensione > 0, restituisci una detection fittizia.
    if frame is not None and frame.size > 0:
        return [{"category": 1, "confidence": 0.95, "box": [50, 50, 100, 100]}]
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mqtt-host", type=str, default="localhost", help="Indirizzo broker MQTT")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="Porta broker MQTT")
    parser.add_argument("--mqtt-topic", type=str, default="imx500/detections", help="Topic MQTT")
    args = parser.parse_args()

    # Inizializza il client MQTT
    mqtt_client = mqtt.Client()
    try:
        mqtt_client.connect(args.mqtt_host, args.mqtt_port, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Connesso a {args.mqtt_host}:{args.mqtt_port}, topic='{args.mqtt_topic}'")
    except Exception as e:
        print("[MQTT] Errore di connessione:", e)
        return

    # Inizializza la fotocamera in modalità headless
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(buffer_count=12)
    picam2.start(config, show_preview=False)

    while True:
        frame = picam2.capture_array()
        detections = parse_detections(frame)
        payload = json.dumps({"detections": detections})
        mqtt_client.publish(args.mqtt_topic, payload)
        print(f"[MQTT] Pubblicato: {payload}")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
