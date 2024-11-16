#define RXp0 3
#define TXp0 1

#define RXp1 36
#define TXp1 4

void setup() {

  Serial.begin(115200);
  Serial0.begin(9600, SERIAL_8N1, RXp0, TXp0);
  Serial1.begin(9600, SERIAL_8N1, RXp1, TXp1);
  
}
void loop() {
    Serial1.println(Serial0.readString());
}