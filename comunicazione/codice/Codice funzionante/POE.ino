#include <PicoMQTT.h>
#include <ETH.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <ESPping.h>

#define RXp1 36
#define TXp2 4


////////////////////
//    COSTANTI    //
////////////////////

#define mqttPort 9000
#define mqttHost "192.168.1.101"
#define DIMENSIONE_MASSIMA_MESSAGGIO 2048
#define MQTT_TOPIC_A "serverai/result"
#define MQTT_TOPIC_B "communication/messages"

/////////////////////////////
//    VARIABILI GLOBALI    //
/////////////////////////////

PicoMQTT::Client mqtt(mqttHost, mqttPort);
static bool eth_connected = false;
QueueHandle_t codaIN = xQueueCreate(10, sizeof(char[DIMENSIONE_MASSIMA_MESSAGGIO]));
QueueHandle_t codaOUT = xQueueCreate(10, sizeof(char[DIMENSIONE_MASSIMA_MESSAGGIO]));

TaskHandle_t xSerialReceiveHandle;
TaskHandle_t xSerialSendHandle;
TaskHandle_t xMqttHandle;
TaskHandle_t xEthMonitorHandle;

//////////////
//  SETUP  //
/////////////

void setup() {

  delay(100);
  Serial.setTimeout(100); 
  Serial.begin(38400);
  
  setupSeriale();
  setupEthernet();
  setupMQTT();
  setupTasks();
  
  Serial.println("[SYSTEM] Setup completato\n");
}

//////////////////////
//  FUNZIONI SETUP  //
//////////////////////

void setupSeriale() {

  Serial.println("\n[SERIAL SETUP] Inizializzazione porte seriali...");

  Serial1.setTimeout(100); 
  Serial1.begin(74880, SERIAL_8N1, RXp1, -1);

  Serial2.setTimeout(100); 
  Serial2.begin(74880, SERIAL_8N1, -1, TXp2);

  Serial.println("[SERIAL SETUP] Porte seriali inizializzate");

  Serial.println("[SERIAL SETUP] Setup seriale completato\n");
  
}

void setupEthernet() {

  Serial.println("[ETHERNET SETUP] Setup interfaccia di rete in corso...");
  ETH.begin();
  ETH.config(IPAddress(192, 168, 1, 50), IPAddress(), IPAddress(255, 255, 255, 0));
  
  while (!ETH.linkUp()) {
    Serial.println("[ETHERNET SETUP] Attesa connessione...");
    delay(1000);
  }
  
  Serial.printf("[ETHERNET SETUP] Connesso: %s\n", ETH.localIP().toString().c_str());

  Serial.println("[ETHERNET SETUP] Setup ethernet completato\n");
}

void setupMQTT() {

  Serial.println("[MQTT SETUP] Setup connessione MQTT...");

  Serial.println("[MQTT SETUP] Ping al server in corso...");

  while(true){
    if (Ping.ping(IPAddress(192,168,1,101))) {
      Serial.println("[MQTT SETUP] Server raggiungibile");

      mqtt.subscribe(MQTT_TOPIC_A, [](const char* topic, const char* payload) {
        
        Serial.printf("[MQTT] Ricevuto: %s\n", payload);
        
        char messaggio[DIMENSIONE_MASSIMA_MESSAGGIO];
        strcpy(messaggio, payload);
        scriviMessaggioCoda(messaggio, codaOUT);

      });

      Serial.println("[MQTT SETUP] Subscribe al server fatto");

      break;

    } else {
      Serial.println("[MQTT SETUP] ERR: Server non raggiungibile");
    }
  }

  Serial.println("[MQTT SETUP] Setup MQTT completato\n");

}

