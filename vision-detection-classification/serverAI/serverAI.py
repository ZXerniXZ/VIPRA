#!/usr/bin/env python3
"""
serverAI.py
──────────────────────────────────────────────────────────────────────────────
FastAPI + Moondream 2-B int8 + Gemma 3 1-B via Ollama
Ottimizzato per Raspberry Pi 5.
Aggiunta pubblicazione dello status su MQTT:
  • --status-topic   topic su cui pubblicare lo stato
  • --status-broker  broker MQTT per lo status (default localhost:1883)
Aggiunta pubblicazione della prediction finale su MQTT:
  • --result-topic   topic su cui pubblicare il risultato di /analyze
Lo script PUBBLICA i messaggi "idle", "processing" e "offline" sul topic di status
 e il payload JSON dei risultati sul topic di result.
Risolve l’errore "Unsupported callback API version" specificando callback_api_version=1.
"""

import os
import time
import json
import requests
from io import BytesIO
from pathlib import Path
import argparse

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import uvicorn
import paho.mqtt.client as mqtt
import moondream as md

# --------------------- CLI e configurazione ---------------------
parser = argparse.ArgumentParser("Moondream Safety-Check API with MQTT status and result")
parser.add_argument("--model", required=True,
                    help="Percorso al modello Moondream (.mf)")
parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                    help="URL base di Ollama API")
parser.add_argument("--status-broker", default="localhost",
                    help="Broker MQTT per lo status (host)")
parser.add_argument("--status-port", type=int, default=1883,
                    help="Porta MQTT per lo status")
parser.add_argument("--status-topic", default="serverai/status",
                    help="Topic MQTT per lo status")
parser.add_argument("--result-topic", default="serverai/result",
                    help="Topic MQTT per i risultati di /analyze")
parser.add_argument("--host", default="0.0.0.0",
                    help="Host per Uvicorn")
parser.add_argument("--port", type=int, default=8000,
                    help="Porta per Uvicorn")
args = parser.parse_args()

MODEL_PATH = Path(args.model)
OLLAMA_URL = args.ollama_url

# ---------------------- init modelli ----------------------
if not MODEL_PATH.exists():
    print(f"[ERROR] Moondream checkpoint mancante: {MODEL_PATH}")
    print("Scarica il modello e riposizionalo correttamente.")
    exit(1)
print("[Server] Loading Moondream …")
try:
    VL = md.vl(model=str(MODEL_PATH))
    print("  ✓ Moondream caricato con successo")
except Exception as e:
    print(f"[ERROR] Errore caricamento Moondream: {e}")
    exit(1)

LLM_NAME = "gemma3:1b"
MAX_TOKENS = 64
LLM_TOKENS = 16

# ---------------------- helper ----------------------------
def build_prompt(caption: str) -> str:
    return (
        f"{caption} given the description, is the situation dangerous? "
        "Respond only with yes or no, and a brief explanation."
    )


def run_gemma(prompt: str) -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {"model": LLM_NAME, "prompt": prompt,
               "stream": False,
               "options": {"num_predict": LLM_TOKENS, "temperature": 0.2}}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(502, f"Ollama error: {e}")
    data = resp.json()
    if "response" not in data:
        raise HTTPException(502, f"Malformed response: {data}")
    return data["response"].strip()

# ---------------------- FastAPI ---------------------------
app = FastAPI(title="Moondream Safety-Check API", version="1.0")
status_client: mqtt.Client  # per status
result_client: mqtt.Client  # per risultati

@app.on_event("startup")
async def on_startup():
    global status_client, result_client
    # Status client
    try:
        status_client = mqtt.Client(client_id="serverai-status", callback_api_version=1)
        status_client.connect(args.status_broker, args.status_port, keepalive=60)
        time.sleep(1)
        status_client.publish(args.status_topic, "idle")
    except Exception as e:
        print(f"[WARNING] Impossibile connettersi a MQTT status: {e}")
        class Dummy:
            def publish(self, *a, **k): pass
            def disconnect(self): pass
        status_client = Dummy()
    # Result client (puoi riutilizzare lo stesso broker)
    try:
        result_client = mqtt.Client(client_id="serverai-result", callback_api_version=1)
        result_client.connect(args.status_broker, args.status_port, keepalive=60)
        time.sleep(1)
    except Exception as e:
        print(f"[WARNING] Impossibile connettersi a MQTT result: {e}")
        class Dummy:
            def publish(self, *a, **k): pass
            def disconnect(self): pass
        result_client = Dummy()

@app.on_event("shutdown")
async def on_shutdown():
    status_client.publish(args.status_topic, "offline")
    status_client.disconnect()
    result_client.disconnect()

@app.get("/ping")
async def ping():
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return {"status": "ok"}
    except:
        return {"status": "ollama-unreachable"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    status_client.publish(args.status_topic, "processing")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        status_client.publish(args.status_topic, "idle")
        raise HTTPException(415, "File must be an image")
    raw = await file.read()
    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except:
        status_client.publish(args.status_topic, "idle")
        raise HTTPException(400, "Invalid image data")

    t0 = time.perf_counter()
    enc = VL.encode_image(img)
    caption = VL.caption(enc, length="short", settings={"max_tokens": MAX_TOKENS})["caption"]
    tc = time.perf_counter()

    verdict = run_gemma(build_prompt(caption))
    tr = time.perf_counter()

    # Prepare payload
    result = {
        "caption": caption,
        "verdict": verdict,
        "latency": {
            "encode_sec": round(tc - t0, 3),
            "llm_sec":    round(tr - tc, 3),
            "total_sec":  round(tr - t0, 3),
        },
    }
    # Publish result
    result_client.publish(args.result_topic, json.dumps(result))
    # Back to idle
    status_client.publish(args.status_topic, "idle")
    return JSONResponse(result)

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port, reload=False)
