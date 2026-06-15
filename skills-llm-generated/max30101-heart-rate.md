---
name: MAX30101 + MAX32664 Pulse Oximeter and Heart Rate Sensor
description: This skill covers the Adafruit MAX30101/MAX32664 biometric sensor combo. The MAX32664 biometric hub processes raw optical data and exposes heart rate and SpO2 over I2C. Includes initialization, FIFO reading, and abnormal-value detection. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# MAX30101 + MAX32664 Pulse Oximeter and Heart Rate Sensor

## Overview
The **MAX30101** is the optical frontend (LED driver + photodetector). The **MAX32664** is a biometric sensor hub that runs the HR/SpO2 algorithm onboard and outputs computed values over I2C. The host only needs to interface with the MAX32664.

## Hardware Specs
- **Interface:** I2C (MAX32664 at address 0x55)
- **Additional Pins:**
  - MFIO (Multi-Function I/O): must be driven HIGH during normal operation
  - RESET: active-low reset (boot into application mode = hold HIGH)
- **Supply:** 1.8V or 3.3V (check breakout)
- **Output rate:** default 100ms (~10 Hz)

## MAX32664 Command Protocol
```
Command byte 1: Family byte
Command byte 2: Index byte
Optional: write data bytes
Read: after command, wait, then read from device
```

## Key Commands (Family / Index)
```
0x01 / 0x01  Read Hub Status (is algorithm running?)
0x10 / 0x00  Set Output Mode (0x01=algorithm, 0x02=sensor+algorithm)
0x10 / 0x01  Set Threshold (FIFO almost full)
0x12 / 0x00  Read Number of Samples in FIFO
0x12 / 0x01  Read FIFO Data
0x50 / 0x07  Set Algorithm Operating Mode
0x52 / 0x02  Set Algorithm Operating Mode — Continuous SpO2/HR
0x44 / 0x03  Set Sensor Enable (enable MAX30101)
```

## FIFO Data Format (Algorithm Mode 2, 6 bytes per sample)
```
Byte 0: HR MSB
Byte 1: HR LSB   (16-bit, value in bpm × 10, so divide by 10)
Byte 2: SpO2 MSB
Byte 3: SpO2 LSB (16-bit, value in % × 10)
Byte 4: Confidence (0–100%)
Byte 5: Status (0=OK, 1=searching, 2=tracking)
```

---

## ATMega2560 + Arduino Implementation (Adafruit Library)

```cpp
#include <Wire.h>
#include "SparkFun_Bio_Sensor_Hub_Library.h"

#define RESET_PIN 4
#define MFIO_PIN  5

SparkFun_Bio_Sensor_Hub bioHub(RESET_PIN, MFIO_PIN);
bioData body;

void setup() {
    Wire.begin();
    Serial.begin(115200);

    int result = bioHub.begin();
    if (result == 0) {
        Serial.println("Sensor started");
    } else {
        Serial.print("Sensor error: "); Serial.println(result);
        while (1);
    }

    /* Configure for SpO2 + heart rate algorithm */
    bioHub.configBpm(MODE_TWO);  /* MODE_ONE=HR only, MODE_TWO=HR+SpO2 */
    delay(4000);  /* Allow sensor to stabilize */
    Serial.println("Ready");
}

void loop() {
    body = bioHub.readBpm();
    int hr   = body.heartRate;
    int spo2 = body.oxygen;
    int conf = body.confidence;
    int status = body.status;  /* 0=no finger, 1=searching, 2=tracking */

    Serial.print("HR="); Serial.print(hr);
    Serial.print(", SpO2="); Serial.print(spo2);
    Serial.print(", confidence="); Serial.print(conf);
    Serial.print(", status="); Serial.println(status);
    delay(250);
}
```

