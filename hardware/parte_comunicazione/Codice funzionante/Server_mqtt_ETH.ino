
#define ETH_CLK_MODE ETH_CLOCK_GPIO17_OUT
#define ETH_PHY_POWER 12

#include <PicoMQTT.h>
#include <ETH.h>

static bool eth_connected = false;

class MQTT: public PicoMQTT::Server {} mqtt;


void setup() {

  delay(500);

  Serial.begin(115200);
  Serial.print("Setup...\n");
  
  WiFi.onEvent(WiFiEvent);
  
  Serial.print("Starting ETH interface...\n");
  ETH.begin();

  mqtt.begin();
  Serial.print("MQTT server started...\n");

}

void WiFiEvent(WiFiEvent_t event)
{
  switch (event) {

    case ARDUINO_EVENT_ETH_CONNECTED:

      Serial.println("ETH Connected");

      break;

    case ARDUINO_EVENT_ETH_GOT_IP:

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
      eth_connected = true;

      break;

    case ARDUINO_EVENT_ETH_DISCONNECTED:

      Serial.println("ETH Disconnected");
      eth_connected = false;

      break;
  }
}

void loop() {
  
  if (random(1000) == 0){
    mqtt.publish("picomqtt/welcome", "Hello from PicoMQTT!");

    delay(1000);
  
  }
}
