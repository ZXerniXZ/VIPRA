# Usa un'immagine base leggera con Python
FROM python:3.10-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia il file dello script nella directory di lavoro
COPY publishToMqtt.py .

# Installa le dipendenze richieste
RUN pip install paho-mqtt opencv-python numpy picamera2

# Espone la porta MQTT (modificare se necessario)
EXPOSE 1883

# Comando per eseguire lo script
CMD ["python", "publishToMqtt.py"]