void setupTasks() {

  Serial.println("[RTOS SETUP] Creazione tasks...");

  xTaskCreatePinnedToCore(
    serialReceiveTask, "SerialRx", 40960, NULL, 2, &xSerialReceiveHandle, 0)
  ;

  xTaskCreatePinnedToCore(
    serialSendTask, "SerialTx", 40960, NULL, 2, &xSerialSendHandle, 1)
  ;
  
  xTaskCreatePinnedToCore(
    mqttTask, "MQTT", 20480, NULL, 3, &xMqttHandle, 1)
  ;
  
  xTaskCreatePinnedToCore(
    ethMonitorTask, "ETH", 8192, NULL, 1, &xEthMonitorHandle, 0)
  ;
    
  Serial.println("[RTOS SETUP] Task creati");
  Serial.println("[RTOS SETUP] Setup tasks completato\n");
}

////////////////
//  FUNZIONI  //
////////////////

bool riceviDatiSeriale(char* destinationBuffer, size_t max_len) {

  int dimensioneMessaggio = 0;

  if(Serial1.available()){
    
    char bufferMessaggi[max_len];

    while (Serial1.available()) {

      char carattereCorrente = Serial1.read();

      bufferMessaggi[dimensioneMessaggio++] = carattereCorrente;

      if (dimensioneMessaggio >= max_len - 1) {
        Serial.println("[SERIAL] ERR: Messaggio troppo lungo");
        memset(bufferMessaggi, 0, max_len);

        return false;
      }
    }

    bufferMessaggi[dimensioneMessaggio -1] = '\0';
    strcpy(destinationBuffer, bufferMessaggi);

    return true;

  }else return false;
}

bool scriviMessaggioCoda(const char* messaggio, QueueHandle_t coda) {

  if (xQueueSend(coda, messaggio, pdMS_TO_TICKS(50)) != pdTRUE) {

    Serial.println("[QUEUE] Coda piena");
    return false;
  } else return true;
}

String leggiMessaggioCoda(QueueHandle_t coda) {

  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];

  if (xQueueReceive(coda, bufferMessaggi, pdMS_TO_TICKS(50)) == pdTRUE) {
    
    return String(bufferMessaggi);
    
  } else return "";
}

////////////////
//   TASKS    //
////////////////

void serialReceiveTask(void* parameter) {

  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];
  
  for(;;) {
    if (riceviDatiSeriale(bufferMessaggi, sizeof(bufferMessaggi))) {
      
      Serial.printf("[SERIAL] Ricevuto: %s\n", bufferMessaggi);
      scriviMessaggioCoda(bufferMessaggi, codaIN);
      
    }
    vTaskDelay(5 / portTICK_PERIOD_MS);
  }
}

void serialSendTask(void* parameter) {

  String messaggio;

  for(;;){

    messaggio = leggiMessaggioCoda(codaOUT);

    if(messaggio.length()>=1){
      Serial2.println(messaggio);
      Serial.printf("[SERIAL] Messaggio inviato in seriale: %s\n", messaggio.c_str());
    }

  }
}

void mqttTask(void* parameter) {
  
  for(;;) {

    mqtt.loop();

    String messaggio = leggiMessaggioCoda(codaIN);

    if(messaggio.length() > 1) {
        mqtt.publish(MQTT_TOPIC_B, messaggio);
    }

    if (!mqtt.connected()) {
      Serial.println("[MQTT] Riconnessione...");
      mqtt.connect(mqttHost, mqttPort);
      vTaskDelay(200 / portTICK_PERIOD_MS);
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }   


}

void ethMonitorTask(void* parameter) {
  for(;;) {
    if (!ETH.linkUp() || ETH.localIP() == IPAddress(0, 0, 0, 0)) {
      Serial.println("[ETH] Riconnessione...");
      setupEthernet();
    }
    vTaskDelay(3000 / portTICK_PERIOD_MS);
  }
}

void loop() {

  static uint32_t last = 0;

  if (millis() - last > 30000) {
    
    Serial.printf("[SYS] Heap: %d | Min: %d\n", ESP.getFreeHeap(), esp_get_minimum_free_heap_size());

    last = millis();
  }
  delay(100);

}
