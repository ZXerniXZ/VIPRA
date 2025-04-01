#!/bin/bash

# Configurazione dell'indirizzo IP statico
INTERFACE="eth0"  # Cambia in "wlan0" se usi Wi-Fi
STATIC_IP="192.168.1.100"
GATEWAY="192.168.1.1"
NETMASK="255.255.255.0"

echo "Assegnando IP statico $STATIC_IP a $INTERFACE..."

# Esegui comandi per impostare l'IP statico
sudo ip addr flush dev $INTERFACE
sudo ip addr add $STATIC_IP/$NETMASK dev $INTERFACE
sudo ip route add default via $GATEWAY

echo "IP statico impostato con successo."