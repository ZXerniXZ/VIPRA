# Dockerfile per serverAI con Qwen2.5VL
FROM python:3.11-slim-bookworm

WORKDIR /app

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt .

# Installa dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia lo script serverAI
COPY serverAI_qwen_optimized.py .

# Esponi la porta
EXPOSE 8000

# Comando di default (può essere sovrascritto da docker-compose)
ENTRYPOINT ["python", "serverAI_qwen_optimized.py"]

