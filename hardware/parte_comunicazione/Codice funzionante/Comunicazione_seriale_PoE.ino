#define RXp0 3
#define TXp0 1

#define RXp1 36
#define TXp1 4

void setup() {
  Serial.begin(9600);
  Serial1.begin(19200, SERIAL_8N1, RXp0, TXp0);
  Serial2.begin(19200, SERIAL_8N1, RXp1, TXp1); 
}

void loop() {

  if (Serial1.available() > 0){

    String messaggio=Serial1.readString();

    Serial2.print(messaggio);
    Serial.print(messaggio);

  }
  
}
