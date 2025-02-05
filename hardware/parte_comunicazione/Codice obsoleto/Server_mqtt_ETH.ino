#include <PicoMQTT.h>
#include <ETH.h>

PicoMQTT::Server mqtt;
static bool eth_connected = false;

void setup() {

  delay(500);

  Serial.begin(115200);
  Serial.print("Setup...\n");
  
  Serial.print("Configuring Ethernet...\n");
  ETH.begin();
  NETsetup();
  Serial.print("Network configuration done\n");
  Serial.print("Starting MQTT server...\n");
  //PicoMQTT::Server mqtt(1883);        porta custom
  mqtt.begin();
  Serial.print("MQTT server started\n");
}

void NETsetup() {

  while (!ETH.linkUp()) {
    Serial.println("Waiting for Ethernet link...");
    delay(3000);
  }

  Serial.println("ETH Connected");
  eth_connected = true;

  while (ETH.localIP() == IPAddress(0, 0, 0, 0)) {
    Serial.println("Waiting for IP address...");
    delay(3000);
  }

  Serial.print("Got an IP Address for ETH MAC: ");
  Serial.print(ETH.macAddress());
  Serial.print(", IPv4: ");
  Serial.print(ETH.localIP());
  if (ETH.fullDuplex()) {
    Serial.print(", FULL_DUPLEX");
  }
  Serial.print(", ");
  Serial.print(ETH.linkSpeed());
  Serial.println("Mbps");
}

int i=0;
void loop() {

  mqtt.loop();
  if (!ETH.linkUp() || ETH.localIP() == IPAddress(0, 0, 0, 0)) {
    Serial.println("ETH Disconnected or IP lost\nReconnecting...");
    eth_connected = false;
    NETsetup();
  }

  if (i==1000){
    mqtt.publish("picomqtt/welcome", "Hello from PicoMQTT!");
    delay(1000);
    i=0;
  } i++;
}

/// AGGIUNGERE SUBSCRIBE E PUBLISH E INTERFACCIARE CON LE ALTRE SCHEDE
/// GUARDARE LOOP IN SEQUENZA (O IN MULTITHREAD)
