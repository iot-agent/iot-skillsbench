---
name: LCD1602 Display via I2C (HD44780 + PCF8574 Backpack)
description: This skill covers the 16×2 LCD with I2C PCF8574 backpack. Includes initialization, text display, cursor positioning, backlight control, and blinking patterns. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# LCD1602 Display via I2C (HD44780 + PCF8574 Backpack)

## Overview
The LCD1602 is a 16-column × 2-row character display. In I2C mode, a PCF8574 I/O expander connects the HD44780 controller to the I2C bus, reducing wiring from 6–8 GPIO pins to 2 (SDA + SCL).

## Hardware Specs
- **Interface:** I2C (via PCF8574 expander)
- **I2C Address:** 0x27 (PCF8574A) or 0x3F (PCF8574) — check with scanner
- **Display:** 16 characters × 2 rows (HD44780 controller)
- **Backlight:** Controlled via PCF8574 bit 3 (HIGH = on)

## PCF8574 Pin Mapping to HD44780
```
PCF8574 bit 7 → HD44780 D7
PCF8574 bit 6 → HD44780 D6
PCF8574 bit 5 → HD44780 D5
PCF8574 bit 4 → HD44780 D4
PCF8574 bit 3 → Backlight (HIGH = on)
PCF8574 bit 2 → EN (Enable)
PCF8574 bit 1 → RW (always LOW for write)
PCF8574 bit 0 → RS (0=command, 1=data)
```

## HD44780 Commands
```
0x01  Clear display
0x02  Return home (cursor to 0,0)
0x04  Entry mode: cursor left shift, no display shift
0x06  Entry mode: cursor right shift (standard)
0x08  Display off
0x0C  Display on, cursor off, no blink
0x0E  Display on, cursor on, no blink
0x0F  Display on, cursor on, blink
0x10  Cursor shift left
0x14  Cursor shift right
0x18  Display shift left
0x1C  Display shift right
0x28  4-bit mode, 2 lines, 5×8 dots
0x38  8-bit mode, 2 lines, 5×8 dots
0x80  Set DDRAM address to 0x00 (row 0, col 0)
0xC0  Set DDRAM address to 0x40 (row 1, col 0)
```

---

## ATMega2560 + Arduino Implementation (LiquidCrystal_I2C Library)

```cpp
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

/* 0x27 is most common; scan if unsure */
LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
    Wire.begin();
    lcd.init();
    lcd.backlight();  /* Turn on backlight */
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Hello World");
}

/* Set cursor: col (0-15), row (0-1) */
void lcd_print(uint8_t col, uint8_t row, const char *text) {
    lcd.setCursor(col, row);
    lcd.print(text);
}

/* Blink backlight effect (for alerts) */
void lcd_blink_backlight(int times, int period_ms) {
    for (int i = 0; i < times; i++) {
        lcd.noBacklight();
        delay(period_ms / 2);
        lcd.backlight();
        delay(period_ms / 2);
    }
}

/* Display power info: Voltage: 5.0V / Current: 500mA */
void lcd_show_power(float v, float i_mA) {
    char buf[17];
    lcd.clear();
    snprintf(buf, sizeof(buf), "V: %.1fV", v);
    lcd.setCursor(0, 0); lcd.print(buf);
    snprintf(buf, sizeof(buf), "I: %dmA", (int)i_mA);
    lcd.setCursor(0, 1); lcd.print(buf);
}

/* Display GPS coordinates */
void lcd_show_gps(double lat, double lon) {
    char buf[17];
    lcd.clear();
    snprintf(buf, sizeof(buf), "Lat:%.5f", lat);
    lcd.setCursor(0, 0); lcd.print(buf);
    snprintf(buf, sizeof(buf), "Lon:%.5f", lon);
    lcd.setCursor(0, 1); lcd.print(buf);
}

/* Air quality panel with warning */
void lcd_air_quality(uint16_t pm25, uint16_t voc, bool warning) {
    char buf[17];
    lcd.clear();
    snprintf(buf, sizeof(buf), "PM2.5:%u VOC:%u", pm25, voc);
    lcd.setCursor(0, 0); lcd.print(buf);
    if (warning) {
        lcd.setCursor(0, 1); lcd.print("!! WARNING !!");
        lcd_blink_backlight(3, 500);
    } else {
        lcd.setCursor(0, 1); lcd.print("Air: OK");
    }
}

/* Biometric access display */
void lcd_access(bool granted) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(granted ? "Access Granted" : "Access Denied");
}

void loop() {
    lcd.clear();
    lcd.setCursor(0, 0); lcd.print("IoT Bench");
    lcd.setCursor(0, 1); lcd.print("Running...");
    delay(1000);
}
```

---

## ESP32 + ESP-IDF Implementation (Direct I2C)

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>

#define LCD_ADDR  0x27
#define LCD_BACKLIGHT 0x08
#define LCD_EN    0x04
#define LCD_RW    0x00  /* always write */
#define LCD_RS    0x01  /* 0=command, 1=data */

/* Write one byte to PCF8574 */
static void lcd_write_i2c(uint8_t data) {
    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (LCD_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(hdl, data, true);
    i2c_master_stop(hdl);
    i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(10));
    i2c_cmd_link_delete(hdl);
}

/* Pulse the EN pin to latch data (4-bit mode) */
static void lcd_pulse_en(uint8_t data) {
    lcd_write_i2c(data | LCD_EN | LCD_BACKLIGHT);
    vTaskDelay(pdMS_TO_TICKS(1));
    lcd_write_i2c((data & ~LCD_EN) | LCD_BACKLIGHT);
    vTaskDelay(pdMS_TO_TICKS(1));
}

