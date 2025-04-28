# Dockerfile per IMX500 object detection via Picamera2 + MQTT

FROM --platform=linux/arm64 python:3.12-slim AS base

# 1) Dipendenze di sistema per Picamera2 e OpenCV
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
        build-essential wget ca-certificates \
        libatlas-base-dev libjpeg-dev libtiff5-dev libturbojpeg0-dev \
        libv4l-dev v4l-utils libopenjp2-7-dev libexif-dev \
        libcamera-apps python3-opencv python3-picamera2 \
    && rm -rf /var/lib/apt/lists/*

# 2) Variabili ambiente Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 3) Installa dipendenze Python
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# 4) Copia il codice dell'applicazione
COPY . /app

# 5) Entry point
ENTRYPOINT ["python3", "main.py"]
