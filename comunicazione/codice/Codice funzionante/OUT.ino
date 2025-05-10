#include <SPI.h>
#include "LoRaWan_APP.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

// Pin seriale
#define RXp1 21

// Frequenza LoRa
#define RF_FREQUENCY 915000000

////////////////////
//    COSTANTI    //
////////////////////

#define DIMENSIONE_MASSIMA_MESSAGGIO 2048

const char machine_code[] = "12345677ABC"; 

/////////////////////////////
//    VARIABILI GLOBALI    //
/////////////////////////////

QueueHandle_t coda = xQueueCreate(10, sizeof(char[DIMENSIONE_MASSIMA_MESSAGGIO]));

TaskHandle_t ComunicazioneSeriale, ComunicazioneLoRa;


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


void setupSeriale(){

  Serial.println("\n[SERIAL SETUP] Inizializzazione porte seriali...");

  Serial1.setTimeout(10);
  Serial1.begin(74880, SERIAL_8N1, RXp1, -1);

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

  Serial.println("[LORA SETUP] Modulo LoRa inizializzato");
  Serial.println("[LORA SETUP] Setup LoRa completato\n");
  

}

void setupTasks(){

  Serial.println("[RTOS SETUP] Creazione tasks...");

  xTaskCreatePinnedToCore(
    comunicazioneSeriale, "ComunicazioneSeriale", 12288, NULL, 2, &ComunicazioneSeriale, 0)
  ;

  xTaskCreatePinnedToCore(
    comunicazioneLoRa, "ComunicazioneLoRa", 12288, NULL, 1, &ComunicazioneLoRa, 1)
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

void inviaMessaggioLora(char* messaggio){

  Radio.Send((uint8_t *)messaggio, sizeof(messaggio));

  Serial.printf("[LORA] Messaggio inviato tramite LoRa: %s\n", messaggio);

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


void comunicazioneSeriale(void * parameter) {

  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];
  
  for(;;) {

    if (riceviDatiSeriale(bufferMessaggi, sizeof(bufferMessaggi))) {

      Serial.printf("[SERIAL] Ricevuto: %s\n", bufferMessaggi);

      scriviMessaggioCoda(bufferMessaggi);
      
    }
    vTaskDelay(5 / portTICK_PERIOD_MS);
  }

}


void comunicazioneLoRa(void * parameter) {

  char bufferMessaggi[DIMENSIONE_MASSIMA_MESSAGGIO];

  for(;;) {
    String messaggio = leggiMessaggioCoda();
    
    if(messaggio.length() > 1) {

      strcpy(bufferMessaggi, messaggio.c_str());
      bufferMessaggi[messaggio.length()] = '\0';

      inviaMessaggioLora(bufferMessaggi);

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
