#!/bin/bash

echo "Aggiornamento dei pacchetti..."
sudo apt update -y

echo "Installazione delle dipendenze Python..."
sudo apt install -y python3 python3-pip python3-venv

echo "Installazione delle librerie Python tramite APT..."
sudo apt install -y python3-paho-mqtt python3-opencv python3-numpy python3-picamera2

echo "Installazione delle dipendenze per il Wi-Fi Hotspot..."
sudo apt install -y hostapd dnsmasq dhcpcd5 iw iptables

echo " nstallazione di Node.js e npm..."
sudo apt install -y nodejs npm

echo "Installazione dell'ultima versione di Node.js tramite NVM..."
sudo curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash
source ~/.bashrc
sudo nvm install node

echo "installazione di Create React App..."
sudo npm install -g create-react-app

echo "Installazione di librerie aggiuntive per React..."
sudo npm install react-router-dom axios styled-components @shadcn/ui lucide-react recharts

echo "assegno permessi a setupHotspot.sh..."
sudo chmod +x ~/setupHotspot.sh

echo "Installazione completata!"
