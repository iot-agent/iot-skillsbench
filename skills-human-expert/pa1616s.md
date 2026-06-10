---
name: PA1616S
description: A GPS module.
---

## Operation

- Utilize UART as serial communication protocol.
- NMEA Output Sentences: 
    - GGA: Time, position and fix type data.
    - GSA: GPS receiver operating mode, active satellites used in the position solution and DOP values.
    - GSV: The number of GPS satellites in view satellite ID numbers, elevation, azimuth, and SNR values.
    - RMC: Time, date, position, course and speed data. Recommended Minimum Navigation Information.
    - VTG: Course and speed information relative to the ground.