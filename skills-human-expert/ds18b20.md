---
name: DS18B20 Temperature Sensor
description: A digital temperature sensor.
---

The DS18B20 is a digital temperature sensor by Maxim Integrated that communicates
over a single data line (1-Wire protocol). It can be powered directly from the data
line (parasite power mode) or from a separate VDD (3.0V to 5.5V), making it ideal
for remote or multi-sensor applications since multiple sensors can share the same wire.

| Property | Value |
|---|---|
| Temperature Range | -55°C to +125°C |
| Accuracy | ±0.5°C (from -10°C to +85°C) |
| Resolution | 9 to 12-bit (configurable) |
| Supply Voltage | 3.0V to 5.5V |
| Interface | 1-Wire (single data line) |
| Package | TO-92, SO-8, µSOP |

---

## 1-Wire Timing (from datasheet)

### Reset / Presence

| Step | Who | Duration |
|---|---|---|
| Reset pulse (LOW) | Master | min 480 µs |
| Release, wait HIGH | Master releases | min 480 µs |
| Presence-Detect HIGH (before ACK) | DS18B20 waits | 15–60 µs |
| Presence-Detect LOW (ACK pulse) | DS18B20 pulls LOW | 60–240 µs |

### Write Bits

| Bit | Master pulls LOW | Notes |
|---|---|---|
| Write 0 | 60–120 µs | Entire time slot held LOW |
| Write 1 | 1–15 µs | Release early, pull-up restores HIGH |

### Read Bit

| Parameter | Value |
|---|---|
| Master init pulse (LOW) | ~1 µs (within Write 1 low time: 1–15 µs) |
| Data valid window (t_RDV) | max 15 µs after master releases |
| Time slot (t_SLOT) | 60–120 µs |
| Recovery time between slots (t_REC) | min 1 µs |

> Master must sample the line **within 15 µs** of releasing it during a read slot.

### Temperature Conversion Time (t_CONV)

| Resolution | Max Time |
|---|---|
| 9-bit  | 93.75 ms |
| 10-bit | 187.5 ms |
| 11-bit | 375 ms |
| 12-bit | 750 ms |

> After issuing Convert T, strong pull-up must be applied within **10 µs** (t_SPON).