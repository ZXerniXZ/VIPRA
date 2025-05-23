## PIN ESP32

![alt text](https://github.com/ZXerniXZ/projectDayProject/blob/a8bfcfb1ef20cd3322cd1562ea8731920c4bb927/hardware/Pin%20esp32.jpg)

## ESP32-PoE-ISO

![alt text](https://github.com/ZXerniXZ/projectDayProject/blob/1ae4fbc1a59daee72ffb16ed00dddbe3c39e25ab/hardware/ESP32-POE-ISO%20pin.png)

## SCHEMA ELETTRICO

![alt text](https://github.com/ZXerniXZ/projectDayProject/blob/cb1a6be08897872936a25effafea403bceb56fd5/hardware/Schema%20elettrico.png)


## INFORMAZIONI UTILI

* Librerie utilizzate
  * Comunicazione LoRa : `<LoRa.h>`
  * Comunicazione SPI : `<SPI.h>`
  * Server MQTT : `<PicoMQTT.h>`
  * Interfaccia Ethernet scheda POE : `<ETH.h>`
  * Multithreading : `<freertos/FreeRTOS.h>`
  * Task : `<freertos/task.h>`
  * Coda, queue : `<freertos/queue.h>`
  * Liste : `<List.hpp>`
  
* Pin comunicazione seriale
  * Scheda IN (TXp1) : `22`
  * Scheda OUT (RXp1) : `21`
  * Scheda POE (RXp1 connesso con scheda IN) : `2`
  * Scheda POE (TXp2 connesso con scheda OUT) : `4`
* Baud rate seriale
  * Monitor seriale : `38400`
  * Seriale per comunicazione tra schede : `115200`
  
* Pin comunicazione LoRa
  * Scheda IN
    * LORA_CS : `18`
    * LORA_RST : `23`
    * LORA_IRQ : `26`
  * Scheda OUT
    * LORA_CS : `18`
    * LORA_RST : `23`
    * LORA_IRQ : `26`
* Frequenza LoRa : `433E6`
 
* Porta server MQTT : `9000`
* IP server MQTT : `192.168.1.50`
* Topic di subsribe della scheda POE : `"MESSAGGI PER SCHEDA OUT"`
* Topic di publish di messaggi della scheda POE : `"MESSAGGI DA SCHEDA IN"`
* Dimensione stack : `10240`
  

