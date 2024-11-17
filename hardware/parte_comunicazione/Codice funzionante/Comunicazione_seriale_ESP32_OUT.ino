#define RXp0 23
#define TXp0 22

void setup() {

  Serial.begin(9600);
  Serial1.begin(19200, SERIAL_8N1, RXp0, TXp0);
  
}
void loop() {
  
  if (Serial1.available() > 0) { 
        
  String messaggio=Serial1.readString();

  Serial.print(messaggio);
  }

}