/* Write 4 bits (nibble) */
static void lcd_write_nibble(uint8_t nibble, uint8_t rs) {
    uint8_t data = (nibble << 4) | rs | LCD_BACKLIGHT;
    lcd_pulse_en(data);
}

/* Write full byte as two nibbles */
static void lcd_write_byte(uint8_t byte, uint8_t rs) {
    lcd_write_nibble((byte >> 4) & 0x0F, rs);
    lcd_write_nibble(byte & 0x0F, rs);
    vTaskDelay(pdMS_TO_TICKS(2));
}

void lcd_cmd(uint8_t cmd)  { lcd_write_byte(cmd,  0); }
void lcd_data(uint8_t dat) { lcd_write_byte(dat,  LCD_RS); }

void lcd_init(void) {
    vTaskDelay(pdMS_TO_TICKS(50));  /* power-on delay */
    /* Initialize in 4-bit mode */
    lcd_write_nibble(0x03, 0); vTaskDelay(pdMS_TO_TICKS(5));
    lcd_write_nibble(0x03, 0); vTaskDelay(pdMS_TO_TICKS(1));
    lcd_write_nibble(0x03, 0); vTaskDelay(pdMS_TO_TICKS(1));
    lcd_write_nibble(0x02, 0); /* set 4-bit mode */

    lcd_cmd(0x28); /* 4-bit, 2 lines, 5x8 */
    lcd_cmd(0x0C); /* display on, cursor off */
    lcd_cmd(0x06); /* increment cursor right */
    lcd_cmd(0x01); /* clear display */
    vTaskDelay(pdMS_TO_TICKS(2));
}

void lcd_set_cursor(uint8_t col, uint8_t row) {
    uint8_t row_offsets[] = {0x00, 0x40};
    lcd_cmd(0x80 | (col + row_offsets[row]));
}

void lcd_print(const char *str) {
    while (*str) lcd_data(*str++);
}

void lcd_clear(void) {
    lcd_cmd(0x01);
    vTaskDelay(pdMS_TO_TICKS(2));
}

void lcd_backlight(bool on) {
    /* Write LCD_BACKLIGHT bit directly */
    lcd_write_i2c(on ? LCD_BACKLIGHT : 0);
}

void lcd_task(void *arg) {
    lcd_init();
    lcd_set_cursor(0, 0); lcd_print("ESP32 IoT");
    lcd_set_cursor(0, 1); lcd_print("Bench Ready");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* Zephyr: use the HD44780 driver if available, or port ESP32 I2C approach */
/* The Zephyr character_display driver supports HD44780 with PCF8574 backpack */

/* prj.conf */
// CONFIG_CHARACTER_FRAMEBUFFER=y
// CONFIG_CHARACTER_FRAMEBUFFER_SHELL=n
// CONFIG_I2C=y

/* Alternatively: directly use I2C with the same bit-banging approach */
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <string.h>

#define LCD_ADDR 0x27
#define LCD_BACKLIGHT 0x08
#define LCD_EN  0x04
#define LCD_RS  0x01

static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

static void lcd_i2c_write(uint8_t data) {
    i2c_write(i2c_dev, &data, 1, LCD_ADDR);
}

static void lcd_pulse_en(uint8_t data) {
    lcd_i2c_write(data | LCD_EN | LCD_BACKLIGHT);
    k_usleep(100);
    lcd_i2c_write((data & ~LCD_EN) | LCD_BACKLIGHT);
    k_usleep(100);
}

static void lcd_nibble(uint8_t nibble, uint8_t rs) {
    lcd_pulse_en((nibble << 4) | rs | LCD_BACKLIGHT);
}

static void lcd_byte(uint8_t b, uint8_t rs) {
    lcd_nibble((b >> 4) & 0xF, rs);
    lcd_nibble(b & 0xF, rs);
    k_msleep(2);
}

void zephyr_lcd_init(void) {
    k_msleep(50);
    lcd_nibble(0x03, 0); k_msleep(5);
    lcd_nibble(0x03, 0); k_msleep(1);
    lcd_nibble(0x03, 0); k_msleep(1);
    lcd_nibble(0x02, 0);
    lcd_byte(0x28, 0);
    lcd_byte(0x0C, 0);
    lcd_byte(0x06, 0);
    lcd_byte(0x01, 0);
    k_msleep(2);
}

void zephyr_lcd_set_cursor(uint8_t col, uint8_t row) {
    uint8_t addr = (row == 0) ? 0x80 + col : 0xC0 + col;
    lcd_byte(addr, 0);
}

void zephyr_lcd_print(const char *str) {
    while (*str) lcd_byte(*str++, LCD_RS);
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    zephyr_lcd_init();
    zephyr_lcd_set_cursor(0, 0);
    zephyr_lcd_print("nRF52840 Zephyr");
    zephyr_lcd_set_cursor(0, 1);
    zephyr_lcd_print("LCD Ready");
    return 0;
}
```

## Best Practices
1. Use LiquidCrystal_I2C library on Arduino — handles all 4-bit protocol details
2. Scan for the correct I2C address (0x27 or 0x3F) with an I2C scanner
3. `lcd.clear()` takes ~2ms — avoid calling it in tight loops
4. Format numbers with `snprintf()` before printing to avoid partial updates
5. For alert blinking: toggle backlight, not the display content, for faster visual feedback

## Common Pitfalls
- ❌ Wrong I2C address (use scanner to find 0x27 or 0x3F)
- ❌ Not calling `lcd.init()` and `lcd.backlight()` in setup
- ❌ Printing strings longer than 16 chars — wraps incorrectly on HD44780
- ❌ Not clearing before writing (leftover characters remain visible)
- ❌ Missing Wire.begin() before lcd.init()

## Related Skills
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C
- `ina219-power-sensor.md` - Power data for LCD display
- `gps-nmea-uart.md` - GPS coordinates for LCD display
