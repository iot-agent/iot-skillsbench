---
name: TB6612FNG Motor Driver
description: A dual H-bridge motor driver IC that can drive two DC motors or one bipolar stepper motor.
---

## Pinout

| Name | Description |
|---|---|
| GND  | Ground |
| VCC  | Logic supply (2.7V to 5.5V, connect to MCU voltage) |
| VM   | Motor power supply (2.5V to 13.5V) |
| STBY | Standby pin; drive HIGH to enable the chip, LOW to put it in standby |
| AIN1 | Motor A direction input 1 |
| AIN2 | Motor A direction input 2 |
| PWMA | Motor A PWM speed input |
| BIN1 | Motor B direction input 1 |
| BIN2 | Motor B direction input 2 |
| PWMB | Motor B PWM speed input |
| AO1  | Motor A output 1 |
| AO2  | Motor A output 2 |
| BO1  | Motor B output 1 |
| BO2  | Motor B output 2 |

## Operation

- Always drive `STBY` to `HIGH` before sending any motion commands. Leaving `STBY` as `LOW` disables both channels regardless of other inputs.

- `AIN2` and `BIN2` are **not connected** to any control pins as they hard-wired to `AIN1` (Right Wheel) and `BIN1` (Left Wheel) through SN74LVC2G14 dual Schmitt-trigger inverter.

- **Direction control** per channel is set by the `xIN1` / `xIN2` pair:

    | AIN1 | BIN1 | Result |
    |---|---|---|
    | HIGH | HIGH | Both wheels forward |
    | LOW  | LOW  | Both wheels backward |
    | LOW  | HIGH | Right wheel forward, left wheel backward |
    | HIGH | LOW  | Left wheel forward, right wheel backward |

- **Speed control:** apply a PWM signal on `PWMA` / `PWMB`. Setting `PWMx` LOW coasts the channel; setting it HIGH always enables full speed. Typical PWM frequency is 10 kHz to 100 kHz.

- For closed-loop steering, validate motor-side correction sign on the real robot: if your controller defines positive heading error as ``need to steer left'', positive correction must speed the right wheel and/or slow the left wheel.

- **Stepper motor use:** wire the two stepper coils to channel A (AO1/AO2) and channel B (BO1/BO2). Step through the coil energization sequence (full-step or half-step) by toggling `AIN1`, `AIN2`, `BIN1`, `BIN2` in the correct order, keeping `PWMA` and `PWMB` HIGH.

- The chip has a built-in thermal shutdown and overcurrent protection, but still ensure VM current stays within the 1.2 A continuous (3 A peak) rating per channel.
