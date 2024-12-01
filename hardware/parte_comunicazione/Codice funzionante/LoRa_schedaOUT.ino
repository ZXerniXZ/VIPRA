#include <SPI.h>
#include <LoRa.h>
#include <regex>

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

void loraSendString(String messaggio){
  LoRa.beginPacket();
  LoRa.print(messaggio);
  LoRa.endPacket();
}

String loraReceiveStringSerial(){
  String messaggio = Serial.readString();
  messaggio.trim();
  if(messaggio.length()>=1){
    return messaggio;
  }else{
    return "";
  }
}

String loraReceiveStringLoRa(){
  String messaggio = LoRa.readString();
  messaggio.trim();
  if(messaggio.length()>=1){
    return messaggio;
  }else{
    return "";
  }
}


std::regex pattern("^[0-9]{8}[A-Z]{3}$");

String const machine_code = "12345677ABC";


void loop() {

  if (LoRa.parsePacket()) {
       
    Serial.print("Ricevuto pacchetto: ");

    String messaggio = loraReceiveStringLoRa();

    if(messaggio.length()>=1){

      if (std::regex_match(messaggio.c_str(), pattern)) {

        Serial.println("Machine code riconosciuto");
        if (messaggio==machine_code){
          Serial.println("Codice macchina uguale riconosciuto, deviazione pacchetto");
          loraSendString("false");
        }else{
          Serial.println("Codice macchina idoneo");
          loraSendString("true");
        }
      }
      else{
        Serial.println(messaggio);
      }

    }
  }      
}
