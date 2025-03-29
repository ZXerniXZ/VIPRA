const mqtt = require('mqtt');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());

const mqttBroker = 'mqtt://192.168.1.100:1883';
const client = mqtt.connect(mqttBroker);

let lastMessage = '';
let isConnected = false;

client.on('connect', () => {
    console.log('✅ Connesso al broker MQTT');
    isConnected = true;
    client.subscribe('heartbeat/servermqtt');
});

client.on('message', (topic, message) => {
    lastMessage = message.toString();
    console.log(`📩 Messaggio ricevuto: ${lastMessage}`);
});

client.on('error', (err) => {
    console.error('❌ Errore MQTT:', err);
    isConnected = false;
});

app.get('/message', (req, res) => {
    res.json({ message: lastMessage });
});

app.get('/status', (req, res) => {
    res.json({ connected: isConnected });
});

const PORT = 5000;
app.listen(PORT, () => {
    console.log(`🚀 Server API in esecuzione su http://localhost:${PORT}`);
});
