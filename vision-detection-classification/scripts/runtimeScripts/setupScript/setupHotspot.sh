#!/bin/bash

# CONFIGURAZIONE - MODIFICA QUESTI VALORI SE NECESSARIO
SSID="MyRaspberryAP"
WPA_PASS="raspberry123"
IP_ADDRESS="192.168.4.1"
SUBNET="192.168.4.0"
RANGE_START="192.168.4.2"
RANGE_END="192.168.4.20"

echo "🔹 Disattivazione temporanea dei servizi..."
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq

echo "🔹 Configurazione dell'IP statico per wlan0..."
sudo bash -c "cat <<EOF >> /etc/dhcpcd.conf
interface wlan0
static ip_address=$IP_ADDRESS/24
nohook wpa_supplicant
EOF"

echo "🔹 Riavvio del servizio DHCP..."
sudo systemctl restart dhcpcd

echo "🔹 Configurazione del server DHCP (dnsmasq)..."
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
sudo bash -c "cat <<EOF > /etc/dnsmasq.conf
interface=wlan0
dhcp-range=$RANGE_START,$RANGE_END,255.255.255.0,24h
EOF"

echo "🔹 Configurazione del Wi-Fi Access Point (hostapd)..."
sudo bash -c "cat <<EOF > /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=$SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$WPA_PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF"

echo "🔹 Collegamento del file di configurazione di hostapd..."
sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

echo "🔹 Attivazione del Wi-Fi Access Point..."
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl start hostapd
sudo systemctl restart dnsmasq

echo "✅ Configurazione completata!"
echo "🔹 Ora puoi connetterti alla rete Wi-Fi: $SSID"
echo "🔹 Password: $WPA_PASS"
