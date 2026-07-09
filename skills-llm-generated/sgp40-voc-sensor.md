---
name: SGP40 Air Quality (VOC) Sensor
description: This skill covers the SGP40 VOC index sensor via I2C. Includes raw measurement commands, humidity/temperature compensation, CRC verification, command timing, and VOC index algorithm. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# SGP40 Air Quality (VOC) Sensor

## Overview
The SGP40 is a digital gas sensor for volatile organic compounds (VOC). It outputs a raw SRAW signal (0–65535) that should be processed by Sensirion's VOC Index algorithm to produce a meaningful 0–500 scale index.

## Hardware Specs
- **Interface:** I2C
- **I2C Address:** 0x59 (fixed)
- **Supply Voltage:** 1.7–3.6V
- **Heater:** Built-in, mandatory for operation
- **Measurement Time:** 30ms after command

## Commands
```
0x2626  Measure Raw Signal (with humidity/temperature compensation)
0x260F  Measure Raw Signal (no compensation — default RH=50%, T=25°C)
0x280E  Execute Self-Test
0x3615  Turn Heater Off (low power mode)
0x0006  Soft Reset
```

## I2C Protocol
- **Command:** 2 bytes (MSB first)
- **Parameters:** 2 bytes data + 1 byte CRC (per pair)
- **Response:** 2 bytes data + 1 byte CRC (per pair)
- **CRC:** CRC-8, polynomial 0x31, init 0xFF, no final XOR

## CRC Calculation
```c
uint8_t sgp40_crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0xFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            crc = (crc & 0x80) ? (crc << 1) ^ 0x31 : (crc << 1);
        }
    }
    return crc;
}
```

