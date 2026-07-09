---
name: LCD1602
description: A 16-character, 2-line liquid crystal display (LCD) based on the Hitachi HD44780 controller.
---

## Pinout (4-bit mode)

| Pin | Name | Description |
|---|---|---|
| RS | Register Select | LOW = command, HIGH = data |
| RW | Read/Write | LOW = write, HIGH = read (tie to GND for write-only) |
| E | Enable | Latches data on falling edge |
| D4–D7 | Data bits | Upper nibble in 4-bit mode |

## Operation

LCD1602 operates in either 8-bit or 4-bit parallel mode. 4-bit mode is the most common as it requires fewer GPIO pins (6 total: RS, E, D4–D7).

### Enable Pulse Timing

Data is latched on the **falling edge** of the E pin.
While datasheets specify minimums (e.g., 450ns), real-world clones and high-speed controllers require much larger margins for signal stability.

**Recommended Robust Timing:**
E LOW → E HIGH → hold HIGH 1ms → E LOW → hold LOW 1ms → settle 37µs

    ____
E: |    |

^ setup  ^ hold 1ms (Robustness)
^ falling edge latches data
^ hold 1ms (Robustness)


For `LCD_CLEAR` and `LCD_RETURN_HOME` commands, wait at least **1.52ms** after
sending — these take longer than other commands.

### 4-bit Initialization Sequence

The HD44780 must be initialized with a specific sequence after power-on.
The delays between steps are mandatory.

**Warning:** Never wrap the initialization sequence (sending `0x03` three times) in a retry loop. If the LCD is already in 4-bit mode, receiving an extra `0x03` will be parsed as a high nibble, permanently desynchronizing the internal state machine.

Power on → wait 50ms

Send nibble 0x03 → wait >4.1ms
Send nibble 0x03 → wait >4.1ms
Send nibble 0x03 → wait >100µs
Send nibble 0x02 → wait >100µs   (switch to 4-bit mode)

Send Function Set  (0x28: 4-bit, 2-line, 5x8)  → wait 1ms
Send Display ON    (0x0C: display on, no cursor) → wait 1ms
Send Clear Display (0x01)                        → wait 2ms
Send Entry Mode    (0x06: increment, no shift)   → wait 1ms

### Writing a Byte in 4-bit Mode

Each byte is sent as two nibbles, high nibble first:
Set RS (0=command, 1=data)
Send high nibble (D7–D4) → pulse E
Send low nibble  (D3–D0) → pulse E
Wait 37µs

### Common Commands

| Command | Hex | Description | Execution Time |
|---|---|---|---|
| Clear Display | 0x01 | Clear screen, cursor home | 1.52ms |
| Return Home | 0x02 | Cursor to (0,0) | 1.52ms |
| Entry Mode Set | 0x06 | Increment cursor (RIGHT), no shift | 37µs |
| Display ON | 0x0C | Display on, cursor off | 37µs |
| Function Set 4-bit | 0x28 | 4-bit, 2-line, 5x8 font | 37µs |

### Cursor Positioning (DDRAM Address)

To maintain consistency with standard matrix addressing and prevent inversion errors, always define cursor functions using the **(row, column)** convention.

Row 0 starts at DDRAM address 0x00
Row 1 starts at DDRAM address 0x40

Set cursor: send command (0x80 | address)

Example: Row 1, Column 5 → 0x80 | (0x40 + 5) = 0xC5
