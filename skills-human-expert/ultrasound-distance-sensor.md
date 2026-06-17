---
name: Ultrasound Distance Sensor
description: HC-SR04 ultrasound sensor for distance measurement
---

## Pinout

| Name | Description |
|---|---|
| GND | Ground |
| VCC | Voltage supply |
| SDA | I2C data line |
| SCL | I2C clock line |
| SQW | Optional square wave output |

## Operation

- Drive the **TRIG** pin with a 10 microseconds HIGH pulse to initiate a measurement.

- Always read **ECHO** with a timeout. The measured ECHO signal duration (HIGH pulse width) corresponds to the round-trip time of the ultrasound wave.

- ECHO pin outputs 5V: use level shifting or a voltage divider if interfacing with 3.3 MCUs.

- Recommended operating range: 10 cm to 250 cm (absolute range: 2 cm to 400 cm); Minimum measurement interval is ~60 milliseconds.