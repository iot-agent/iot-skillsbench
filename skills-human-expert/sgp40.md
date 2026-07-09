---
name: SGP40
description: A digital VOC (volatile organic compounds) sensor.
---

## Pinout

| Name | Description |
|---|---|
| VIN | Voltage supply, 3-5V, use same voltage as MCU logic level |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |

## Operation

- I2C interface with address 0x59
- For Aruidno framework, use `Adafruit_SGP40.h` in `Adafruit SGP40 Sensor` library.
    - Initialize with Adafruit_SGP40::begin();
    - Relevant functions include uint16_t measureRaw(float temperature = 25, float humidity = 50) and int32_t measureVocIndex(float temperature = 25, float humidity = 50), where the temperature and humidity (optional) are for compensation.
