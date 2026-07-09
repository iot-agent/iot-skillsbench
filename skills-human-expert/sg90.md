---
name: SG90 Micro Servo
description: A 9g hobby servo motor controlled by PWM pulse width.
---

## Pinout

| Name | Description |
|---|---|
| GND | Ground |
| VCC | Voltage supply (typically 4.8V to 6V) |
| SIG | PWM control signal |

## Operation

- SG90 is controlled by a ~50Hz PWM frame (period about 20 milliseconds). Pulse width range to prevent mechanical stall is ~0.5 to 2.4 milliseconds

- Servo angle is determined by pulse width, not duty cycle percentage. Typical pulse width mapping (exact endpoints vary by unit):
    - ~1.0 milliseconds for ~0 degrees
    - ~1.5 milliseconds for ~90 degrees
    - ~2.0 milliseconds for ~180 degrees

- It would be helpful to start from center pointing direction (~1.5 milliseconds) during initialization
