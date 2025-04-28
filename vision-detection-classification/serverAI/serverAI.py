"""
FastAPI + Moondream 2-B int8 + Gemma 3 1-B via Ollama
Ottimizzato per Raspberry Pi 5.
"""

import os, time, requests
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import moondream as md
import uvicorn

# --------------------- configurazione ---------------------
MODEL_PATH = Path("models/moondream-2b-int8.mf")
LLM_NAME   = "gemma3:1b"
MAX_TOKENS = 64
LLM_TOKENS = 16
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")

# ---------------------- init modelli ----------------------
try:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Moondream checkpoint mancante: {MODEL_PATH}")

    print("[Server] Loading Moondream …")
    try:
        print("caricamento")
        VL = md.vl(model=str(MODEL_PATH))
        print("  ↳ Moondream caricato con successo\n")
    except Exception as e:
        raise RuntimeError(f"Errore nel caricamento del modello Moondream: {str(e)}")

except FileNotFoundError as e:
    print(f"[ERROR] {str(e)}")
    print("Per favore scarica il modello da: https://huggingface.co/vikhyatk/moondream2/resolve/main/moondream-2b-int8.mf")
    print("E posizionalo in: ./models/moondream-2b-int8.mf")
    exit(1)
except Exception as e:
    print(f"[ERROR] Errore critico nell'inizializzazione: {str(e)}")
    exit(1)

# ---------------------- helper ----------------------------
def build_prompt(caption: str) -> str:
    return (
        f"{caption} given the description, is the situation dangerous for the driver or other car on the road? "
        "A dangerous situation could be: bikes on the road, debris on the road, crashes, dangerous overtaking. "
        "Respond only with yes or no, and a brief explanation of why."
    )

def run_gemma(prompt: str) -> str:
    """Chiama /api/generate su Ollama e restituisce la risposta."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model":  LLM_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": LLM_TOKENS,
            "temperature": 0.2
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # 502 Bad Gateway dal tuo server → Ollama ha risposto male
        raise HTTPException(
            status_code=502,
            detail=f"Ollama HTTP {resp.status_code}: {resp.text}"
        ) from e
    except requests.exceptions.RequestException as e:
        # timeout, connessione rifiutata, DNS fallito…
        raise HTTPException(
            status_code=502,
            detail=f"Errore di rete verso Ollama: {e}"
        ) from e

    data = resp.json()
    # In tutte le versioni /api/generate restituisce "response"
    if "response" not in data:
        # log completo per debug
        raise HTTPException(
            status_code=502,
            detail=f"Ollama response malformato: {data}"
        )
    return data["response"].strip()


# ---------------------- FastAPI ---------------------------
app = FastAPI(title="Moondream Safety-Check API", version="1.0")

@app.get("/ping")
async def ping():
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        status = "ok"
    except Exception:
        status = "ollama-unreachable"
    return {"status": status}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "File must be an image")

    raw = await file.read()
    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Invalid image data")

    t0 = time.perf_counter()
    enc = VL.encode_image(img)
    caption = VL.caption(enc, length="short", settings={"max_tokens": MAX_TOKENS})["caption"]
    tc = time.perf_counter()

    verdict = run_gemma(build_prompt(caption))
    tr = time.perf_counter()

    return JSONResponse(
        {
            "caption": caption,
            "verdict": verdict,
            "latency": {
                "encode_sec": round(tc - t0, 3),
                "llm_sec":    round(tr - tc, 3),
                "total_sec":  round(tr - t0, 3),
            },
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
