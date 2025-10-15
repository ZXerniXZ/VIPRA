#!/usr/bin/env python3
"""
debug_imx500_classes.py
──────────────────────────────────────────────────────────────────────────────
Script di DEBUG per IMX500 - visualizza le classi rilevate in tempo reale
Basato sul codice imx500.py originale ma semplificato per debug.
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

import numpy as np
from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500

# Mappa delle classi COCO (80 classi, 0-79)
COCO_CLASSES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
    20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
    25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite", 34: "baseball bat",
    35: "baseball glove", 36: "skateboard", 37: "surfboard", 38: "tennis racket",
    39: "bottle", 40: "wine glass", 41: "cup", 42: "fork", 43: "knife",
    44: "spoon", 45: "bowl", 46: "banana", 47: "apple", 48: "sandwich",
    49: "orange", 50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza",
    54: "donut", 55: "cake", 56: "chair", 57: "couch", 58: "potted plant",
    59: "bed", 60: "dining table", 61: "toilet", 62: "tv", 63: "laptop",
    64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave",
    69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator", 73: "book",
    74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier",
    79: "toothbrush"
}

def build_camera(picam2: Picamera2, model_path: Path) -> IMX500:
    """Inizializza e configura la camera IMX500"""
    imx = IMX500(str(model_path))
    cfg = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "XBGR8888"},
        raw={"size": (2028, 1520), "format": "SRGGB10"},
    )
    picam2.configure(cfg)
    imx.set_auto_aspect_ratio()
    return imx

def main():
    parser = argparse.ArgumentParser(description="Debug IMX500 - Mostra classi rilevate")
    parser.add_argument("--model", default="/usr/share/imx500-models/imx500_network_efficientdet_lite0_pp.rpk",
                        help="Percorso al modello .rpk")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Soglia di confidenza (default: 0.3)")
    parser.add_argument("--loglevel", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel),
        format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║              DEBUG IMX500 - Rilevamento Classi                    ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"\n📷 Modello: {Path(args.model).name}")
    print(f"🎯 Threshold: {args.threshold}")
    print(f"\n👁️  Avvio camera...\n")

    # Inizializza camera
    picam2 = Picamera2()
    imx = build_camera(picam2, Path(args.model))
    
    logging.info("Firmware upload – attendere 1-2 minuti...")
    picam2.start()
    logging.info("✅ Camera avviata!")
    
    print("\n" + "="*70)
    print("  RILEVAMENTI IN TEMPO REALE (Ctrl+C per uscire)")
    print("="*70 + "\n")

    # Handler per uscita pulita
    stop = False
    def signal_handler(sig, frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    detection_count = 0

    try:
        while not stop:
            # Cattura frame
            req = picam2.capture_request()
            meta = req.get_metadata()
            req.release()

            # Estrai detection
            outputs = imx.get_outputs(meta)
            if outputs is None:
                continue

            boxes, scores, classes, *_ = outputs
            boxes = np.asarray(boxes).reshape(-1, 4)
            scores = np.asarray(scores).reshape(-1)
            classes = np.asarray(classes).reshape(-1)

            # Filtra per threshold
            valid_detections = []
            for box, score, cls in zip(boxes, scores, classes):
                if score >= args.threshold:
                    valid_detections.append((int(cls), float(score)))

            # Stampa solo se ci sono detection
            if valid_detections:
                detection_count += 1
                timestamp = time.strftime("%H:%M:%S")
                print(f"\n🔍 Detection #{detection_count} @ {timestamp}")
                print("-" * 70)
                
                for cls_id, score in valid_detections:
                    cls_name = COCO_CLASSES.get(cls_id, f"unknown-{cls_id}")
                    confidence = score * 100
                    
                    # Emoji basato sulla classe
                    emoji = "🚗" if cls_id in [2, 3, 5, 7] else \
                            "👤" if cls_id == 0 else \
                            "🚲" if cls_id == 1 else \
                            "🚦" if cls_id in [9, 11] else "📦"
                    
                    print(f"  {emoji} Classe {cls_id:2d}: {cls_name:20s} - Confidence: {confidence:5.1f}%")
                
                print("-" * 70)

            time.sleep(0.1)  # Piccola pausa per non sovraccaricare

    except Exception as e:
        logging.error(f"Errore: {e}", exc_info=True)
    finally:
        print("\n\n🛑 Arresto camera...")
        picam2.stop()
        print("✅ Camera arrestata")
        print(f"\n📊 Totale rilevamenti: {detection_count}")

if __name__ == "__main__":
    main()


