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

void loop() {

  if (LoRa.parsePacket()) {

    Serial.print("Ricevuto pacchetto: ");

    String messaggio = LoRa.readString();
    Serial.println(messaggio);
      
  }
}
