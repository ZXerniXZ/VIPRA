#include <PicoMQTT.h>
#include <ETH.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <ESPping.h>

#define RXp1 2
#define TXp2 4

static bool eth_connected = false;
uint16_t mqttPort = 9000;
static String topic = "imx500/detections";

PicoMQTT::Client mqtt("192.168.1.100", 9000);

TaskHandle_t 
  SerialReceiveTask, // Ricezione e invio dati in seriale
  MqttTask,          // Connessione al server MQTT
  EthMonitorTask;    // Monitor per eventi di connessione ethernet


// Creazione della coda per i messaggi
QueueHandle_t xQueue = xQueueCreate(10, sizeof(char) * 128);

void setup() {

  delay(100);

  // Configurazione Seriale
  setupSeriale();

  // Configurazione Ethernet
  setupEthernet();

  // Configurazione MQTT
  setupMQTT();

  // Creazione dei task con assegnazione esplicita dei core
  Serial.println("Creating tasks...");
    xTaskCreatePinnedToCore(
      serialReceiveTask, // Nome funzione
      "SerialReceive", // Nome task
      10240, // Dimensione stack
      NULL,  // Parametri
      1,  // Priorità
      &SerialReceiveTask,  // Task handle
      0)  // Core
    ;
    
    xTaskCreatePinnedToCore(
      mqttTask, // Nome funzione
      "MQTT", // Nome task
      10240, // Dimensione stack
      NULL,  // Parametri
      2,  // Priorità
      &MqttTask,  // Task handle
      1)   // Core
    ;  
  
    xTaskCreatePinnedToCore(
      ethMonitorTask, // Nome funzione
      "ETHMonitor", // Nome task
      10240, // Dimensione stack
      NULL,  // Parametri
      0,  // Priorità
      &EthMonitorTask,  // Task handle
      0)  // Core
    ;  

  Serial.println("Tasks created");

  Serial.println("Setup done");
}

void serialReceiveTask(void * parameter) {
  while (true) {

    String messaggio = loraReceiveStringSerial1();
    
    if (messaggio.length() >= 1) {
      Serial.println("Messaggio ricevuto da scheda IN: " + messaggio);

      // Invia il messaggio alla coda
      if (xQueueSend(xQueue, &messaggio, portMAX_DELAY) != pdTRUE) {
        Serial.println("Errore: coda piena!");
      }
    }
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void mqttTask(void * parameter) {
  while (true) {

    String messaggio;
    if (uxQueueMessagesWaiting(xQueue) > 0) {
      if (xQueueReceive(xQueue, &messaggio, 0) == pdTRUE) {
      mqtt.publish("MESSAGGI DA SCHEDA IN", messaggio);
      }
    }
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void ethMonitorTask(void * parameter) {
  while (true) {
    
    if (!ETH.linkUp() || ETH.localIP() == IPAddress(0, 0, 0, 0)) {
      Serial.println("ETH Disconnected or IP lost\nReconnecting...");
      eth_connected = false;
      NETsetup();
    }
    vTaskDelay(3000 / portTICK_PERIOD_MS);
  }
}

String loraReceiveStringSerial1() {
  String messaggio = Serial1.readString();
  messaggio.trim();
  if (messaggio.length() >= 1) {
    return messaggio;
  } else {
    return "";
  }
}

void messageReceived(String topic, String payload) {
  Serial.print("Messaggio ricevuto: ");
  Serial.println(payload);
  Serial2.println(payload);
}

void NETsetup() {
  while (!ETH.linkUp()) {
    Serial.println("Waiting for Ethernet link...");
    delay(3000);
  }

  Serial.println("ETH Connected");
  eth_connected = true;

  while (ETH.localIP() == IPAddress(0, 0, 0, 0)) {
    Serial.println("Waiting for IP address...");
    delay(3000);
  }

  Serial.print("Got an IP Address for ETH MAC: ");
  Serial.print(ETH.macAddress());
  Serial.print(", IPv4: ");
  Serial.print(ETH.localIP());
  if (ETH.fullDuplex()) {
    Serial.print(", FULL_DUPLEX");
  }
  Serial.print(", ");
  Serial.print(ETH.linkSpeed());
  Serial.println("Mbps");
}

void setupSeriale(){

  Serial.setTimeout(100);
  Serial1.setTimeout(100);
  Serial2.setTimeout(100);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);
  Serial2.begin(115200, SERIAL_8N1, -1, TXp2);

  Serial.println("Serial configuration done...");
}

void setupEthernet(){

  Serial.println("Configuring Ethernet...");
  ETH.begin();
  ETH.config(IPAddress(192, 168, 1, 50), IPAddress(-1, -1, -1, -1), IPAddress(255, 255, 255, 0));
  NETsetup();
  Serial.println("Network configuration done...");

}

void setupMQTT(){

  Serial.println("Configuring MQTT connection...");
  const IPAddress remote_ip(192,168,1,100);
  if (Ping.ping(remote_ip)) {
    Serial.println("ESP32 → PC: Ping OK!");
  } else {
    Serial.println("ESP32 → PC: Ping FAILED!");
  }

  mqtt.subscribe(topic, messageReceived);

  Serial.println("Connected to server: "+mqtt.host+"\nPort: "+mqtt.port);
  mqtt.subscribe(topic, messageReceived);
  Serial.print("MQTT subscribe at ["+topic+"] topic done\n");
  Serial.println("MQTT connection setup done");
  
}

void loop() {}