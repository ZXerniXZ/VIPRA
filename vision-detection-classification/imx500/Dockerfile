FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1         
# <‑‑ abilita pip nei post‑install

RUN apt-get update && apt-get install -y wget gnupg ca-certificates \
 && echo "deb http://archive.raspberrypi.com/debian/ bookworm main" \
        > /etc/apt/sources.list.d/raspi.list \
 && wget -qO - https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \
        | gpg --dearmor -o /etc/apt/trusted.gpg.d/raspberrypi.gpg

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip \
        python3-opencv python3-picamera2 imx500-all \
        python3-paho-mqtt \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY imx500/imx500Detection.py /app/

ENTRYPOINT ["python3", "/app/imx500Detection.py"]

CMD ["--model", "/usr/share/imx500-models/imx500_network_efficientdet_lite0_pp.rpk", "--broker", "localhost", "--topic", "ai/camera", "--max-boxes", "1"]

