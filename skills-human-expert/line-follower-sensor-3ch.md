---
name: Line Follower Sensor (3-channel)
description: A 3-channel IR reflectance module that outputs left (L), middle (M), and right (R) line detection signals.
---

## Pinout

| Name | Description |
|---|---|
| GND | Ground |
| VCC | Voltage supply (typically 3.3V to 5V) |
| L   | Left IR sensor digital output |
| M   | Middle IR sensor digital output |
| R   | Right IR sensor digital output |

## Operation

- The module uses IR reflection to detect surface contrast. White/bright surfaces reflect more IR, while black/dark lines reflect less.

- Read `L`, `M`, and `R` together each control cycle to infer line position:
    - `010`: centered on line
    - `110` or `011`: line is slightly offset
    - `100` or `001`: line is far to one side
    - `000` or `111`: line lost or ambiguous (depends on module polarity and track)

- Output polarity may differ by board (some are active `LOW` on black line, some active `HIGH`). Confirm logic by testing sensor values over both line and background before writing control rules.

- Keep sensor height and angle stable above the floor, and tune onboard threshold potentiometers (if available) to reduce false triggers from ambient light.

- Sample at a fixed interval (e.g., 10 millisecond) and apply brief debouncing or majority filtering to avoid oscillation in steering decisions.
