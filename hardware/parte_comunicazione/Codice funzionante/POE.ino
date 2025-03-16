#include <PicoMQTT.h>
#include <ETH.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

#define RXp1 2
#define TXp2 4

static bool eth_connected = false;
uint16_t mqttPort = 9000;

PicoMQTT::Server mqtt(mqttPort);

// Coda per i messaggi ricevuti da Serial1
QueueHandle_t xQueue;

void serialReceiveTask(void *pvParameters);
void mqttTask(void *pvParameters);
void ethMonitorTask(void *pvParameters);

void setup() {
  Serial.setTimeout(100);
  Serial1.setTimeout(100);
  Serial2.setTimeout(100);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);
  Serial2.begin(115200, SERIAL_8N1, -1, TXp2);

  delay(100);

  Serial.print("Setup...\n");

  // Configurazione Ethernet
  Serial.print("Configuring Ethernet...\n");
  ETH.begin();
  ETH.config(IPAddress(192, 168, 1, 50), IPAddress(192, 168, 1, 150), IPAddress(255, 255, 255, 0));
  NETsetup();
  Serial.print("Network configuration done\n");

  // Avvio del server MQTT
  Serial.print("Starting MQTT server...\n");
  mqtt.begin();
  Serial.print("MQTT server started\n");
  mqtt.subscribe("MESSAGGI PER SCHEDA OUT", messageReceived);
  Serial.print("MQTT subscribe done...\n");

  // Creazione della coda per i messaggi
  xQueue = xQueueCreate(10, sizeof(String));

  // Creazione dei task con assegnazione esplicita dei core
  xTaskCreatePinnedToCore(serialReceiveTask, "SerialReceive", 10000, NULL, 2, NULL, 0); // Core 0, priorità alta
  xTaskCreatePinnedToCore(mqttTask, "MQTT", 10000, NULL, 1, NULL, 1);              // Core 1, priorità media
  xTaskCreatePinnedToCore(ethMonitorTask, "ETHMonitor", 10000, NULL, 1, NULL, 0); // Core 0, priorità media
}

void serialReceiveTask(void *pvParameters) {
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

void mqttTask(void *pvParameters) {
  while (true) {

    String messaggio;

    // Ricevi il messaggio dalla coda
    if (uxQueueMessagesWaiting(xQueue) > 0) {
      if (xQueueReceive(xQueue, &messaggio, 0) == pdTRUE) {
      mqtt.publish("MESSAGGI DA SCHEDA IN", messaggio);
      }
    }
    mqtt.loop();
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void ethMonitorTask(void *pvParameters) {
  while (true) {
    if (!ETH.linkUp() || ETH.localIP() == IPAddress(0, 0, 0, 0)) {
      Serial.println("ETH Disconnected or IP lost\nReconnecting...");
      eth_connected = false;
      NETsetup();
    }
    vTaskDelay(1000 / portTICK_PERIOD_MS);
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
  Serial.print("Received message: ");
  Serial.println(payload);
  Serial2.println(payload);
}

void NETsetup() {
  while (!ETH.linkUp()) {
    Serial.println("Waiting for Ethernet link...");
    delay(1000);
  }

  Serial.println("ETH Connected");
  eth_connected = true;

  while (ETH.localIP() == IPAddress(0, 0, 0, 0)) {
    Serial.println("Waiting for IP address...");
    delay(1000);
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

void loop() {}