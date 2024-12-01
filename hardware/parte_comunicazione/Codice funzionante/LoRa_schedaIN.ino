#include <SPI.h>
#include <LoRa.h>

#define LORA_CS 18
#define LORA_RST 14
#define LORA_IRQ 26

void setup() {

  Serial.setTimeout(100); 
  LoRa.setTimeout(100);
  Serial.begin(9600);

  Serial.println("Inizializzazione LoRa...");
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  if (!LoRa.begin(433E6)) { 
    Serial.println("Errore: Modulo LoRa non trovato!");
    while (true);
  }
  Serial.println("LoRa inizializzato con successo!");

}

String const machine_code = "12345678ABC";
String messaggio;
String conferma;
int count_messaggi = 0;
bool responso;

void loop() {

  responso =false;
  conferma = "";

  do{

    messaggio = "Invio pacchetto n";

    messaggio = Serial.readString();
    messaggio.trim();

  }while(messaggio.length()<1);

  LoRa.beginPacket();
  LoRa.print(machine_code);
  LoRa.endPacket();
  Serial.println("Machine code inviato");

  do{

    if(LoRa.parsePacket()){
      conferma = LoRa.readString();
      conferma.trim();
    }

    if (conferma == "true"){

      responso = true;
    
    }else{
      responso = false;
    }
  
    
  }while (conferma.length()<1);
  

  if(responso){

    Serial.println("Responso positivo ottenuto");
    LoRa.beginPacket();
    //messaggio = "Pacchetto n";
    LoRa.print(messaggio);
    LoRa.endPacket();
    Serial.print("Messaggio inviato: ");
    Serial.println(messaggio);

    count_messaggi++;

  }else{
    Serial.println("Responso negativo ottenuto");
  }

}
