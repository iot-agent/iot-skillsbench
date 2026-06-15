---
name: DS1307 Real-Time Clock (RTC) via I2C
description: This skill covers the DS1307 RTC module via I2C. Includes register map (BCD format), reading/setting date and time, and timestamp formatting for data logging. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# DS1307 Real-Time Clock (RTC) via I2C

## Overview
The DS1307 is a low-power I2C RTC that tracks seconds, minutes, hours, day, date, month, and year with leap-year compensation. Time is stored in BCD (Binary-Coded Decimal) format.

## Hardware Specs
- **Interface:** I2C
- **I2C Address:** 0x68 (fixed)
- **Supply:** 5V (crystal requires 5V for standard operation)
- **Backup:** CR2032 battery via VBAT pin
- **Crystal:** 32.768 kHz (external)

## Register Map (0x00–0x06)
```
Reg 0x00: Seconds  (BCD, bit 7 = CH clock halt: 0=running, 1=halted)
Reg 0x01: Minutes  (BCD)
Reg 0x02: Hours    (BCD, bit 6 = 12/24 mode: 0=24h, 1=12h; bit 5 in 12h mode = AM/PM)
Reg 0x03: Day      (BCD, 1=Sunday–7=Saturday)
Reg 0x04: Date     (BCD, 1–31)
Reg 0x05: Month    (BCD, 1–12)
Reg 0x06: Year     (BCD, 00–99, represents 2000–2099)
Reg 0x07: Control  (SQWE, RS1, RS0 for square-wave output)
Reg 0x08–0x3F: RAM (56 bytes of battery-backed SRAM)
```

## BCD Conversion
```c
uint8_t bcd_to_dec(uint8_t bcd) { return (bcd >> 4) * 10 + (bcd & 0x0F); }
uint8_t dec_to_bcd(uint8_t dec) { return ((dec / 10) << 4) | (dec % 10); }
```

---

## ATMega2560 + Arduino Implementation

### Using RTClib (Adafruit)
```cpp
#include <Wire.h>
#include <RTClib.h>

RTC_DS1307 rtc;

void setup() {
    Wire.begin();
    Serial.begin(115200);

    if (!rtc.begin()) {
        Serial.println("DS1307 not found");
        while (1);
    }

    /* Set time if RTC is not running */
    if (!rtc.isrunning()) {
        /* Set to compile time */
        rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
        /* Or set explicitly: rtc.adjust(DateTime(2026, 6, 15, 12, 0, 0)); */
    }
}

void loop() {
    DateTime now = rtc.now();
    char buf[32];
    snprintf(buf, sizeof(buf), "%04d/%02d/%02d %02d:%02d:%02d",
             now.year(), now.month(), now.day(),
             now.hour(), now.minute(), now.second());
    Serial.println(buf);
    delay(1000);
}

/* Get timestamp string for data logging */
void getTimestamp(char *buf, size_t len) {
    DateTime now = rtc.now();
    snprintf(buf, len, "%04d-%02d-%02d %02d:%02d:%02d",
             now.year(), now.month(), now.day(),
             now.hour(), now.minute(), now.second());
}
```

