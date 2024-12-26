#include <SPI.h>
#include <LoRa.h>
#include <regex>

//pin lora
#define LORA_CS 18
#define LORA_RST 23
#define LORA_IRQ 26

//pin seriale
#define RXp1 21
//#define TXp1 22


String messaggio;
String const machine_code = "12345677ABC";



void setup() {

  Serial.setTimeout(100);  
  Serial1.setTimeout(100);
  LoRa.setTimeout(100);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);
  LoRa.begin(433E6);

  delay(500); //delay setup

  Serial.println("\nInizializzazione LoRa...");
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  if (!LoRa.begin(433E6)) {
    Serial.println("Errore: Modulo LoRa non trovato!");
  }else
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

String loraReceiveStringSerial1(){
  String messaggio = Serial1.readString();
  messaggio.trim();
  if(messaggio.length()>=1){
    return messaggio;
  }else{
    return "";
  }
}



void loop() {

  do{
    messaggio=loraReceiveStringSerial1();
    delay(100);
  }while(messaggio.length()<1);

  Serial.println("Messaggio ricevuto: " + messaggio);
  loraSendString(machine_code+messaggio);
  Serial.println("Messaggio inviato: " + machine_code + messaggio);
  
  delay(100);

}


///   INVIARE STRINGA MESSAGGIO CON LE PRIME 8 POSIZIONI CONTENENTI IL CODICE MACCHINA E IL RESTO IL MESSAGGIO  //
///   RIMUOVERE CONTROLLO ACK   //
///   RICEVI DATI DA POE E INVIA IN LORA AD ALTRE MACCHINE   //
