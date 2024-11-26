#define RXp1 2
//#define TXp1 5  

//#define RXp2 36
#define TXp2 4

void setup() {

  Serial.setTimeout(0);  
  Serial1.setTimeout(0);
  Serial2.setTimeout(0);

  Serial.begin(38400);
  Serial1.begin(115200, SERIAL_8N1, RXp1, -1);
  Serial2.begin(115200, SERIAL_8N1, -1, TXp2); 
}

void loop() {

  String messaggio = Serial1.readString();
  
  Serial2.print(messaggio);
  Serial.print(messaggio);
    
}