#define RXp0 3
#define TXp0 1

void setup() {

  Serial.begin(115200);
  Serial0.begin(9600, SERIAL_8N1, RXp0, TXp0);
  
}
void loop() {
  for(int i; i=0; i<100){
    Serial.println("Messaggio dalla scheda in n:"+i);
    delay(3000);
  }
   
}