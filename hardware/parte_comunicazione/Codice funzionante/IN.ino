#include <SPI.h>
#include <LoRa.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

// Pin LoRa
#define LORA_CS 18
#define LORA_RST 23
#define LORA_IRQ 26

// Pin seriale
#define TXp1 22

#define MAX_MESSAGE_LENGTH 2500 // Lunghezza massima del messaggio

String const machine_code = "12345678ABC"; // Codice macchina
QueueHandle_t xQueue; // Coda per i messaggi ricevuti via LoRa

TaskHandle_t RicezioneLoRa, InvioSeriale;



void setup() {
  Serial.setTimeout(100); 
  Serial1.setTimeout(100);
  LoRa.setTimeout(100);
  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, -1, TXp1);

  Serial.println("\nInizializzazione LoRa...");
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  delay(100); // Delay per setup

  if (!LoRa.begin(433E6)) { 
    Serial.println("Errore: Modulo LoRa non trovato!");
    //while (1);
  } else {
    Serial.println("LoRa inizializzato con successo!");
  }

  // Crea una coda per 10 messaggi di tipo char[]
  xQueue = xQueueCreate(10, sizeof(char[MAX_MESSAGE_LENGTH]));

  // Creazione dei task
  xTaskCreatePinnedToCore(
    ricezioneLoRa, // Nome funzione
    "RicezioneLoRa", // Nome task
    2048, // Dimensione stack
    NULL,  // Parametri
    2,  // Priorità più alta per la ricezione
    &RicezioneLoRa,  // Task handle
    0)  // Core
  ;  

  xTaskCreatePinnedToCore(
    invioSeriale, // Nome funzione
    "InvioSeriale", // Nome task
    2048, // Dimensione stack
    NULL,  // Parametri
    1,  // Priorità
    &InvioSeriale,  // Task handle
    1)  // Core
  ;   
}

void ricezioneLoRa(void * parameter) {
  for(;;) {
    // Ricezione messaggio via LoRa
    if (LoRa.parsePacket()) {
      char nuovoMessaggio[MAX_MESSAGE_LENGTH] = {0}; // Buffer per il messaggio
      int index = 0;

      while (LoRa.available() && index < MAX_MESSAGE_LENGTH - 1) {
        nuovoMessaggio[index++] = (char)LoRa.read();
      }
      nuovoMessaggio[index] = '\0'; // Termina la stringa

      // Invia il messaggio alla coda
      if (xQueueSend(xQueue, &nuovoMessaggio, portMAX_DELAY) != pdTRUE) {
        Serial.println("[RicezioneLoRa] Errore: coda piena!");
      }
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void invioSeriale(void * parameter) {
  for(;;) {
    char messaggioDaInviare[MAX_MESSAGE_LENGTH] = {0}; // Buffer per il messaggio

    // Ricevi il messaggio dalla coda
    if (xQueueReceive(xQueue, &messaggioDaInviare, portMAX_DELAY) == pdTRUE) {
      // Controlla il codice macchina
      if (strncmp(messaggioDaInviare, machine_code.c_str(), 11) == 0) {
        Serial.println("[InvioSeriale] Machine code uguale, deviazione pacchetto...");
      } else {
        // Estrai il messaggio (rimuovi il codice macchina)
        char messaggioSenzaCodice[MAX_MESSAGE_LENGTH] = {0};
        strncpy(messaggioSenzaCodice, messaggioDaInviare + 11, MAX_MESSAGE_LENGTH - 11);

        if (strlen(messaggioSenzaCodice) >= 1) {
          Serial.print("[InvioSeriale] Messaggio da inviare: ");
          Serial.println(messaggioSenzaCodice);

          // Invia il messaggio via seriale
          Serial1.println(messaggioSenzaCodice);
        } else {
          Serial.println("[InvioSeriale] Messaggio vuoto");
        }
      }
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void loop() {}