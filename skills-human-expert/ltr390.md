---
name: LTR390
description: An integrated ambient light sensor (ALS) and ultraviolet light sensor (UVS).
---

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |
| INT (optional) | Interrupt output for threshold events |

## Operation

- LTR390 communicates via the **I2C** protocol and uses a fixed I2C device address of `0x53`.

- It supports two sensing channels:
	- **ALS**: ambient visible light sensing;
	- **UVS**: ultraviolet sensing data used to estimate UV index.

- The sensor provides digital readings (ADC counts), not direct lux/UVI by default. Convert counts to application-level values using driver/library formulas.

- Key measurement controls:
	- **Gain**: selectable (for adapting to dim or bright scenes);
	- **Integration time**: configurable (trade-off between response speed and noise).

- For stable measurements, choose gain and integration time to avoid saturation, and average several samples if readings are noisy.

- The **INT** pin can be used to trigger events when readings cross configured upper/lower thresholds.