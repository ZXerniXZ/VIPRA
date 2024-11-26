//#define RXp1 23
#define TXp1 22

void setup() {

  Serial.setTimeout(0);  
  Serial1.setTimeout(0);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, -1, TXp1);
  
}

  int contatore=0;

void loop() {


  String messaggio="Messaggio n:";

  messaggio = Serial.readString();

  messaggio.trim();

  if(messaggio.length()>=1){
  Serial.println(messaggio);
  Serial1.println(messaggio);
  }

  contatore++;
  delay(3000);

}