---
name: Photoresistor Light Sensor
description: A light intensity sensor using a photoresistor (KY-018).
---

## Pinout

| Name | Description |
|---|---|
| S   | Analog output |
| VCC | Voltage supply |
| GND | Ground |

## Operation

- The **Analog Output** reflects the ambient light intensity: a lower output voltage (i.e., lower resistance) indicates higher light levels.

- Inside KY-018, the photoresistor and a fixed 10 kΩ resistor form a voltage divider between VCC and ground: this circuit converts the photoresistor’s changing resistance into a varying voltage on the signal pin (S).
