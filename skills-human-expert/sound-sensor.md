---
name: Microphone Sound Sensor
description: A sound sensor based on condenser microphone (KY-038).
---

## Pinout

| Name | Description |
|---|---|
| A0  | Analog output |
| GND | Ground |
| VCC | Voltage supply |
| D0  | Digital output |


## Operation

- The **Digital Output** (`D0`) produces a HIGH signal (logic `1`) if sound is detected. Detection sensitivity can be tuned using the on-board variable resistor. Use ISR to better detect the triggering signal.

- The **Analog Output** (`A0`) produces an analog voltage proportional to the sound intensity.