### Wearable Health Device (Abnormal Value Detection)
```cpp
#include <Wire.h>
#include "SparkFun_Bio_Sensor_Hub_Library.h"

#define RESET_PIN   4
#define MFIO_PIN    5
#define BUZZER_PIN  8
#define WINDOW_SIZE 10
#define LOW_HR_THRESHOLD 50   /* alert if HR < 50 bpm */
#define ALERT_PERSIST_S  5    /* alert if low for 5 consecutive seconds */

SparkFun_Bio_Sensor_Hub bioHub(RESET_PIN, MFIO_PIN);
bioData body;

int hr_window[WINDOW_SIZE];
int win_idx = 0;
int low_count = 0;
bool alert = false;

void setup() {
    Serial.begin(115200);
    Wire.begin();
    pinMode(BUZZER_PIN, OUTPUT);
    bioHub.begin();
    bioHub.configBpm(MODE_TWO);
    delay(4000);
}

void loop() {
    body = bioHub.readBpm();
    int hr = body.heartRate;

    /* Update rolling window */
    hr_window[win_idx] = hr;
    win_idx = (win_idx + 1) % WINDOW_SIZE;

    /* Check if current HR is abnormal */
    if (body.confidence > 70 && hr < LOW_HR_THRESHOLD) {
        low_count++;
    } else {
        low_count = 0;
    }

    if (low_count >= ALERT_PERSIST_S) {
        alert = true;
        digitalWrite(BUZZER_PIN, HIGH);
    } else {
        alert = false;
        digitalWrite(BUZZER_PIN, LOW);
    }

    Serial.print("heart_rate="); Serial.print(hr);
    Serial.print(", alert="); Serial.println(alert ? "on" : "off");
    delay(1000);
}
```

