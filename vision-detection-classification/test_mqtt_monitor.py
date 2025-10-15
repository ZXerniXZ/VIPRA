#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connesso a MQTT (rc={rc})")
    client.subscribe("serverai/#")
    client.subscribe("ai/camera")

def on_message(client, userdata, msg):
    print(f"📩 [{msg.topic}] {msg.payload.decode()}")

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message

print("🔌 Connessione a localhost:9000...")
client.connect("localhost", 9000, 60)
print("👂 In ascolto...\n")
client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Chiusura...")
    client.loop_stop()
    client.disconnect()

