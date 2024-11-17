#define RXp0 3
#define TXp0 1

void setup() {

  Serial.begin(19200);
  Serial0.begin(9600, SERIAL_8N1, RXp0, TXp0);
  
}
void loop() {
  
  Serial.print("SCHEDA OUT:"+Serial0.readString());
  delay(2000);     
}