---
name: PMSA003I Particulate Matter Air Quality Sensor
description: This skill covers the PMSA003I PM sensor via I2C. Includes the 32-byte frame format, parsing PM1.0/PM2.5/PM10, checksum verification, and AQI computation patterns. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# PMSA003I Particulate Matter Air Quality Sensor

## Overview
The PMSA003I is a laser particle counter that measures PM1.0, PM2.5, and PM10 concentrations via I2C. It sends a 32-byte frame continuously; the host reads all 32 bytes at once.

## Hardware Specs
- **Interface:** I2C
- **I2C Address:** 0x12 (fixed)
- **Supply Voltage:** 5V (logic 3.3V compatible)
- **Update Rate:** ~1 Hz
- **Measurement range:** 0–500 μg/m³

## Frame Format (32 bytes)
```
Byte  0:   0x42  (magic byte 1)
Byte  1:   0x4D  (magic byte 2)
Byte  2-3: Frame length = 28 (big-endian)
Byte  4-5: PM1.0  (CF=1, standard) μg/m³
Byte  6-7: PM2.5  (CF=1, standard) μg/m³
Byte  8-9: PM10   (CF=1, standard) μg/m³
Byte 10-11: PM1.0  (atmospheric) μg/m³
Byte 12-13: PM2.5  (atmospheric) μg/m³
Byte 14-15: PM10   (atmospheric) μg/m³
Byte 16-17: Particles ≥0.3μm / 0.1L
Byte 18-19: Particles ≥0.5μm / 0.1L
Byte 20-21: Particles ≥1.0μm / 0.1L
Byte 22-23: Particles ≥2.5μm / 0.1L
Byte 24-25: Particles ≥5.0μm / 0.1L
Byte 26-27: Particles ≥10μm  / 0.1L
Byte 28:    Reserved
Byte 29:    Error/check byte
Byte 30-31: Checksum (sum of bytes 0–29)
```

## Checksum Verification
```c
bool pmsa003i_verify_checksum(const uint8_t *frame) {
    uint16_t sum = 0;
    for (int i = 0; i < 30; i++) sum += frame[i];
    uint16_t checksum = ((uint16_t)frame[30] << 8) | frame[31];
    return sum == checksum;
}
```

## AQI Calculation (US EPA PM2.5 breakpoints, simplified)
```c
int pm25_to_aqi(float pm25) {
    typedef struct { float c_lo, c_hi; int a_lo, a_hi; } bp_t;
    static const bp_t bp[] = {
        { 0.0,  12.0,   0,  50},
        {12.1,  35.4,  51, 100},
        {35.5,  55.4, 101, 150},
        {55.5, 150.4, 151, 200},
        {150.5, 250.4, 201, 300},
        {250.5, 350.4, 301, 400},
        {350.5, 500.0, 401, 500},
    };
    for (int i = 0; i < 7; i++) {
        if (pm25 <= bp[i].c_hi) {
            return (int)((bp[i].a_hi - bp[i].a_lo) / (bp[i].c_hi - bp[i].c_lo)
                         * (pm25 - bp[i].c_lo) + bp[i].a_lo);
        }
    }
    return 500;
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define PMSA003I_ADDR 0x12

typedef struct {
    uint16_t pm1_0;   /* CF=1, standard */
    uint16_t pm2_5;
    uint16_t pm10;
    uint16_t pm1_0_atm;
    uint16_t pm2_5_atm;
    uint16_t pm10_atm;
} pmsa003i_data_t;

/* Read 32-byte frame (no register write needed — sensor streams data) */
static bool pmsa003i_read_frame(uint8_t *frame) {
    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (PMSA003I_ADDR << 1) | I2C_MASTER_READ, true);
    i2c_master_read(hdl, frame, 31, I2C_MASTER_ACK);
    i2c_master_read_byte(hdl, frame + 31, I2C_MASTER_NACK);
    i2c_master_stop(hdl);
    bool ok = (i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(200)) == ESP_OK);
    i2c_cmd_link_delete(hdl);
    return ok;
}

static bool pmsa003i_parse(const uint8_t *frame, pmsa003i_data_t *data) {
    if (frame[0] != 0x42 || frame[1] != 0x4D) return false;

    uint16_t sum = 0;
    for (int i = 0; i < 30; i++) sum += frame[i];
    uint16_t chk = ((uint16_t)frame[30] << 8) | frame[31];
    if (sum != chk) return false;

    data->pm1_0    = ((uint16_t)frame[4]  << 8) | frame[5];
    data->pm2_5    = ((uint16_t)frame[6]  << 8) | frame[7];
    data->pm10     = ((uint16_t)frame[8]  << 8) | frame[9];
    data->pm1_0_atm = ((uint16_t)frame[10] << 8) | frame[11];
    data->pm2_5_atm = ((uint16_t)frame[12] << 8) | frame[13];
    data->pm10_atm  = ((uint16_t)frame[14] << 8) | frame[15];
    return true;
}

void pmsa003i_task(void *arg) {
    uint8_t frame[32];
    pmsa003i_data_t data;

    while (1) {
        if (pmsa003i_read_frame(frame) && pmsa003i_parse(frame, &data)) {
            printf("PM1.0=%u, PM2.5=%u, PM10=%u\n",
                   data.pm1_0, data.pm2_5, data.pm10);
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* Frame integrity check variant */
void pmsa003i_integrity_task(void *arg) {
    uint8_t frame[32];
    while (1) {
        bool ok = pmsa003i_read_frame(frame);
        bool chk_ok = ok && (frame[0] == 0x42 && frame[1] == 0x4D);
        if (chk_ok) {
            uint16_t sum = 0;
            for (int i = 0; i < 30; i++) sum += frame[i];
            uint16_t chk = ((uint16_t)frame[30] << 8) | frame[31];
            chk_ok = (sum == chk);
            uint16_t pm2_5 = ((uint16_t)frame[6] << 8) | frame[7];
            printf("checksum=%s, pm2_5=%u\n", chk_ok ? "ok" : "fail", pm2_5);
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* PM2.5 alarm with hysteresis */
void pmsa003i_alarm_task(void *arg) {
    uint8_t frame[32];
    pmsa003i_data_t data;
    uint16_t threshold = 35;   /* WHO guideline */
    uint32_t clear_ms  = 5000; /* stay below 5s to clear */
    bool alarm = false;
    uint32_t below_since = 0;

    while (1) {
        if (pmsa003i_read_frame(frame) && pmsa003i_parse(frame, &data)) {
            if (data.pm2_5 > threshold) {
                alarm = true; below_since = 0;
            } else if (alarm) {
                if (below_since == 0) below_since = xTaskGetTickCount() * portTICK_PERIOD_MS;
                if ((xTaskGetTickCount() * portTICK_PERIOD_MS - below_since) >= clear_ms) {
                    alarm = false; below_since = 0;
                }
            }
            printf("pm2_5=%u, alarm=%s\n", data.pm2_5, alarm ? "on" : "off");
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Wire.h>
#include <Adafruit_PM25AQI.h>

Adafruit_PM25AQI aqi;

void setup() {
    Wire.begin();
    Serial.begin(115200);

    if (!aqi.begin_I2C()) {
        Serial.println("PMSA003I not found");
        while (1);
    }
    Serial.println("PMSA003I ready");
}

void loop() {
    PM25_AQI_Data data;
    if (!aqi.read(&data)) {
        Serial.println("Read failed");
        delay(500);
        return;
    }
    Serial.print("PM1.0="); Serial.print(data.pm10_standard);
    Serial.print(", PM2.5="); Serial.print(data.pm25_standard);
    Serial.print(", PM10="); Serial.println(data.pm100_standard);
    delay(1000);
}
```

