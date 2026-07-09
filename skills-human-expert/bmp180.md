---
name: BMP180
description: A digital sensor for barometric pressure and temperature.
---

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |

## Operation

- BMP180 communicates via the **I2C** protocol and has an I2C device address of `0x77`, always write to and read from this address.

- Attributes and detection range:
    - **Temperature**: -40°C to 85°C;
    - **Pressure**: 30000 Pa to 110000 Pa (300 hPa to 1100 hPa).

- For Arduino-based systems, the `Adafruit BMP085/BMP180 library` is recommended.