#!/usr/bin/env python3
"""
serverAI_qwen_optimized.py
──────────────────────────────────────────────────────────────────────────────
FastAPI + Qwen2.5:3B (via Ollama) OTTIMIZZATO per Raspberry Pi 5.
• Prompt più breve e diretto
• Processing immagini ottimizzato
• Configurazione Ollama ottimizzata
• Timeout ridotti
"""

import os, time, json, argparse, requests
from io import BytesIO
from pathlib import Path
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import uvicorn
import paho.mqtt.client as mqtt

# ──────── CLI / configurazione ────────────────────────────────────────────
parser = argparse.ArgumentParser("Qwen2.5 Safety‑Check API with MQTT - OPTIMIZED")
parser.add_argument("--ollama-url",     default=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
parser.add_argument("--status-broker",  default="localhost")
parser.add_argument("--status-port",    type=int, default=1883)
parser.add_argument("--status-topic",   default="serverai/status")
parser.add_argument("--result-topic",   default="serverai/result")
parser.add_argument("--host",           default="0.0.0.0")
parser.add_argument("--port",           type=int, default=8000)
parser.add_argument("--mqtt-enabled",   action="store_true", help="Enable MQTT functionality")
args = parser.parse_args()

OLLAMA_URL = args.ollama_url

# ──────── configurazione Qwen2.5 OTTIMIZZATA ───────────────────────────────
LLM_NAME, MAX_TOKENS = "qwen2.5vl:3b", 16  # Ridotto da 32 a 16

def build_prompt() -> str:
    """Prompt ottimizzato - più breve e diretto"""
    return """You are a **Driver Safety Assistant**.  
You are given a **dashcam image** showing a real driving scene.  
Your task is to decide if the situation is **SAFE** or **DANGEROUS**.  

If it is **DANGEROUS**, classify it into **one** of the following danger types:  
- `TREE_ON_ROAD` — fallen tree or large branch blocking the road  
- `DEBRIS_ON_ROAD` — obstacles, objects, or debris obstructing the road  
- `PEDESTRIAN_ON_ROAD` — person walking, standing, or crossing on the road  
- `BICYCLE_ON_ROAD` — bicycle or cyclist posing a collision risk  
- `ACCIDENT_ON_ROAD` — crash, collision, or disabled vehicle on the road  

**Output format (strictly):**  
- `[SAFE]`  
- `[DANGEROUS, CLASS_NAME]`

**Rules:**  
- Output **only one** label in the exact format above.  
- A scene is **DANGEROUS** if there is any collision, obstacle, or person/vehicle blocking or entering the roadway.  
- Do **not** add explanations or extra text.
"""

def image_to_base64_optimized(image: Image.Image) -> str:
    """Conversione immagine ottimizzata"""
    # Ridimensiona l'immagine per ridurre i dati
    if image.width > 512 or image.height > 512:
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
    
    buffer = BytesIO()
    # Qualità ridotta per file più piccoli
    image.save(buffer, format="JPEG", quality=70, optimize=True)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

def run_qwen25VL_optimized(prompt: str, image: Image.Image) -> str:
    """Run Qwen2.5 vision-language model via Ollama - OTTIMIZZATO"""
    img_base64 = image_to_base64_optimized(image)
    
    # Configurazione ottimizzata per ARM/Raspberry Pi
    r = requests.post(f"{OLLAMA_URL}/api/generate",
                      json={"model": LLM_NAME,
                            "prompt": prompt,
                            "images": [img_base64],
                            "stream": False,
                            "options": {
                                "num_predict": MAX_TOKENS, 
                                "temperature": 0.0,  # Deterministico per velocità
                                "top_p": 0.9,       # Riduce la complessità
                                "repeat_penalty": 1.1,
                                "num_ctx": 2048,    # Ridotto da default
                                "num_thread": 4,    # Ottimizzato per 4 core
                                "num_batch": 1,     # Ridotto per ARM
                            }},
                      timeout=130)  # Timeout ridotto da 120 a 30 secondi
    r.raise_for_status()
    data = r.json()
    if "response" not in data:
        raise HTTPException(502, f"Malformed response: {data}")
    return data["response"].strip()

# ──────── MQTT Setup ─────────────────────────────────────────────────────
status_client: mqtt.Client = None
result_client: mqtt.Client = None

def setup_mqtt_clients():
    """Setup MQTT clients with error handling"""
    global status_client, result_client
    
    try:
        # client MQTT per lo status
        status_client = mqtt.Client(
            client_id="serverai-status",
            protocol=mqtt.MQTTv311,
        )
        status_client.connect(args.status_broker, args.status_port, keepalive=60)
        status_client.loop_start()
        status_client.publish(args.status_topic, "idle", qos=1)
        print(f"[MQTT] Status client connected to {args.status_broker}:{args.status_port}")

        # client MQTT per i risultati
        result_client = mqtt.Client(
            client_id="serverai-result",
            protocol=mqtt.MQTTv311,
        )
        result_client.connect(args.status_broker, args.status_port, keepalive=60)
        result_client.loop_start()
        print(f"[MQTT] Result client connected to {args.status_broker}:{args.status_port}")
        
    except Exception as e:
        print(f"[MQTT] Warning: Could not connect to MQTT broker: {e}")
        print("[MQTT] Continuing without MQTT functionality...")
        status_client = None
        result_client = None

def cleanup_mqtt_clients():
    """Cleanup MQTT clients"""
    global status_client, result_client
    
    if status_client:
        try:
            status_client.publish(args.status_topic, "offline", qos=1)
            status_client.loop_stop()
            status_client.disconnect()
            print("[MQTT] Status client disconnected")
        except:
            pass
    
    if result_client:
        try:
            result_client.loop_stop()
            result_client.disconnect()
            print("[MQTT] Result client disconnected")
        except:
            pass

def publish_mqtt(topic: str, message: str, qos: int = 1):
    """Publish MQTT message with error handling"""
    client = status_client if "status" in topic else result_client
    if client:
        try:
            client.publish(topic, message, qos=qos)
        except Exception as e:
            print(f"[MQTT] Warning: Failed to publish to {topic}: {e}")

# ──────── FastAPI Lifespan ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[Server] Starting up...")
    if args.mqtt_enabled:
        setup_mqtt_clients()
    else:
        print("[MQTT] MQTT disabled by configuration")
    yield
    # Shutdown
    print("[Server] Shutting down...")
    cleanup_mqtt_clients()

app = FastAPI(title="serverAI-optimized", version="1.2", lifespan=lifespan)

@app.get("/ping")
async def ping():
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return {"status": "ok", "mqtt_enabled": args.mqtt_enabled}
    except Exception:
        return {"status": "ollama‑unreachable", "mqtt_enabled": args.mqtt_enabled}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    publish_mqtt(args.status_topic, "processing", qos=1)

    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        publish_mqtt(args.status_topic, "idle", qos=1)
        raise HTTPException(415, "File must be an image")

    raw = await file.read()
    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        publish_mqtt(args.status_topic, "idle", qos=1)
        raise HTTPException(400, "Invalid image data")

    t0 = time.perf_counter()
    prompt = build_prompt()
    analysis = run_qwen25VL_optimized(prompt, img)
    latency = round(time.perf_counter() - t0, 3)

    # Parse ottimizzato della risposta
    analysis_upper = analysis.upper()
    if "DANGEROUS" in analysis_upper:
        verdict = "dangerous"
        # Estrai spiegazione più intelligente
        parts = analysis.split(":", 1)
        explanation = parts[1].strip() if len(parts) > 1 else analysis
    elif "SAFE" in analysis_upper:
        verdict = "safe"
        parts = analysis.split(":", 1)
        explanation = parts[1].strip() if len(parts) > 1 else analysis
    else:
        # Fallback parsing
        verdict = "unknown"
        explanation = analysis

    result = {"analysis": analysis,
              "verdict": verdict,
              "explanation": explanation,
              "latency_sec": latency}

    publish_mqtt(args.result_topic, json.dumps(result), qos=1)
    publish_mqtt(args.status_topic, "idle", qos=1)
    return JSONResponse(result)

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)
