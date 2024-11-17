#define RXp0 23
#define TXp0 22

void setup() {

  Serial.begin(9600);
  Serial1.begin(19200, SERIAL_8N1, RXp0, TXp0);
  
}
void loop() {

  for(int i=0;i<100;i++){
  
  String messaggio="SCHEDA IN:";
  Serial.println(messaggio+i);
  Serial1.println(messaggio+i);
  delay(3000);
  }
}