### Raw IR/Red LED Values (MAX30101 sensor data mode)
```cpp
/* Use MODE_ONE raw sensor data */
#include "SparkFun_Bio_Sensor_Hub_Library.h"

bioData body;

void setup() {
    Wire.begin();
    Serial.begin(115200);
    bioHub.begin();
    bioHub.configSensorBpm(MODE_ONE);  /* sensor + algorithm */
    delay(4000);
}

void loop() {
    body = bioHub.readSensorBpm();
    Serial.print("IR="); Serial.print(body.irLed);
    Serial.print(", Red="); Serial.println(body.redLed);
    delay(100);
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include <stdio.h>

#define MAX32664_ADDR  0x55
#define RESET_PIN      GPIO_NUM_4
#define MFIO_PIN       GPIO_NUM_5

/* i2c_read_bytes / i2c_write_bytes from i2c-communication-esp32-esp-idf.md */

static void max32664_reset(void) {
    gpio_set_direction(RESET_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MFIO_PIN,  GPIO_MODE_OUTPUT);
    gpio_set_level(MFIO_PIN, 1);   /* MFIO HIGH = application mode */
    gpio_set_level(RESET_PIN, 0);  /* Assert reset */
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(RESET_PIN, 1);  /* Release reset */
    vTaskDelay(pdMS_TO_TICKS(1000)); /* Boot time ~1s */
}

/* Write command + data bytes */
static esp_err_t max32664_write(uint8_t family, uint8_t index,
                                 const uint8_t *data, size_t data_len) {
    uint8_t buf[64];
    buf[0] = family;
    buf[1] = index;
    if (data && data_len) memcpy(buf + 2, data, data_len);

    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (MAX32664_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(hdl, buf, 2 + data_len, true);
    i2c_master_stop(hdl);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);
    return ret;
}

/* Read N bytes response (first byte is status) */
static esp_err_t max32664_read(uint8_t family, uint8_t index,
                                uint8_t *resp, size_t len) {
    max32664_write(family, index, NULL, 0);
    vTaskDelay(pdMS_TO_TICKS(50));  /* CMD_DELAY */

    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (MAX32664_ADDR << 1) | I2C_MASTER_READ, true);
    if (len > 1) i2c_master_read(hdl, resp, len - 1, I2C_MASTER_ACK);
    i2c_master_read_byte(hdl, resp + len - 1, I2C_MASTER_NACK);
    i2c_master_stop(hdl);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);
    return ret;
}

static void max32664_init(void) {
    max32664_reset();

    /* Set output mode: algorithm data (0x01) */
    uint8_t mode = 0x01;
    max32664_write(0x10, 0x00, &mode, 1);
    vTaskDelay(pdMS_TO_TICKS(50));

    /* Enable MAX30101 sensor */
    uint8_t en = 0x01;
    max32664_write(0x44, 0x03, &en, 1);
    vTaskDelay(pdMS_TO_TICKS(50));

    /* Set algorithm to SpO2+HR (0x02 = MODE_TWO) */
    uint8_t alg_mode = 0x02;
    max32664_write(0x50, 0x07, &alg_mode, 1);
    vTaskDelay(pdMS_TO_TICKS(4000));  /* algorithm warm-up */
}

void max32664_task(void *arg) {
    max32664_init();

    while (1) {
        /* Read sample count */
        uint8_t count_resp[2];
        max32664_read(0x12, 0x00, count_resp, 2);
        uint8_t sample_count = count_resp[1];

        if (sample_count > 0) {
            /* Read FIFO: 6 bytes per sample */
            uint8_t fifo_data[7];  /* status + 6 data bytes */
            max32664_read(0x12, 0x01, fifo_data, 7);

            int16_t hr   = ((uint16_t)fifo_data[1] << 8) | fifo_data[2];
            int16_t spo2 = ((uint16_t)fifo_data[3] << 8) | fifo_data[4];
            printf("IR=%d, Red=%d (HR=%.1f bpm, SpO2=%.1f%%)\n",
                   0, 0, hr / 10.0f, spo2 / 10.0f);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* Same I2C command pattern as ESP32 version, adapted for Zephyr */
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/gpio.h>

#define MAX32664_ADDR 0x55
static const struct device *i2c_dev  = DEVICE_DT_GET(DT_NODELABEL(i2c0));
static const struct gpio_dt_spec mfio  = GPIO_DT_SPEC_GET(DT_ALIAS(mfio),  gpios);
static const struct gpio_dt_spec reset = GPIO_DT_SPEC_GET(DT_ALIAS(reset), gpios);

static void max32664_reset(void) {
    gpio_pin_configure_dt(&mfio,  GPIO_OUTPUT_HIGH);
    gpio_pin_configure_dt(&reset, GPIO_OUTPUT_LOW);
    k_msleep(10);
    gpio_pin_set_dt(&reset, 1);
    k_msleep(1000);
}

static int max32664_write(uint8_t family, uint8_t index,
                           const uint8_t *data, size_t len) {
    uint8_t buf[64];
    buf[0] = family; buf[1] = index;
    if (data && len) memcpy(buf + 2, data, len);
    return i2c_write(i2c_dev, buf, 2 + len, MAX32664_ADDR);
}

static int max32664_read(uint8_t family, uint8_t index,
                          uint8_t *resp, size_t len) {
    max32664_write(family, index, NULL, 0);
    k_msleep(50);
    return i2c_read(i2c_dev, resp, len, MAX32664_ADDR);
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    max32664_reset();

    uint8_t m;
    m = 0x01; max32664_write(0x10, 0x00, &m, 1); k_msleep(50);
    m = 0x01; max32664_write(0x44, 0x03, &m, 1); k_msleep(50);
    m = 0x02; max32664_write(0x50, 0x07, &m, 1); k_msleep(4000);

    while (1) {
        uint8_t cnt[2], fifo[7];
        max32664_read(0x12, 0x00, cnt, 2);
        if (cnt[1] > 0) {
            max32664_read(0x12, 0x01, fifo, 7);
            int hr   = ((uint16_t)fifo[1] << 8) | fifo[2];
            int spo2 = ((uint16_t)fifo[3] << 8) | fifo[4];
            printk("heart_rate=%d, spo2=%d\n", hr/10, spo2/10);
        }
        k_msleep(100);
    }
}
```

## Best Practices
1. Hold MFIO HIGH before releasing RESET to boot into application mode
2. Wait 4 seconds after enabling the algorithm for warm-up before reading
3. Check `confidence` field — values < 70% are unreliable
4. Use SparkFun Bio Sensor Hub library on Arduino for simplified access
5. Read FIFO only when sample count > 0 to avoid stale data reads

## Common Pitfalls
- ❌ Not asserting MFIO before reset release (boots into bootloader mode)
- ❌ Not waiting for algorithm warm-up (reads 0 or garbage values)
- ❌ Dividing HR by 10 missing: raw value is in 0.1 bpm units
- ❌ Reading without checking confidence — displays invalid HR

## Related Skills
- `i2c-communication-esp32-esp-idf.md` - ESP32 I2C
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C
