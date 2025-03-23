#!/usr/bin/env python3
import time
from flask import Flask, Response
import cv2
from picamera2 import Picamera2, MappedArray

app = Flask(__name__)

# Inizializza la fotocamera (Picamera2)
picam2 = Picamera2()
# Crea una configurazione di anteprima (modifica se necessario)
config = picam2.create_preview_configuration()
# Avvia la camera in modalità headless (senza mostrare una finestra di anteprima)
picam2.start(config, show_preview=False)

def gen_frames():
    """Genera frame JPEG dal feed della camera e li serve in streaming MJPEG."""
    while True:
        # Acquisizione del frame come array NumPy
        frame = picam2.capture_array()
        
        # (Opzionale) Aggiungi qui la tua logica per disegnare bounding box o annotazioni
        # Ad esempio:
        # cv2.putText(frame, "Hello, world!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Codifica il frame in formato JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        # Restituisci il frame in formato multipart MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        # Regola il delay se necessario (ad esempio, 0.1 secondi)
        time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    """Endpoint che serve il feed video."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Avvia l'app Flask, rendendola accessibile su tutte le interfacce sulla porta 5000
    app.run(host="0.0.0.0", port=5000)