### Manual I2C (without RTClib)
```cpp
#include <Wire.h>
#define DS1307_ADDR 0x68

uint8_t bcd_to_dec(uint8_t b) { return (b >> 4) * 10 + (b & 0xF); }
uint8_t dec_to_bcd(uint8_t d) { return ((d / 10) << 4) | (d % 10); }

struct DS1307Time {
    uint8_t sec, min, hour, day, date, month, year;
};

void ds1307_read(DS1307Time *t) {
    Wire.beginTransmission(DS1307_ADDR);
    Wire.write(0x00);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)DS1307_ADDR, (uint8_t)7);
    t->sec   = bcd_to_dec(Wire.read() & 0x7F);  /* strip CH bit */
    t->min   = bcd_to_dec(Wire.read() & 0x7F);
    t->hour  = bcd_to_dec(Wire.read() & 0x3F);  /* strip 12/24 bits */
    t->day   = bcd_to_dec(Wire.read() & 0x07);
    t->date  = bcd_to_dec(Wire.read() & 0x3F);
    t->month = bcd_to_dec(Wire.read() & 0x1F);
    t->year  = bcd_to_dec(Wire.read());
}

void ds1307_set(const DS1307Time *t) {
    Wire.beginTransmission(DS1307_ADDR);
    Wire.write(0x00);                   /* start at seconds register */
    Wire.write(dec_to_bcd(t->sec));     /* bit 7 = 0 (start clock) */
    Wire.write(dec_to_bcd(t->min));
    Wire.write(dec_to_bcd(t->hour));    /* 24h mode */
    Wire.write(dec_to_bcd(t->day));
    Wire.write(dec_to_bcd(t->date));
    Wire.write(dec_to_bcd(t->month));
    Wire.write(dec_to_bcd(t->year));    /* 2-digit year */
    Wire.endTransmission();
}

void setup() {
    Wire.begin();
    Serial.begin(115200);

    /* Set time to 2026/06/15 12:00:00 */
    DS1307Time t = {0, 0, 12, 2, 15, 6, 26};  /* sec,min,hr,day,date,mon,yr */
    ds1307_set(&t);
}

void loop() {
    DS1307Time t;
    ds1307_read(&t);
    char buf[32];
    snprintf(buf, sizeof(buf), "20%02d/%02d/%02d %02d:%02d:%02d",
             t.year, t.month, t.date, t.hour, t.min, t.sec);
    Serial.println(buf);
    delay(1000);
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define DS1307_ADDR 0x68
/* Use i2c_read_bytes/i2c_write_bytes from i2c-communication-esp32-esp-idf.md */

static uint8_t bcd2dec(uint8_t b) { return (b >> 4) * 10 + (b & 0xF); }
static uint8_t dec2bcd(uint8_t d) { return ((d / 10) << 4) | (d % 10); }

typedef struct { uint8_t sec, min, hour, day, date, month, year; } ds1307_time_t;

void ds1307_read(ds1307_time_t *t) {
    uint8_t buf[7];
    i2c_read_bytes(DS1307_ADDR, 0x00, buf, 7);
    t->sec   = bcd2dec(buf[0] & 0x7F);
    t->min   = bcd2dec(buf[1] & 0x7F);
    t->hour  = bcd2dec(buf[2] & 0x3F);
    t->day   = bcd2dec(buf[3] & 0x07);
    t->date  = bcd2dec(buf[4] & 0x3F);
    t->month = bcd2dec(buf[5] & 0x1F);
    t->year  = bcd2dec(buf[6]);
}

void ds1307_set(const ds1307_time_t *t) {
    uint8_t buf[7];
    buf[0] = dec2bcd(t->sec);    /* CH=0 to start clock */
    buf[1] = dec2bcd(t->min);
    buf[2] = dec2bcd(t->hour);
    buf[3] = dec2bcd(t->day);
    buf[4] = dec2bcd(t->date);
    buf[5] = dec2bcd(t->month);
    buf[6] = dec2bcd(t->year);
    i2c_write_bytes(DS1307_ADDR, 0x00, buf, 7);
}

/* Format timestamp for logging */
void ds1307_timestamp(char *buf, size_t len) {
    ds1307_time_t t;
    ds1307_read(&t);
    snprintf(buf, len, "20%02d-%02d-%02d %02d:%02d:%02d",
             t.year, t.month, t.date, t.hour, t.min, t.sec);
}

void rtc_task(void *arg) {
    ds1307_time_t t = {0, 0, 12, 2, 15, 6, 26};
    ds1307_set(&t);

    char ts[32];
    while (1) {
        ds1307_timestamp(ts, sizeof(ts));
        printf("Time: %s\n", ts);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>
#include <stdio.h>

#define DS1307_ADDR 0x68
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

static uint8_t bcd2dec(uint8_t b) { return (b >> 4)*10 + (b&0xF); }
static uint8_t dec2bcd(uint8_t d) { return ((d/10)<<4) | (d%10); }

typedef struct { uint8_t sec,min,hour,day,date,month,year; } ds1307_t;

void ds1307_read(ds1307_t *t) {
    uint8_t reg = 0x00, buf[7];
    i2c_write_read(i2c_dev, DS1307_ADDR, &reg, 1, buf, 7);
    t->sec   = bcd2dec(buf[0] & 0x7F);
    t->min   = bcd2dec(buf[1] & 0x7F);
    t->hour  = bcd2dec(buf[2] & 0x3F);
    t->day   = bcd2dec(buf[3] & 0x07);
    t->date  = bcd2dec(buf[4] & 0x3F);
    t->month = bcd2dec(buf[5] & 0x1F);
    t->year  = bcd2dec(buf[6]);
}

void ds1307_set(const ds1307_t *t) {
    uint8_t buf[8];
    buf[0] = 0x00;  /* register address */
    buf[1] = dec2bcd(t->sec);
    buf[2] = dec2bcd(t->min);
    buf[3] = dec2bcd(t->hour);
    buf[4] = dec2bcd(t->day);
    buf[5] = dec2bcd(t->date);
    buf[6] = dec2bcd(t->month);
    buf[7] = dec2bcd(t->year);
    i2c_write(i2c_dev, buf, 8, DS1307_ADDR);
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    ds1307_t t;
    char ts[32];
    while (1) {
        ds1307_read(&t);
        snprintf(ts, sizeof(ts), "20%02d-%02d-%02d %02d:%02d:%02d",
                 t.year, t.month, t.date, t.hour, t.min, t.sec);
        printk("Time: %s\n", ts);
        k_msleep(1000);
    }
}
```

## Best Practices
1. Use RTClib on Arduino — handles BCD conversion and CH bit automatically
2. Always mask status bits: `buf[0] & 0x7F` for seconds (removes CH), `buf[2] & 0x3F` for hours
3. Write all 7 registers in a single I2C transaction (more atomic)
4. DS1307 loses time if VBAT battery is dead — always check `isrunning()`
5. For logging, format timestamp before opening SD file (adds ~0ms vs. the SD write time)

## Common Pitfalls
- ❌ Forgetting that CH bit (bit 7 of seconds register) = 1 halts the clock
- ❌ Reading 12h mode hours without checking the 12/24 mode bit
- ❌ Using raw BCD values in arithmetic (must convert with bcd_to_dec first)
- ❌ Not having a backup battery — time resets to 0 on power loss

## Related Skills
- `gps-nmea-uart.md` - GPS data logging with timestamp
- `microsd-spi.md` - SD card logging
