---
name: LTR390 UV and Ambient Light Sensor
description: This skill covers the LTR390 UV/ALS (ambient light sensor) via I2C. Includes ALS/UV mode switching, gain and resolution configuration, data ready polling, and UV index calculation. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# LTR390 UV and Ambient Light Sensor

## Overview
The LTR390 is a combined UV + ambient light sensor (I2C). It has two operating modes: ALS (visible light) and UVS (UV light). Only one mode is active at a time; you must switch modes to read both values.

## Hardware Specs
- **Interface:** I2C
- **I2C Address:** 0x53 (fixed)
- **UV Range:** 280–430 nm
- **ALS Range:** 400–700 nm
- **Measurement resolution:** 13–20 bit (configurable)

## Register Map
```
0x00 MAIN_CTRL   - mode, enable/disable
0x04 MEAS_RATE   - measurement rate and resolution
0x05 GAIN        - gain setting
0x06 PART_ID     - should be 0xB2
0x07 MAIN_STATUS - data ready, power-on, interrupt status
0x0D ALS_DATA_0  - ALS data low byte  (20-bit: [0D][0E][0F])
0x0E ALS_DATA_1  - ALS data mid byte
0x0F ALS_DATA_2  - ALS data high byte
0x10 UVS_DATA_0  - UVS data low byte  (20-bit: [10][11][12])
0x11 UVS_DATA_1  - UVS data mid byte
0x12 UVS_DATA_2  - UVS data high byte
0x19 INT_CFG     - interrupt enable and LS/UVS select
0x1A INT_PST     - interrupt persistence
```

## MAIN_CTRL Register (0x00)
```
Bit 3: UVS_EN  - 1=UV mode active, 0=ALS mode active
Bit 1: ALS_EN  - 1=sensor enabled, 0=standby
```

## MEAS_RATE Register (0x04)
```
Bits [5:4]: Resolution
  00=20-bit (400ms), 01=19-bit (200ms), 10=18-bit (100ms), 11=17-bit (50ms)
  100=16-bit (25ms), 101=13-bit (12.5ms)
Bits [2:0]: Measurement rate
  000=25ms, 001=50ms, 010=100ms (default), 011=200ms, 100=500ms, 101=1000ms, 110=2000ms
```

## GAIN Register (0x05)
```
Bits [2:0]:
  000=1x, 001=3x, 010=6x, 011=9x (default), 100=18x
```

## MAIN_STATUS Register (0x07)
```
Bit 3: DATA_STATUS - 1=new data ready, cleared on reading data registers
Bit 2: INT_STATUS  - interrupt triggered
Bit 1: POWER_ON    - power-on event
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define LTR390_ADDR 0x53
/* Use i2c_read_bytes / i2c_write_bytes from i2c-communication-esp32-esp-idf.md */

void ltr390_write(uint8_t reg, uint8_t val) {
    i2c_write_bytes(LTR390_ADDR, reg, &val, 1);
}

uint8_t ltr390_read(uint8_t reg) {
    uint8_t val;
    i2c_read_bytes(LTR390_ADDR, reg, &val, 1);
    return val;
}

uint32_t ltr390_read24(uint8_t reg) {
    uint8_t buf[3];
    i2c_read_bytes(LTR390_ADDR, reg, buf, 3);
    return (uint32_t)buf[2] << 16 | (uint32_t)buf[1] << 8 | buf[0];
}

void ltr390_init(void) {
    /* Enable ALS mode (bit1=1 enable, bit3=0 ALS mode) */
    ltr390_write(0x00, 0x02);
    /* 18-bit resolution, 100ms rate */
    ltr390_write(0x04, 0x22);
    /* Gain 3x */
    ltr390_write(0x05, 0x01);
    vTaskDelay(pdMS_TO_TICKS(100));
}

/* Switch to ALS mode, wait for data, read */
uint32_t ltr390_read_als(void) {
    ltr390_write(0x00, 0x02);   /* ALS mode, enabled */
    vTaskDelay(pdMS_TO_TICKS(120));
    while (!(ltr390_read(0x07) & 0x08)) vTaskDelay(pdMS_TO_TICKS(10));
    return ltr390_read24(0x0D);
}

/* Switch to UV mode, wait for data, read */
uint32_t ltr390_read_uvs(void) {
    ltr390_write(0x00, 0x0A);   /* UV mode (bits: UVS_EN=1, ALS_EN=1) */
    vTaskDelay(pdMS_TO_TICKS(120));
    while (!(ltr390_read(0x07) & 0x08)) vTaskDelay(pdMS_TO_TICKS(10));
    return ltr390_read24(0x10);
}

void ltr390_task_single(void *arg) {
    ltr390_init();
    while (1) {
        uint32_t uv = ltr390_read_uvs();
        uint32_t al = ltr390_read_als();
        printf("UV: %lu, AL: %lu\n", uv, al);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

void ltr390_task_switching(void *arg) {
    ltr390_init();
    bool als_mode = true;
    while (1) {
        if (als_mode) {
            uint32_t al = ltr390_read_als();
            printf("mode=ALS, value=%lu\n", al);
        } else {
            uint32_t uv = ltr390_read_uvs();
            printf("mode=UV, value=%lu\n", uv);
        }
        als_mode = !als_mode;
        vTaskDelay(pdMS_TO_TICKS(3000));
    }
}

/* UV Alert: alert when UV exceeds threshold, clear after sustained low */
void ltr390_alert_task(void *arg) {
    ltr390_init();
    uint32_t uv_threshold  = 1000;  /* threshold count */
    uint32_t clear_time_ms = 5000;  /* must be below 5s to clear */
    bool alert = false;
    uint32_t below_since = 0;

    while (1) {
        uint32_t uv = ltr390_read_uvs();
        if (uv > uv_threshold) {
            alert = true; below_since = 0;
            /* TODO: blink LED pin */
        } else if (alert) {
            if (below_since == 0) below_since = xTaskGetTickCount() * portTICK_PERIOD_MS;
            uint32_t elapsed = xTaskGetTickCount() * portTICK_PERIOD_MS - below_since;
            if (elapsed >= clear_time_ms) { alert = false; below_since = 0; }
        }
        printf("uv=%lu, alert=%s\n", uv, alert ? "on" : "off");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Wire.h>
#include <Adafruit_LTR390.h>

Adafruit_LTR390 ltr390;

void setup() {
    Wire.begin();
    Serial.begin(115200);

    if (!ltr390.begin()) {
        Serial.println("LTR390 not found");
        while (1);
    }
    ltr390.setMode(LTR390_MODE_ALS);
    ltr390.setGain(LTR390_GAIN_3);
    ltr390.setResolution(LTR390_RESOLUTION_18BIT);
}

/* UV_Light_Sensor_Single_Mode_Reading */
void loop_single() {
    ltr390.setMode(LTR390_MODE_ALS);
    delay(120);
    if (!ltr390.newDataAvailable()) return;
    uint32_t als = ltr390.readALS();

    ltr390.setMode(LTR390_MODE_UVS);
    delay(120);
    if (!ltr390.newDataAvailable()) return;
    uint32_t uvs = ltr390.readUVS();

    Serial.print("UV: "); Serial.print(uvs);
    Serial.print(", AL: "); Serial.println(als);
    delay(2000);
}

/* UV_Light_Sensor_Mode_Switching_Readout */
void loop_switching() {
    static bool als_mode = true;
    static unsigned long last_switch = 0;

    if (millis() - last_switch >= 3000) {
        als_mode = !als_mode;
        last_switch = millis();
        ltr390.setMode(als_mode ? LTR390_MODE_ALS : LTR390_MODE_UVS);
        delay(120);
    }

    if (als_mode && ltr390.newDataAvailable()) {
        Serial.print("mode=ALS, value="); Serial.println(ltr390.readALS());
    } else if (!als_mode && ltr390.newDataAvailable()) {
        Serial.print("mode=UV, value="); Serial.println(ltr390.readUVS());
    }
}

void loop() { loop_switching(); }
```

