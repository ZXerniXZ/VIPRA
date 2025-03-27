#include <SPI.h>
#include <LoRa.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <List.hpp>


// Pin LoRa
#define LORA_CS 18
#define LORA_RST 23
#define LORA_IRQ 26

// Pin seriale
#define TXp1 22


////////////////////

//    COSTANTI    //

////////////////////

#define MAX_MESSAGE_LENGTH 2500 // Lunghezza massima del messaggio

String const machine_code = "12345678ABC"; // Codice macchina


/////////////////////////////

//    VARIABILI GLOBALI    //

/////////////////////////////

QueueHandle_t xQueue = xQueueCreate(10, sizeof(char[MAX_MESSAGE_LENGTH])); // Coda per i messaggi ricevuti via LoRa

TaskHandle_t ComunicazioneLoRa, ComunicazioneSeriale;


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
  Serial1.begin(115200, SERIAL_8N1, -1, TXp1);

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
    1,  // Priorità
    &ComunicazioneSeriale,  // Task handle
    0)  // Core
  ;

  xTaskCreatePinnedToCore(
    comunicazioneLoRa, // Nome funzione
    "ComunicazioneLoRa", // Nome task
    10240, // Dimensione stack
    NULL,  // Parametri
    2,  // Priorità più alta per la ricezione
    &ComunicazioneLoRa,  // Task handle
    1)  // Core
  ;  


  Serial.println("Tasks created succesfully");

}


////////////////

//  FUNZIONI  //

////////////////



String receiveStringLoRa() {

  if (LoRa.parsePacket()) {

    char nuovoMessaggio[MAX_MESSAGE_LENGTH] = {0};
    int index = 0;

    while (LoRa.available() && index < MAX_MESSAGE_LENGTH - 1) {
      nuovoMessaggio[index++] = char(LoRa.read());
    }

    nuovoMessaggio[index] = '\0'; // Termina la stringa

    Serial.println(String(nuovoMessaggio));

    return String(nuovoMessaggio);
  }else{

    return "";

  }

}




////////////////

//   TASKS    //

////////////////

void comunicazioneLoRa(void * parameter) {
  for(;;) {

    String nuovoMessaggio = receiveStringLoRa();

    if (nuovoMessaggio.length() >= 1){

      if (xQueueSend(xQueue, &nuovoMessaggio, portMAX_DELAY) != pdTRUE) {
        Serial.println("[ComunicazioneLoRa] Error: full queue!");
      }else{
        Serial.println("[ComunicazioneLoRa] Message correctly queued");
      }
    }
  
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void comunicazioneSeriale(void * parameter) {
  for(;;) {

    char messaggioDaInviare[MAX_MESSAGE_LENGTH] = {0}; // Buffer per il messaggio

    char codiceMacchina[machine_code.length()]={0};

    for(int i=0; i<machine_code.length(); i++){
      codiceMacchina[i]=messaggioDaInviare[i];
    }

    if (xQueueReceive(xQueue, &messaggioDaInviare, portMAX_DELAY) == pdTRUE) {

      if (String(codiceMacchina).equals(machine_code)) {
        Serial.println("[ComunicazioneSeriale] Machine code uguale, deviazione pacchetto...");
      } else {
        // Estrai il messaggio (rimuovi il codice macchina)
        char messaggioSenzaCodice[MAX_MESSAGE_LENGTH] = {0};
        
        for(int i=0; i<MAX_MESSAGE_LENGTH; i++){
          messaggioDaInviare[i+machine_code.length()]=messaggioDaInviare[i];
        }

        if (String(messaggioSenzaCodice).length() >= 1) {

          Serial.print("[ComunicazioneSeriale] Messaggio da inviare: ");
          Serial.println(messaggioSenzaCodice);

          Serial1.println(messaggioSenzaCodice);
        } else {
          Serial.println("[ComunicazioneSeriale] Messaggio vuoto");
        }
      }
    }

    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

void loop() {}