FROM python:3.11

# Evita interazioni con apt
ENV DEBIAN_FRONTEND=noninteractive

# Installa OpenCV, NumPy e Picamera2 dai repository
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-opencv \
        python3-numpy \
        python3-picamera2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Installa paho-mqtt (e altre eventuali dipendenze) via pip
RUN pip install --no-cache-dir paho-mqtt

# Imposta la directory di lavoro
WORKDIR /app

# Copia il tuo script nella directory di lavoro
COPY publishToMqtt.py .

# Esegui lo script
CMD ["python", "publishToMqtt.py"]