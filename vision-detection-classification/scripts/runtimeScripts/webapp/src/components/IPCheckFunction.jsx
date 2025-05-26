import React, { useState, useEffect } from 'react';
import BootstrapButton from 'react-bootstrap/Button';
import 'bootstrap/dist/css/bootstrap.min.css';
import LogText from './LogText';

const ButtonCheck = () => {
    const [status, setStatus] = useState(null);
    const [currentIP, setCurrentIP] = useState("192.168.1.100");
    const [messages, setMessages] = useState([]);
    const [lastMessage, setLastMessage] = useState("");
    const serverUrl = "http://localhost:5000";

    useEffect(() => {
        const fetchMessage = async () => {
            try {
                const response = await fetch(`${serverUrl}/message`);
                const data = await response.json();
                const newMessage = `MQTT: ${data.message}`;
                
                if (newMessage !== lastMessage) {
                    setLastMessage(newMessage);
                    setMessages(prev => [...prev, newMessage]);
                }
                
            } catch (error) {
                console.error("Errore nel recupero del messaggio MQTT:", error);
            }
        };

        const interval = setInterval(fetchMessage, 2000);
        return () => clearInterval(interval);
    }, [lastMessage]);

    const connectToServer = async () => {
        try {
            const response = await fetch(`${serverUrl}/status`);
            const data = await response.json();
            setStatus(data.connected);
        } catch (error) {
            console.error("Errore nella connessione al server MQTT:", error);
            setStatus(false);
        }
    };

    return (
        <div>
            <LogText ip={currentIP} />
            
            <BootstrapButton variant="outline-success" onClick={connectToServer}>
                Connetti al Server MQTT
            </BootstrapButton>
            {status !== null && (
                <p className="mt-2">
                    Stato: {status ? "Connesso al Broker MQTT ✅" : "Non Connesso ❌"}
                </p>
            )}
            <div className="mt-3">
                <h4>Messaggi Ricevuti:</h4>
                <p>Ultimo messaggio: {lastMessage}</p>
                <ul>
                    {messages.map((msg, index) => (
                        <li key={index}>{msg}</li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default ButtonCheck;