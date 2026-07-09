---
name: Ultrasonic Distance Sensor
description: An ultrasonic sensor for distance measurement (HC-SR04).
---

## Pinout

| Name | Description |
|---|---|
| VCC  | Voltage supply |
| TRIG | Trigger pulse input |
| ECHO | Echo pulse output |
| GND  | Ground |

## Operation

- Drive the **TRIG** pin with a 10 microseconds HIGH pulse to initiate a measurement.

- Always read **ECHO** with a timeout. The measured ECHO signal duration (HIGH pulse width) corresponds to the round-trip time of the ultrasound wave.

- ECHO pin outputs 5V: use level shifting or a voltage divider if interfacing with a 3.3V MCU.

- Recommended operating range: 10 cm to 250 cm (absolute range: 2 cm to 400 cm); Minimum measurement interval is ~60 milliseconds.