#define RXp0 3
#define TXp0 1

void setup() {

  Serial0.begin(9600, SERIAL_8N1, RXp0, TXp0);
  
}
void loop() {

  Serial0.print("SCHEDA IN:\n");

  delay(3000);

   
}