## Humidity/Temperature Compensation Encoding
```
Relative Humidity: RH_ticks = RH% × 65535 / 100
Temperature:       T_ticks  = (T_C + 45) × 65535 / 175

Default (50% RH, 25°C):
  RH_ticks = 0x8000 = 32768
  T_ticks  = 0x6666 = 26214
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define SGP40_ADDR 0x59
/* Use I2C driver from i2c-communication-esp32-esp-idf.md */

/* CRC-8 for Sensirion protocol */
static uint8_t crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0xFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (crc << 1) ^ 0x31 : (crc << 1);
    }
    return crc;
}

/* Send 2-byte command + 2 optional parameter words (each with CRC) */
static esp_err_t sgp40_send_cmd(uint16_t cmd, const uint16_t *params, uint8_t param_count) {
    uint8_t buf[2 + param_count * 3];
    int pos = 0;
    buf[pos++] = (cmd >> 8) & 0xFF;
    buf[pos++] = cmd & 0xFF;
    for (uint8_t i = 0; i < param_count; i++) {
        uint8_t d[2] = { (params[i] >> 8) & 0xFF, params[i] & 0xFF };
        buf[pos++] = d[0];
        buf[pos++] = d[1];
        buf[pos++] = crc8(d, 2);
    }

    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (SGP40_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(hdl, buf, pos, true);
    i2c_master_stop(hdl);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);
    return ret;
}

/* Read N words (each 2 data + 1 CRC byte) */
static esp_err_t sgp40_read_words(uint16_t *words, uint8_t word_count) {
    uint8_t buf[word_count * 3];
    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (SGP40_ADDR << 1) | I2C_MASTER_READ, true);
    if (word_count * 3 > 1) i2c_master_read(hdl, buf, word_count * 3 - 1, I2C_MASTER_ACK);
    i2c_master_read_byte(hdl, buf + word_count * 3 - 1, I2C_MASTER_NACK);
    i2c_master_stop(hdl);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);
    if (ret != ESP_OK) return ret;

    for (uint8_t i = 0; i < word_count; i++) {
        words[i] = ((uint16_t)buf[i*3] << 8) | buf[i*3+1];
        /* Verify CRC */
        uint8_t d[2] = { buf[i*3], buf[i*3+1] };
        if (crc8(d, 2) != buf[i*3+2]) return ESP_ERR_INVALID_CRC;
    }
    return ESP_OK;
}

/* Read raw VOC without compensation */
int sgp40_read_raw(uint16_t *raw_voc) {
    if (sgp40_send_cmd(0x260F, NULL, 0) != ESP_OK) return -1;
    vTaskDelay(pdMS_TO_TICKS(30));  /* measurement time */
    return sgp40_read_words(raw_voc, 1) == ESP_OK ? 0 : -1;
}

/* Read with humidity/temperature compensation */
int sgp40_read_compensated(uint16_t *raw_voc, float rh_pct, float temp_c) {
    uint16_t params[2];
    params[0] = (uint16_t)(rh_pct   * 65535 / 100);
    params[1] = (uint16_t)((temp_c + 45) * 65535 / 175);
    if (sgp40_send_cmd(0x2626, params, 2) != ESP_OK) return -1;
    vTaskDelay(pdMS_TO_TICKS(30));
    return sgp40_read_words(raw_voc, 1) == ESP_OK ? 0 : -1;
}

void sgp40_task(void *arg) {
    uint16_t raw;
    while (1) {
        if (sgp40_read_raw(&raw) == 0) {
            printf("raw_voc=%u\n", raw);
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* Command timing validation */
void sgp40_timing_task(void *arg) {
    uint16_t raw;
    uint32_t interval_ms = 1000;
    TickType_t last = xTaskGetTickCount();
    while (1) {
        uint32_t elapsed = (xTaskGetTickCount() - last) * portTICK_PERIOD_MS;
        last = xTaskGetTickCount();
        if (sgp40_read_raw(&raw) == 0) {
            printf("measurement_interval=%lu, raw_voc=%u\n", elapsed, raw);
        }
        vTaskDelay(pdMS_TO_TICKS(interval_ms));
    }
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Wire.h>

#define SGP40_ADDR 0x59

uint8_t crc8(uint8_t *data, uint8_t len) {
    uint8_t crc = 0xFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (crc << 1) ^ 0x31 : (crc << 1);
    }
    return crc;
}

int sgp40_send(uint16_t cmd, uint16_t *params, uint8_t param_count) {
    Wire.beginTransmission(SGP40_ADDR);
    Wire.write((cmd >> 8) & 0xFF);
    Wire.write(cmd & 0xFF);
    for (uint8_t i = 0; i < param_count; i++) {
        uint8_t d[2] = { (params[i] >> 8) & 0xFF, params[i] & 0xFF };
        Wire.write(d[0]); Wire.write(d[1]);
        Wire.write(crc8(d, 2));
    }
    return Wire.endTransmission();
}

uint16_t sgp40_read_word(void) {
    Wire.requestFrom((uint8_t)SGP40_ADDR, (uint8_t)3);
    uint8_t hi = Wire.read(), lo = Wire.read(), chk = Wire.read();
    uint8_t d[2] = {hi, lo};
    if (crc8(d, 2) != chk) return 0xFFFF;  /* CRC error */
    return ((uint16_t)hi << 8) | lo;
}

/* Raw measurement (no compensation) */
uint16_t sgp40_read_raw(void) {
    sgp40_send(0x260F, NULL, 0);
    delay(30);  /* 30ms measurement */
    return sgp40_read_word();
}

/* Humidity-compensated measurement */
uint16_t sgp40_read_compensated(float rh, float temp_c) {
    uint16_t params[2];
    params[0] = (uint16_t)(rh * 65535 / 100);
    params[1] = (uint16_t)((temp_c + 45) * 65535 / 175);
    sgp40_send(0x2626, params, 2);
    delay(30);
    return sgp40_read_word();
}

void setup() {
    Wire.begin();
    Serial.begin(115200);
}

void loop() {
    uint16_t raw = sgp40_read_raw();
    Serial.print("raw_voc="); Serial.println(raw);
    delay(1000);
}
```

