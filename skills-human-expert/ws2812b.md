---
name: WS2812B RGB LED
description: A digitally addressable RGB LED that communicates via a single-wire serial protocol to display colors and effects.
---

## Pinout

| Name | Description |
|---|---|
| GND  | Ground |
| VCC  | Voltage supply (typically 5V) |
| DIN  | Data input; serial signal from MCU |
| DOUT | Data output; can chain to next LED/segment |

## Operation

- WS2812B uses NeoPixel protocol: a single GPIO pin sends a high-speed bit stream (800 kHz nominal) where bit timing defines `0` and `1` states. A `0` bit is ~0.4 μs HIGH; a `1` bit is ~0.8 μs HIGH; the total bit period is ~1.25 μs.

- Each LED requires a 24-bit color frame: 8 bits for each color. Send MSB first.

- **Daisy Chain Mode**: connect `DOUT` of one LED to `DIN` of the next. Send all color data in sequence; each chip absorbs its frame and relays the rest downstream.

- Use a current-limiting resistor (~470 Ω) on the `DIN` line and a small capacitor (~100 nF) across VCC and GND near the LED supply to reduce noise and ringing.

- Typical brightness is full 24-bit (0–255 per channel), enable all three RGB channels with the same value if no specific color channel is mentioned. Note that dimming via software (reduce values) is preferable to avoid brownout on the power supply. A chain of many LEDs can draw significant current; use a dedicated 5V supply if driving many pixels.

- For Arduino-based systems, the `Adafruit NeoPixel library` is recommended. Configure `NEO_GRB` so that the 24-bit color frame encoding follows the R-G-B order.
