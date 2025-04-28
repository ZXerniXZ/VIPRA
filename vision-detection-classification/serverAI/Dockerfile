# ---- 1. Base image ----------------------------------------------------------
FROM python:3.12-slim  AS base

# ---- 2. System deps ---------------------------------------------------------
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
        build-essential wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ---- 3. Python deps ---------------------------------------------------------
COPY serverAI/requirements.txt /tmp/req.txt
RUN pip install --upgrade pip && pip install -r /tmp/req.txt

# ---- 4. App code & models ---------------------------------------------------
WORKDIR /app
COPY serverAI/ /app

# ---- 5. Runtime settings ----------------------------------------------------
ENV OMP_NUM_THREADS=4 \
    OMP_WAIT_POLICY=PASSIVE

EXPOSE 8000
ENTRYPOINT ["python", "serverAI.py"]
