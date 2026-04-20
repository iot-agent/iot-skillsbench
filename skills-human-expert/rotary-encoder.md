---
name: Rotary Encoder
description: KY-040 low-cost incremental rotary encoder module that provides 360-degree rotational input and direction tracking with an integrated push-button switch.
---

## Operation
Detect **rotation direction** in clockwise (CW) or counterclockwise (CCW) using a quadrature rotary encoder with two digital signals: **CLK** and **DT**, both configured as input.

- Monitor **state changes on CLK**
- On each **falling edge of CLK**: Read `DT` and determine direction:
    - If `DT = HIGH`, direction is **clockwise (CW)**
    - If `DT = LOW`, direction is **counterclockwise (CCW)**
- Do not implement edge detection using ISR tied to GPIO pin unless specified