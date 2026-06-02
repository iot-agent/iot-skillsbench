---
name: PMSA003I
description: A laser-based particular matter (PM) air quality sensor.
---

## Operation

- I2C interface.
- The I2C data stream updates once per second, you'll get:
    - PM1.0, PM2.5 and PM10.0 concentration in both standard & environmental units.
    - Particulate matter per 0.1L air, categorized into 0.3um, 0.5um, 1.0um, 2.5um, 5.0um, and 10um size bins.
    - checksum, in binary format.