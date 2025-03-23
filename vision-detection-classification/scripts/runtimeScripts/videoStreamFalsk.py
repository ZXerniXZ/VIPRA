#!/usr/bin/env python3
import time
import cv2
import numpy as np
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

# Inizializza la fotocamera in modalità headless
picam2 = Picamera2()
config = picam2.create_preview_configuration(buffer_count=12)
picam2.start(config, show_preview=False)

def gen_frames():
    """Genera frame JPEG per lo streaming MJPEG."""
    while True:
        # Cattura un frame
        frame = picam2.capture_array()
        # (Opzionale: puoi eseguire qui inferenze e disegnare bounding box sul frame)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        # Restituisce il frame in formato MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    """Endpoint che serve il feed video MJPEG."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Avvia il server Flask sulla porta 5000, accessibile da altri dispositivi
    app.run(host="0.0.0.0", port=5000)
