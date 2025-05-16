#!/usr/bin/env python3
"""
serverAI.py
──────────────────────────────────────────────────────────────────────────────
FastAPI + Moondream 2‑B int8 + Gemma‑3 1‑B (via Ollama) ottimizzato per Raspberry Pi 5.
• Pubblica sul topic di stato  (idle | processing | offline) con QoS 1
• Pubblica il risultato JSON dell’analisi su un topic dedicato   con QoS 1
"""

import os, time, json, argparse, requests
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import uvicorn
import paho.mqtt.client as mqtt
import moondream as md

# ──────── CLI / configurazione ────────────────────────────────────────────
parser = argparse.ArgumentParser("Moondream Safety‑Check API with MQTT")
parser.add_argument("--model",          required=True,  help="Percorso modello .mf")
parser.add_argument("--ollama-url",     default=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
parser.add_argument("--status-broker",  default="localhost")
parser.add_argument("--status-port",    type=int, default=1883)
parser.add_argument("--status-topic",   default="serverai/status")
parser.add_argument("--result-topic",   default="serverai/result")
parser.add_argument("--host",           default="0.0.0.0")
parser.add_argument("--port",           type=int, default=8000)
args = parser.parse_args()

MODEL_PATH = Path(args.model)
OLLAMA_URL = args.ollama_url

# ──────── carica Moondream ───────────────────────────────────────────────
if not MODEL_PATH.exists():
    raise SystemExit(f"[ERROR] Modello mancante: {MODEL_PATH}")
print("[Server] Loading Moondream …")
VL = md.vl(model=str(MODEL_PATH))
print("  ✓ Moondream caricato")

LLM_NAME, MAX_TOKENS, LLM_TOKENS = "gemma3:1b", 64, 16

def build_prompt(caption: str) -> str:
    return (f"{caption} given the description, is the situation dangerous? "
            "Respond only with yes or no, and a brief explanation.")

def run_gemma(prompt: str) -> str:
    r = requests.post(f"{OLLAMA_URL}/api/generate",
                      json={"model": LLM_NAME,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"num_predict": LLM_TOKENS, "temperature": 0.2}},
                      timeout=60)
    r.raise_for_status()
    data = r.json()
    if "response" not in data:
        raise HTTPException(502, f"Malformed response: {data}")
    return data["response"].strip()

# ──────── FastAPI & MQTT ─────────────────────────────────────────────────
app = FastAPI(title="Moondream Safety‑Check API", version="1.0")
status_client: mqtt.Client
result_client: mqtt.Client

@app.on_event("startup")
async def startup() -> None:
    global status_client, result_client

    # client MQTT per lo status
    status_client = mqtt.Client(
        client_id="serverai-status",
        callback_api_version=1,
        transport="tcp",
        protocol=mqtt.MQTTv311,
    )
    status_client.connect(args.status_broker, args.status_port, keepalive=60)
    status_client.loop_start()                  # thread di rete
    status_client.publish(args.status_topic, "idle", qos=1)

    # client MQTT per i risultati
    result_client = mqtt.Client(
        client_id="serverai-result",
        callback_api_version=1,
        transport="tcp",
        protocol=mqtt.MQTTv311,
    )
    result_client.connect(args.status_broker, args.status_port, keepalive=60)
    result_client.loop_start()

@app.on_event("shutdown")
async def shutdown() -> None:
    status_client.publish(args.status_topic, "offline", qos=1)
    status_client.loop_stop()
    status_client.disconnect()

    result_client.loop_stop()
    result_client.disconnect()

@app.get("/ping")
async def ping():
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return {"status": "ok"}
    except Exception:
        return {"status": "ollama‑unreachable"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    status_client.publish(args.status_topic, "processing", qos=1)

    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        status_client.publish(args.status_topic, "idle", qos=1)
        raise HTTPException(415, "File must be an image")

    raw = await file.read()
    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        status_client.publish(args.status_topic, "idle", qos=1)
        raise HTTPException(400, "Invalid image data")

    t0 = time.perf_counter()
    enc     = VL.encode_image(img)
    caption = VL.caption(enc, length="short",
                         settings={"max_tokens": MAX_TOKENS})["caption"]
    verdict = run_gemma(build_prompt(caption))
    latency = round(time.perf_counter() - t0, 3)

    result = {"caption": caption,
              "verdict": verdict,
              "latency_sec": latency}

    result_client.publish(args.result_topic, json.dumps(result), qos=1)
    status_client.publish(args.status_topic, "idle", qos=1)
    return JSONResponse(result)

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)
