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
#define RXp1 21

String const machine_code = "12345677ABC"; // Codice macchina
QueueHandle_t xQueue; // Coda per i messaggi ricevuti da Serial1

TaskHandle_t ComunicazioneSeriale, ComunicazioneLoRa;

void setup() {
  Serial.setTimeout(100);  
  Serial1.setTimeout(100);
  LoRa.setTimeout(100);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);
  LoRa.begin(433E6);

  delay(100); // Delay setup

  Serial.println("\nInizializzazione LoRa...");
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  if (!LoRa.begin(433E6)) {
    Serial.println("Errore: Modulo LoRa non trovato!");
    //while (1);
  } else {
    Serial.println("LoRa inizializzato con successo!");
  }

  // Crea una coda per 10 messaggi di tipo String
  xQueue = xQueueCreate(10, sizeof(String));

  // Creazione dei task
  xTaskCreatePinnedToCore(
    comunicazioneSeriale, // Nome funzione
    "ComunicazioneSeriale", // Nome task
    2048, // Dimensione stack
    NULL,  // Parametri
    2,  // Priorità più alta per la ricezione seriale
    &ComunicazioneSeriale,  // Task handle
    0)  // Core
  ;  

  xTaskCreatePinnedToCore(
    comunicazioneLoRa, // Nome funzione
    "ComunicazioneLoRa", // Nome task
    2048, // Dimensione stack
    NULL,  // Parametri
    1,  // Priorità
    &ComunicazioneLoRa,  // Task handle
    1)  // Core
  ;   
}

void comunicazioneSeriale(void * parameter) {
  for(;;) {
    // Ricezione messaggio da Serial1
    String nuovoMessaggio = loraReceiveStringSerial1();
    if (nuovoMessaggio.length() >= 1) {
      Serial.println("[Seriale] Messaggio ricevuto: " + nuovoMessaggio);

      // Invia il messaggio alla coda
      if (xQueueSend(xQueue, &nuovoMessaggio, portMAX_DELAY) != pdTRUE) {
        Serial.println("[Seriale] Errore: coda piena!");
      }
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void comunicazioneLoRa(void * parameter) {
  for(;;) {
    String messaggioDaInviare;

    // Ricevi il messaggio dalla coda
    if (xQueueReceive(xQueue, &messaggioDaInviare, portMAX_DELAY) == pdTRUE) {
      Serial.println("[LoRa] Messaggio ricevuto dalla coda: " + messaggioDaInviare);

      // Invia il messaggio via LoRa
      loraSendString(machine_code + messaggioDaInviare);
      Serial.println("[LoRa] Messaggio inviato via LoRa: " + machine_code + messaggioDaInviare);
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void loraSendString(String messaggio) {
  LoRa.beginPacket();
  LoRa.print(messaggio);
  LoRa.endPacket();
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

void loop() {}