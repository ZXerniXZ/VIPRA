#include <SPI.h>
#include "LoRaWan_APP.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

// Pin seriale
#define TXp1 22

// Frequenza LoRa
#define RF_FREQUENCY 915000000

////////////////////
//    COSTANTI    //
////////////////////

#define DIMENSIONE_MASSIMA_MESSAGGIO 2048
const char machine_code[] = "12345678ABC";

/////////////////////////////
//    VARIABILI GLOBALI    //
/////////////////////////////

QueueHandle_t coda = xQueueCreate(10, sizeof(char[DIMENSIONE_MASSIMA_MESSAGGIO]));

TaskHandle_t ComunicazioneLoRa, ComunicazioneSeriale;

RadioEvents_t RadioEvents;

char loraMessage[DIMENSIONE_MASSIMA_MESSAGGIO];


//////////////
//  SETUP  //
/////////////

void setup() {

  delay(100);
  Serial.setTimeout(10); 
  Serial.begin(38400);
  
  setupSeriale();
  setupLora();
  setupTasks();
  Serial.println("[SYSTEM] Setup completato\n");

}


//////////////////////
//  FUNZIONI SETUP  //
//////////////////////

void setupSeriale() {

  Serial.println("\n[SERIAL SETUP] Inizializzazione porte seriali...");

  Serial1.setTimeout(10);
  Serial1.begin(74880, SERIAL_8N1, -1, TXp1);

  Serial.println("[SERIAL SETUP] Porte seriali inizializzate");

  Serial.println("[SERIAL SETUP] Setup seriale completato\n");

}

void setupLora(){

  Serial.println("[LORA SETUP] Inizializzazione modulo LoRa...");

  Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);

  Serial.println("[LORA SETUP] Modulo LoRa inizializzato");

  delay(100);

  Serial.println("[LORA SETUP] Settaggio in corso...");

  Radio.SetTxConfig(MODEM_LORA, 5, 0, 0, 7, 1, 8, false, true, 0, 0, false, 3000);

  Serial.println("[LORA SETUP] Settaggio completato");

  Serial.println("[LORA SETUP] Settaggio frequenza in corso...");

  Radio.SetChannel(RF_FREQUENCY);

  Serial.println("[LORA SETUP] Frequenza settata");

  Serial.println("[LORA SETUP] Settaggio eventi...");

  RadioEvents.RxDone = onRxDone; 
  Radio.Init(&RadioEvents);

  Serial.println("[LORA SETUP] Eventi settati");

  Serial.println("[LORA SETUP] Modulo LoRa inizializzato");
  Serial.println("[LORA SETUP] Setup LoRa completato\n");
  

}

void setupTasks(){

  Serial.println("[RTOS SETUP] Creazione tasks...");

  xTaskCreatePinnedToCore(
    comunicazioneSeriale, "ComunicazioneSeriale", 12288, NULL, 1, &ComunicazioneSeriale, 0)
  ;

  xTaskCreatePinnedToCore(
    comunicazioneLoRa, "ComunicazioneLoRa", 12288, NULL, 2, &ComunicazioneLoRa, 1)
  ;

  Serial.println("[RTOS SETUP] Task creati");
  Serial.println("[RTOS SETUP] Setup tasks completato\n");

}

////////////////
//  FUNZIONI  //
////////////////

void onRxDone(uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr) {
  
  memcpy(loraMessage, payload, size); 
  
}

bool riceviDatiLora(char* buffer, size_t max_len) {

  char messaggio[max_len];

  bool inRicezione = false;
  
  if(!inRicezione) {
    Radio.Rx(0);      
    inRicezione = true;
  }
  
  Radio.IrqProcess();
  
  if(String(loraMessage).length() > 1) {

    strcpy(messaggio, loraMessage);

    messaggio[sizeof(loraMessage)] = '\0';

    strcpy(buffer, messaggio);
    
    inRicezione = false;
    return true;

  }
  return false;
}

bool scriviMessaggioCoda(char* messaggio) {

  if (xQueueSend(coda, messaggio, pdMS_TO_TICKS(50)) != pdTRUE) {

    Serial.println("[QUEUE] Coda piena");
    return false;
  } else return true;
}

String leggiMessaggioCoda() {

  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];

  if (xQueueReceive(coda, bufferMessaggi, pdMS_TO_TICKS(50)) == pdTRUE) {
    
    return String(bufferMessaggi);
    
  } else return "";
}


////////////////
//   TASKS    //
////////////////


void comunicazioneLoRa(void* parameter) {
  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];
  
  for(;;) {

    if (riceviDatiLora(bufferMessaggi, DIMENSIONE_MASSIMA_MESSAGGIO)) {

      Serial.printf("[LORA] Ricevuto: %s\n", bufferMessaggi);

      scriviMessaggioCoda(bufferMessaggi);

    }
    vTaskDelay(5 / portTICK_PERIOD_MS);

  }
}

void comunicazioneSeriale(void* parameter) {
  
  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];

  for(;;){

    String messaggio = leggiMessaggioCoda();

    if(messaggio.length() > 1) {
      strcpy(bufferMessaggi, messaggio.c_str());
      bufferMessaggi[messaggio.length()] = '\0';

      Serial1.println(bufferMessaggi);
    }
    vTaskDelay(5 / portTICK_PERIOD_MS);

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