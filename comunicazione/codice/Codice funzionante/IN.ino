#include <SPI.h>
#include "LoRaWan_APP.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

// Pin seriale
#define TXp1 2

// Frequenza LoRa
#define RF_FREQUENCY                                433000000 // Hz
#define TX_OUTPUT_POWER                             14        // dBm
#define LORA_BANDWIDTH                              0         // [0: 125 kHz, 1: 250 kHz, 2: 500 kHz, 3: Reserved]
#define LORA_SPREADING_FACTOR                       7         // [SF7..SF12]
#define LORA_CODINGRATE                             1         // [1: 4/5, 2: 4/6, 3: 4/7, 4: 4/8]
#define LORA_PREAMBLE_LENGTH                        8         // Same for Tx and Rx
#define LORA_SYMBOL_TIMEOUT                         0         // Symbols
#define LORA_FIX_LENGTH_PAYLOAD_ON                  false
#define LORA_IQ_INVERSION_ON                        false
#define RX_TIMEOUT_VALUE                            1000

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

static RadioEvents_t RadioEvents;
void OnRxDone( uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr );

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
  RadioEvents.RxDone = OnRxDone;
  Radio.Init( &RadioEvents );

  Serial.println("[LORA SETUP] Modulo LoRa inizializzato");

  delay(100);

  Serial.println("[LORA SETUP] Settaggio frequenza in corso...");

  Radio.SetChannel(RF_FREQUENCY);

  Serial.println("[LORA SETUP] Frequenza settata");

  Serial.println("[LORA SETUP] Settaggio parametri in corso...");

  Radio.SetRxConfig( MODEM_LORA, LORA_BANDWIDTH, LORA_SPREADING_FACTOR,
                                   LORA_CODINGRATE, 0, LORA_PREAMBLE_LENGTH,
                                   LORA_SYMBOL_TIMEOUT, LORA_FIX_LENGTH_PAYLOAD_ON,
                                   0, true, 0, 0, LORA_IQ_INVERSION_ON, true );

  Serial.println("[LORA SETUP] Settaggio parametri completato");

  Radio.Rx(0);

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

void OnRxDone( uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr )
{
  int rxSize=size;

  memcpy(loraMessage, payload, size );
  loraMessage[rxSize]='\0';

  Radio.Rx(0);

}

bool riceviDatiLora(char* buffer, size_t max_len) {
  
  if(String(loraMessage).length() > 1) {

    strcpy(buffer, loraMessage);

    memset(loraMessage, 0, DIMENSIONE_MASSIMA_MESSAGGIO);
    
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

      Serial.printf("[LORA] Scritto alla coda: %s\n", bufferMessaggi);

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

      Serial1.println(String(bufferMessaggi));

      Serial.printf("[SERIAL] Messaggio inviato in seriale: %s\n", bufferMessaggi);
    }
    vTaskDelay(5 / portTICK_PERIOD_MS);

  }
  
}

void loop() {

  Radio.IrqProcess();

  static uint32_t last = 0;

  if (millis() - last > 30000) {

    Serial.printf("[SYS] Heap: %d | Min: %d\n", ESP.getFreeHeap(), esp_get_minimum_free_heap_size());

    last = millis();
  }
  delay(10);

}