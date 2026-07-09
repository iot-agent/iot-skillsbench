---
name: INA219
description: A current shunt and power monitor that measures high side voltage and DC current draw.
---

## Pinout

| Name | Description |
|---|---|
| VIN  | Voltage supply |
| GND  | Ground |
| SCL  | I2C clock line (with 10K pullup) |
| SDA  | I2C data line (with 10K pullup) |
| VIN+ | Positive input pin |
| VIN- | Negative input pin |

## Operation

- Default I2C addr is `0x40`

- The INA219 senses across shunts on buses that can vary from 0 to 26 V. 

- `Vin+` is the positive input pin: Connect to supply for high side current sensing or to load ground for low side sensing.

- `Vin-` is the negative input pin: Connect to load for high side current sensing or to board ground for low side sensing