---
name: Joystick
description: A 2-axis analog joystick module (KY-023).
---

## Pinout

| Name | Description |
|---|---|
| GND | Ground |
| VCC | Voltage supply |
| VRx | Horizontal axis output (analog) |
| VRy | Vertical axis output (analog) |
| SW  | Push button |

## Operation

- The idle position voltage is VCC/2. Moving the joystick along the vertical axis changes the voltage of the `VRy` pin from 0 volts (bottom) to VCC (top). Moving the joystick along the horizontal axis changes the voltages of `VRx` from 0 volts (right) to VCC (left).

- Apply a small "Dead Zone" to remove jitter: Small fluctuations around the center (e.g., +/- 20-50) should not be treated as movement. Also, do not sample too fast: Set a MINIMUM sampling interval of 0.1 second.