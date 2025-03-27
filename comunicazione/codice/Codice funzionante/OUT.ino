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



////////////////////

//    COSTANTI    //

////////////////////

#define MAX_MESSAGE_LENGTH 2500 // Lunghezza massima del messaggio

String const machine_code = "12345677ABC"; // Codice macchina


/////////////////////////////

//    VARIABILI GLOBALI    //

/////////////////////////////


QueueHandle_t xQueue = xQueueCreate(10, MAX_MESSAGE_LENGTH * sizeof(char)); // Coda per i messaggi ricevuti da Serial1

TaskHandle_t ComunicazioneSeriale, ComunicazioneLoRa;


//////////////

//  SETUP  //

/////////////


void setup() {
  
  serialSetup();

  loraSetup();

  tasksSetup();

  Serial.println("Setup done");

}


//////////////////////

//  FUNZIONI SETUP  //

//////////////////////


void serialSetup(){

  Serial.setTimeout(100);  
  Serial1.setTimeout(100);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);

  Serial.println("\nSerial setup done");
}

void loraSetup(){

  Serial.println("Setup lora...");
  
  LoRa.setTimeout(100);
  LoRa.begin(433E6);

  delay(100);

  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  if (!LoRa.begin(433E6)) {
    Serial.println("Error: LoRa module not find! Restarting ESP32..");
    ESP.restart();
  } else {
    Serial.println("LoRa initialized successfully!");
  }

  Serial.println("Lora setup done");

}

void tasksSetup(){

  Serial.println("Creating tasks...");

  xTaskCreatePinnedToCore(
    comunicazioneSeriale, // Nome funzione
    "ComunicazioneSeriale", // Nome task
    10240, // Dimensione stack
    NULL,  // Parametri
    1,  // Priorità più alta per la ricezione seriale
    &ComunicazioneSeriale,  // Task handle
    0)  // Core
  ;  

  xTaskCreatePinnedToCore(
    comunicazioneLoRa, // Nome funzione
    "ComunicazioneLoRa", // Nome task
    10240, // Dimensione stack
    NULL,  // Parametri
    2,  // Priorità
    &ComunicazioneLoRa,  // Task handle
    1)  // Core
  ;  

  Serial.println("Tasks created succesfully");

}


////////////////

//  FUNZIONI  //

////////////////



String receiveStringSerial1() {

  if(Serial1.available()){

    char buffer[MAX_MESSAGE_LENGTH]={0};

    int len = Serial1.readBytesUntil('\n', buffer, MAX_MESSAGE_LENGTH - 1);
    buffer[len-1] = '\0';

    return String(buffer);

  }else{
    return "";
  }

}

void loraSendString(String messaggio) {
  LoRa.beginPacket();
  LoRa.print(messaggio);
  LoRa.endPacket();
}


////////////////

//   TASKS    //

////////////////


void comunicazioneSeriale(void * parameter) {
  for(;;) {
    
    String nuovoMessaggio = receiveStringSerial1();

    if (nuovoMessaggio.length() >= 1) {
      // Invia il messaggio alla coda

      if (xQueueSend(xQueue, &nuovoMessaggio, portMAX_DELAY) != pdTRUE) {
        Serial.println("[Seriale] Errore: coda piena!");
      }else{
        Serial.printf("Messaggio inviato alla coda: ", nuovoMessaggio);
      }
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}


void comunicazioneLoRa(void * parameter) {
  
  char messaggioDaInviare[MAX_MESSAGE_LENGTH]={0};

  for(;;) {

    // Ricevi il messaggio dalla coda
    if (xQueueReceive(xQueue, &messaggioDaInviare, portMAX_DELAY) == pdTRUE) {

      Serial.printf("\n[LoRa] Messaggio ricevuto dalla coda: %s\n", messaggioDaInviare);

      // Invia il messaggio via LoRa
      String messaggio = machine_code + String(messaggioDaInviare);
      loraSendString(messaggio);
      Serial.println("[LoRa] Messaggio inviato via LoRa: " + messaggio);

    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}



void loop() {}