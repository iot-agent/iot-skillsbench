---
name: SGP40
description: A digital VOC (volatile organic compounds) sensor.
---

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |

## Operation

- SGP40 communicates via the **I2C** protocol and uses a fixed I2C device address of `0x59`.

- The main output is a **VOC Index** (typically 0-500 after algorithm processing):
	- **100**: baseline indoor air quality (24-hour average);
	- **>100**: air quality is getting worse;
	- **<100**: air quality is improving.

- SGP40 provides a **raw gas signal** that should be converted to VOC Index by a gas-index algorithm (for example, Sensirion's VOC Algorithm). Use a sampling interval of about **1 second** for stable index updates.

- SGP40 does **not** output an absolute VOC concentration in ppm directly. Avoid treating the reading as exact ppm without a separate calibration model.

- For better stability, apply **temperature/humidity compensation** during measurement (or use default compensation values if no RH/T sensor is available).