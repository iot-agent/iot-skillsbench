---
name: MAX30101 & MAX32664
description: The SparkFun Pulse Oximeter and Heart Rate Sensor.
---

The SparkFun Pulse Oximeter and Heart Rate Sensor is an I2C-based biometric module using two chips from Maxim Integrated: the **MAX32664** biometric sensor hub and the **MAX30101** optical pulse-oximetry front end.

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |
| MFIO (optional) | Mode/control pin used by the sensor hub |
| RST (optional)  | Hardware reset pin |
| INT (optional)  | Data-ready interrupt output |

## Operation

- The module communicates via the **I2C** protocol, and the MAX32664 sensor hub is typically accessed at I2C address `0x55`.

- Output metrics are algorithm-processed biometric values, typically including:
	- **Heart Rate (BPM)**;
	- **SpO2 (%)**.

- For reliable readings:
	- Keep the finger steady with consistent contact pressure;
	- Reduce ambient light leakage into the optical path;
	- Allow a short settling window before trusting displayed values.

- Data quality depends on perfusion and motion. Strong movement, poor contact, or cold fingers can cause unstable or invalid readings.

- The sensor internally uses red/IR (and optionally green) LED photoplethysmography data, while the MAX32664 runs filtering and estimation algorithms before publishing results.

- If available on your board, use **INT** for data-ready signaling and **RST/MFIO** for robust startup/reset handling.