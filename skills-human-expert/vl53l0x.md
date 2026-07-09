---
name: VL53L0X
description: A laser-based Time-of-Flight Distance Sensor with 5-120cm range.
---

## Pinout

| Name | Description |
|---|---|
| VIN | Voltage supply, 3-5V, use same voltage as MCU logic level |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |
| GPIO | Interrupt output; optional |
| XSHUT | Reset input; active low; optional |

## Operation

- VL53L0X uses **I2C** with address '0x29'.
- For Aruidno-based systems, use `Adafruit_VL53L0X Library`.
