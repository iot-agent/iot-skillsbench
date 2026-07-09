---
name: MPU6050
description: A 6-axis inertial measurement unit (IMU) with a 3-axis gyroscope and a 3-axis accelerometer.
---

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| SCL | I2C clock line |
| SDA | I2C data line |
| AD0 | I2C addr select pin |

## Operation

- Always convert raw MPU6050 readings using correct sensitivity (LSB/g, LSB/dps) to get values in g and deg/s.

- Define and document axis/sign convention before control tuning, e.g., positive yaw rate (`Gz`) corresponds to turning left (counterclockwise, CCW).

- Keep heading and control equations consistent with that convention, for example `error = targetHeading - currentHeading`, and verify with a manual turn test that positive error produces the intended steering direction.

- Normalize accel and gyro separately by their configured ranges (e.g., ±2g, ±250 dps) to map values into ~[-1, 1].

- Unless mentioned otherwise, display/print in format of "A[g]: X=+0.00 Y=-0.00 Z=+1.00" and "G[d/s]: X=+1.20 Y=-0.40 Z=+0.00"

- For Arduino-based systems, the `Adafruit MPU6050 library` is recommended.