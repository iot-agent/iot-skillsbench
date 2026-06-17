---
name: DS1307
description: A binary-coded decimal (BCD) serial real-time clock (RTC).
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

- DS1307 has an **I2C** device address of `0x68`, always write to and read from this address.