### Manual I2C (without library)
```cpp
#include <Wire.h>
#define PMSA003I_ADDR 0x12

bool readFrame(uint8_t *frame) {
    Wire.requestFrom((uint8_t)PMSA003I_ADDR, (uint8_t)32);
    if (Wire.available() < 32) return false;
    for (int i = 0; i < 32; i++) frame[i] = Wire.read();
    return true;
}

bool parseFrame(const uint8_t *frame, uint16_t *pm1, uint16_t *pm25, uint16_t *pm10) {
    if (frame[0] != 0x42 || frame[1] != 0x4D) return false;
    uint16_t sum = 0;
    for (int i = 0; i < 30; i++) sum += frame[i];
    uint16_t chk = ((uint16_t)frame[30] << 8) | frame[31];
    if (sum != chk) return false;
    *pm1  = ((uint16_t)frame[4] << 8) | frame[5];
    *pm25 = ((uint16_t)frame[6] << 8) | frame[7];
    *pm10 = ((uint16_t)frame[8] << 8) | frame[9];
    return true;
}

uint8_t frame[32];
void loop() {
    if (readFrame(frame)) {
        uint16_t pm1, pm25, pm10;
        bool ok = parseFrame(frame, &pm1, &pm25, &pm10);
        Serial.print("checksum="); Serial.print(ok ? "ok" : "fail");
        if (ok) {
            Serial.print(", pm2_5="); Serial.print(pm25);
        }
        Serial.println();
    }
    delay(1000);
}
```

---

## nRF52840 + Zephyr Implementation

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

#define PMSA003I_ADDR 0x12
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

static bool pmsa_read(uint16_t *pm1, uint16_t *pm25, uint16_t *pm10) {
    uint8_t frame[32];
    if (i2c_read(i2c_dev, frame, 32, PMSA003I_ADDR) != 0) return false;
    if (frame[0] != 0x42 || frame[1] != 0x4D) return false;

    uint16_t sum = 0;
    for (int i = 0; i < 30; i++) sum += frame[i];
    if (sum != (((uint16_t)frame[30] << 8) | frame[31])) return false;

    *pm1  = ((uint16_t)frame[4] << 8) | frame[5];
    *pm25 = ((uint16_t)frame[6] << 8) | frame[7];
    *pm10 = ((uint16_t)frame[8] << 8) | frame[9];
    return true;
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    uint16_t pm1, pm25, pm10;
    while (1) {
        if (pmsa_read(&pm1, &pm25, &pm10)) {
            printk("PM1.0=%u, PM2.5=%u, PM10=%u\n", pm1, pm25, pm10);
        }
        k_msleep(1000);
    }
}
```

## Best Practices
1. Always verify the magic bytes (0x42, 0x4D) and checksum before using the data
2. Read all 32 bytes in a single I2C transaction — the sensor doesn't support partial reads
3. The sensor warms up for ~30 seconds after power-on; discard early readings
4. Use CF=1 (standard) values (bytes 4–9) for display; atmospheric values for AQI calculation
5. PM2.5 > 35 μg/m³ is "Unhealthy for Sensitive Groups" (US EPA); > 150 is "Unhealthy"

## Common Pitfalls
- ❌ Writing to sensor (it streams, no register write needed for I2C reads)
- ❌ Partial reads (Wire.requestFrom must request exactly 32 bytes)
- ❌ Not verifying checksum — accepts frame from mid-stream alignment
- ❌ Using atmospheric PM values when standard is required or vice versa

## Related Skills
- `sgp40-voc-sensor.md` - VOC sensor for combined AQI
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C