### Manual I2C (without Adafruit library)
```cpp
#include <Wire.h>
#define LTR390_ADDR 0x53

uint8_t ltr_read(uint8_t reg) {
    Wire.beginTransmission(LTR390_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)LTR390_ADDR, (uint8_t)1);
    return Wire.read();
}

uint32_t ltr_read24(uint8_t reg) {
    Wire.beginTransmission(LTR390_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)LTR390_ADDR, (uint8_t)3);
    uint32_t v = Wire.read();
    v |= (uint32_t)Wire.read() << 8;
    v |= (uint32_t)Wire.read() << 16;
    return v;
}

void ltr_write(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(LTR390_ADDR);
    Wire.write(reg); Wire.write(val);
    Wire.endTransmission();
}
```

---

## nRF52840 + Zephyr Implementation

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

#define LTR390_ADDR 0x53
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

static void ltr_write(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg, val };
    i2c_write(i2c_dev, buf, 2, LTR390_ADDR);
}

static uint8_t ltr_read(uint8_t reg) {
    uint8_t val;
    i2c_write_read(i2c_dev, LTR390_ADDR, &reg, 1, &val, 1);
    return val;
}

static uint32_t ltr_read24(uint8_t reg) {
    uint8_t buf[3];
    i2c_write_read(i2c_dev, LTR390_ADDR, &reg, 1, buf, 3);
    return (uint32_t)buf[2] << 16 | (uint32_t)buf[1] << 8 | buf[0];
}

void ltr390_init(void) {
    ltr_write(0x00, 0x02);  /* ALS mode, enabled */
    ltr_write(0x04, 0x22);  /* 18-bit, 100ms */
    ltr_write(0x05, 0x01);  /* 3x gain */
    k_msleep(100);
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    ltr390_init();

    while (1) {
        ltr_write(0x00, 0x0A);   /* UV mode */
        k_msleep(120);
        while (!(ltr_read(0x07) & 0x08)) k_msleep(10);
        uint32_t uv = ltr_read24(0x10);

        ltr_write(0x00, 0x02);   /* ALS mode */
        k_msleep(120);
        while (!(ltr_read(0x07) & 0x08)) k_msleep(10);
        uint32_t al = ltr_read24(0x0D);

        printk("UV: %u, AL: %u\n", uv, al);
        k_msleep(2000);
    }
}
```

## Best Practices
1. Allow 100–200ms after mode switch before reading — sensor needs time to convert
2. Check DATA_STATUS bit (bit 3 of 0x07) before reading to get fresh data
3. ALS and UV cannot be read simultaneously — alternate with sufficient settling time
4. UV index computation: `UV_index = UVS_raw × 0.0006` (approximate; depends on gain/resolution)
5. Use Adafruit library on Arduino — it handles data ready polling internally

## Common Pitfalls
- ❌ Reading UV data while in ALS mode (reads ALS data instead)
- ❌ Not waiting for data ready — reads stale value
- ❌ Reading 3 separate bytes with 3 separate I2C transactions — use burst read
- ❌ Forgetting to enable the sensor (bit 1 of MAIN_CTRL must be 1)

## Related Skills
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C
- `i2c-communication-esp32-esp-idf.md` - ESP32 I2C
