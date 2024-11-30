#include <SPI.h>
#include <LoRa.h>

#define LORA_CS 18
#define LORA_RST 14
#define LORA_IRQ 26

void setup() {
  Serial.begin(9600);

  Serial.println("Inizializzazione LoRa...");
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  if (!LoRa.begin(433E6)) { 
    Serial.println("Errore: Modulo LoRa non trovato!");
    while (true);
  }
  Serial.println("LoRa inizializzato con successo!");
}

int count_messaggi = 0;

void loop() {

  String messaggio = "Invio pacchetto n";

  messaggio = Serial.readString();

  messaggio.trim();

  if(messaggio.length()>=1){
  Serial.println(messaggio);
  Serial1.println(messaggio);
  }

  LoRa.beginPacket();
  //messaggio = "Pacchetto n";
  LoRa.print(messaggio);
  LoRa.endPacket();

  count_messaggi++;

  //delay(3000);
}
