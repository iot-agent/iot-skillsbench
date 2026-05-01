---
name: MQ2
description: A smoke and combustible gas sensor for detecting flammable gas.
---

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| DO  | Digital output |
| AO  | Analog output |

## Operation

- The **Analog Output** provides a continuous voltage reading that corresponds to the gas concentration (in unit ppm). Higher gas concentration results in higher voltage output.

- The **Digital Output** acts as a threshold detector: It goes `LOW` when gas concentration exceeds the threshold set by the potentiometer.

- Attributes and detection range:
    - Gas concentration: 300-10,000ppm (flammable gas).