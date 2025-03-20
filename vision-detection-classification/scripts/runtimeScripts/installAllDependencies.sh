#!/bin/bash
set -e

echo "====================================================="
echo " Installazione di tutte le dipendenze necessarie"
echo "====================================================="

# 1) Aggiorna e aggiorna i pacchetti
echo "[1/7] Aggiorno i pacchetti di sistema..."
sudo apt update
sudo apt upgrade -y

# 2) Installa Python3, pip e librerie Python base (OpenCV, NumPy)
echo "[2/7] Installo Python3, pip, OpenCV, NumPy..."
sudo apt install -y python3 python3-pip python3-opencv python3-numpy

# 3) Installa paho-mqtt (per mqttStart.py e raspMAIN.py)
echo "[3/7] Installo libreria Python paho-mqtt..."
sudo apt install python3-paho-mqtt

# 4) Installa Mosquitto (broker MQTT) e i client
echo "[4/7] Installo Mosquitto e mosquitto-clients..."
sudo apt install -y mosquitto mosquitto-clients
# Abilita e avvia Mosquitto all'avvio (opzionale)
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# 5) Installa i pacchetti per hotspot (hostapd, dnsmasq) se servono
echo "[5/7] Installo hostapd e dnsmasq per l'hotspot Wi-Fi..."
sudo apt install -y hostapd dnsmasq
# Nota: la configurazione avverrà poi con setupHotspot.sh

# 6) Installa strumenti di rete e GNOME Terminal (richiesti da checkRete.py)
echo "[6/7] Installo iputils-ping, iproute2 e gnome-terminal..."
sudo apt install -y iputils-ping iproute2 gnome-terminal

# 7) Pulizia e messaggio finale
echo "[7/7] Pulizia pacchetti non più necessari..."
sudo apt autoremove -y

echo "====================================================="
echo " Installazione completata!"
echo " - Python3, pip, OpenCV, NumPy"
echo " - paho-mqtt"
echo " - Mosquitto e mosquitto-clients"
echo " - hostapd, dnsmasq"
echo " - iputils-ping, iproute2, gnome-terminal"
echo " Ora puoi eseguire: setupHotspot.sh, checkRete.py, raspMAIN.py, mqttStart.py"
echo "====================================================="
