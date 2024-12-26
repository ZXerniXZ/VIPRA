#include <SPI.h>
#include <LoRa.h>

//pin lora
#define LORA_CS 18
#define LORA_RST 23
#define LORA_IRQ 26

//pin seriale
//#define RXp1 21
#define TXp1 22


String const machine_code = "12345678ABC";
String messaggio;
String conferma;
int count_messaggi = 0;
int contatore=0;
bool responso;



void setup() {

  Serial.setTimeout(100); 
  Serial1.setTimeout(100);
  LoRa.setTimeout(100);
  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, -1, TXp1);
  LoRa.begin(433E6);

  Serial.println("\nInizializzazione LoRa...");
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);

  delay(500); //delay per setup

  if (!LoRa.begin(433E6)) { 
    Serial.println("Errore: Modulo LoRa non trovato!");
  }else
  Serial.println("LoRa inizializzato con successo!");

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
  
  Serial.print("SONO NELLA FUNZIONE\n");
  while (LoRa.available()) {
    char byteReceived = (char)LoRa.read(); 
    messaggio+=byteReceived;
  }
  return messaggio;
}


void loop() {

  do{

    
    if(LoRa.parsePacket()){
      Serial.print("SONO NEL IF\n");
      messaggio = loraReceiveStringLoRa();
    }

    //messaggio = loraReceiveStringSerial();  // PER UTILIZZARE LA SCHEDA SENZA LA OUT

    delay(100);

  }while(messaggio.length()<1);

  if(String(messaggio.substring(0, 11))==machine_code){
    Serial.println("Machine code uguale, deviazione pacchetto...");
  }else{
    messaggio = messaggio.substring(11,messaggio.length());

    if(messaggio.length()>1){
    Serial.print("Messaggio ricevuto: ");
    Serial.println(messaggio);
    Serial1.println(messaggio);
    }else{
      Serial.println("Messaggio vuoto");
    }
  }
    
  delay(100);

  ///   RICEVERE UNA STRINGA LORA DOVE I PRIMI CARATTERI SONO IL CODICE MACCHINA, E IL RESTO IL MESSAGGIO  //
  ///   MANDARE MESSAGGIO IN SERIALE A POE //
  ///   RICEVERE IN SERIALE DALLA NVIDIA IL CODICE MACCHINA  
  ///   RIMUOVERE SCAMBIO ACK MA MANTENERE IL CONTROLLO (DEVIAZIONE PACCHETTO)  //

}