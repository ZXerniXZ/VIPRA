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

String const machine_code = "12345678ABC";
String messaggio;
String conferma;
int count_messaggi = 0;
bool responso;

void loop() {

  responso =false;
  conferma = "";

  do{

    //messaggio = "Invio pacchetto n";
    messaggio = loraReceiveStringSerial();

    //aggiungere delay di sovraccarico

  }while(messaggio.length()<1);

  loraSendString(machine_code);
  Serial.println("Machine code inviato");

  do{

    if(LoRa.parsePacket()){
      conferma = loraReceiveStringLoRa();
    }

    if (conferma == "true"){

      responso = true;
    
    }else{
      responso = false;
    }
  
    
  }while (conferma.length()<1);
  

  if(responso){

    Serial.println("Responso positivo ottenuto");
    //messaggio = "Pacchetto n";
    loraSendString(messaggio);

    Serial.print("Messaggio inviato: ");
    Serial.println(messaggio);

    count_messaggi++;

  }else{
    Serial.println("Responso negativo ottenuto");
  }

  //aggiungere delay di sovraccarico


  ///   RICEVERE UNA STRINGA DOVE I PRIMI CARATTERI SONO IL CODICE MACCHINA, E IL RESTO IL MESSAGGIO
  ///   RICEVERE IN SERIALE DALLA NVIDIA IL CODICE MACCHINA
  //    RIMUOVERE SCAMBIO ACK MA MANTENERE IL CONTROLLO (DEVIAZIONE PACCHETTO)

}
