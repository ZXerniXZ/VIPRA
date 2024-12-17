#define RXp1 23
//#define TXp1 22

void setup() {

  Serial.setTimeout(0);  
  Serial1.setTimeout(0);
  
  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);
  
}
void loop() {
  
  String messaggio=Serial1.readString();

  Serial.print(messaggio);
  
  //aggiungere delay di sovraccarico

  ///   RICEVI DATI DA POE E INVIA IN LORA AD ALTRE MACCHINE
}