### Using Adafruit SGP40 Library
```cpp
#include <Adafruit_SGP40.h>
Adafruit_SGP40 sgp40;

void setup() {
    Wire.begin();
    Serial.begin(115200);
    if (!sgp40.begin()) { Serial.println("SGP40 not found"); while(1); }
}

void loop() {
    uint16_t raw = sgp40.measureRaw();
    int32_t voc_index = sgp40.measureVocIndex();  /* uses built-in VOC algorithm */
    Serial.print("raw_voc="); Serial.print(raw);
    Serial.print(", voc_index="); Serial.println(voc_index);
    delay(1000);
}
```

---

## nRF52840 + Zephyr Implementation

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

#define SGP40_ADDR 0x59
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

static uint8_t crc8(const uint8_t *d, uint8_t n) {
    uint8_t c = 0xFF;
    while (n--) { c ^= *d++; for (int b=0;b<8;b++) c=(c&0x80)?(c<<1)^0x31:c<<1; }
    return c;
}

static int sgp40_measure(uint16_t *raw) {
    /* Send 0x260F (no compensation) */
    uint8_t cmd[2] = { 0x26, 0x0F };
    if (i2c_write(i2c_dev, cmd, 2, SGP40_ADDR) != 0) return -1;
    k_msleep(30);

    uint8_t resp[3];
    if (i2c_read(i2c_dev, resp, 3, SGP40_ADDR) != 0) return -1;
    uint8_t d[2] = {resp[0], resp[1]};
    if (crc8(d, 2) != resp[2]) return -2;
    *raw = ((uint16_t)resp[0] << 8) | resp[1];
    return 0;
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    uint16_t raw;
    while (1) {
        if (sgp40_measure(&raw) == 0) printk("raw_voc=%u\n", raw);
        k_msleep(1000);
    }
}
```

---

## VOC Index Algorithm (Simplified Sensirion Algorithm)

The official Sensirion VOC Index algorithm is a C library (sensirion-embedded-common). For simple approximation:

```c
/* Simplified moving-mean VOC index (not official Sensirion algorithm) */
#define VOC_WINDOW 100
static uint32_t voc_buf[VOC_WINDOW];
static int voc_idx = 0;
static uint32_t voc_sum = 0;

int32_t compute_voc_index(uint16_t raw) {
    voc_sum -= voc_buf[voc_idx];
    voc_buf[voc_idx] = raw;
    voc_sum += raw;
    voc_idx = (voc_idx + 1) % VOC_WINDOW;

    uint32_t mean = voc_sum / VOC_WINDOW;
    /* Normalize: typical clean air ~25000, VOC index 100=normal */
    int32_t index = (int32_t)((float)raw / (float)mean * 100);
    return (index < 0) ? 0 : (index > 500) ? 500 : index;
}
```

Note: For production use, integrate the official Sensirion VOC Index algorithm from https://github.com/Sensirion/gas-index-algorithm

## Best Practices
1. Wait exactly 30ms after sending measurement command before reading
2. Always verify CRC on the 3-byte response (2 data + 1 CRC)
3. Run the sensor continuously (heater must stay on) for accurate measurements
4. For humidity compensation: obtain RH/temperature from an external sensor (DHT11, BME280)
5. Use VOC Index algorithm (Sensirion library) instead of raw values for application logic

## Common Pitfalls
- ❌ Not waiting 30ms after command — reads incomplete/corrupt response
- ❌ Ignoring CRC check — accepts corrupted readings
- ❌ Using raw values directly in UI (they drift with temperature and humidity)
- ❌ Calling measure too frequently (< 1 Hz) affects heater stabilization

## Related Skills
- `i2c-communication-esp32-esp-idf.md` - ESP32 I2C
- `pmsa003i-air-quality.md` - Combine with PM sensor for full AQI
