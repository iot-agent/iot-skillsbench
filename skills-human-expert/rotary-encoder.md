---
name: Rotary Encoder
description: An incremental rotary encoder module that provides 360-degree rotational input and direction tracking with an integrated push-button switch (KY-040).
---

## Pinout

| Name | Description |
|---|---|
| CLK | Rotary encoder pin A |
| DT  | Rotary encoder pin B |
| SW  | Push button pin. Normally open, shorted to GND on press |
| VCC | Voltage supply |
| GND | Ground |

## Operation
Detect **rotation direction** in clockwise (CW) or counterclockwise (CCW) using a quadrature rotary encoder with two digital signals: **CLK** and **DT**, both configured as input.

- Monitor **state changes on CLK**

- On each **falling edge of CLK**: Read `DT` and determine direction:
    - If `DT = HIGH`, direction is **clockwise (CW)**
    - If `DT = LOW`, direction is **counterclockwise (CCW)**

- Do not implement edge detection using ISR tied to GPIO pin unless specified