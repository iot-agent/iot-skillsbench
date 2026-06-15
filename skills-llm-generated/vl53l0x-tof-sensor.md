---
name: VL53L0X Time-of-Flight Distance Sensor
description: This skill covers the VL53L0X ToF distance sensor via I2C. Includes initialization, single-shot mode, continuous ranging, timing budget configuration, range status interpretation, and gesture detection. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# VL53L0X Time-of-Flight Distance Sensor

## Overview
The VL53L0X is an I2C ToF laser-ranging sensor that measures distances from 50–2000 mm (typical). It uses VCSEL (940nm) and a SPAD array. The device requires a complex multi-step initialization sequence that is best handled via a library.

## Hardware Specs
- **Interface:** I2C
- **Default I2C Address:** 0x29 (can be changed via XSHUT + I2C command)
- **Range:** 50–2000 mm (up to 8000 mm in long-range mode)
- **Timing Budget:** 20ms–2000ms (trade-off: accuracy vs. speed)
- **Modes:** Continuous (auto-repeat), Single-shot (on-demand), Timed

## Key Registers / Concepts
```
SYSRANGE_START (0x00):       0x01 = start single, 0x03 = back-to-back
RESULT_RANGE_STATUS (0x14):  bit[3:0] = range error code, bit[4] = data ready
RESULT_INTERRUPT_STATUS (0x13): bit[0] = new data available
RESULT_RANGE_MM (0x1E):      16-bit range in mm (big-endian, 2 bytes)
SYSTEM_RANGE_CONFIG (0x09):  continuous timing
FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI (0x71): timing budget register
MSRC_CONFIG_TIMEOUT_MACROP (0x46)
```

## Range Status Codes
```
0  = No error (RangeStatus_None — valid range)
1  = VCSEL continuity test failure
2  = VCSEL watchdog test failure
3  = No VHV value found
4  = MSRC no target
5  = SNR check failure
6  = Range phase check failure
7  = Sigma threshold check failure
8  = TCC failure
9  = Phase consistency
10 = Min clip
11 = Range complete — data valid
12 = Algo underflow
13 = Algo overflow
14 = Range ignore threshold
```
Note: Status 0 means "no error" = valid reading.

---

## ESP32 + ESP-IDF Implementation

Use the `vl53l0x` component (port of ST's VL53L0X API, or use a community driver). For direct I2C implementation:

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define VL53L0X_ADDR 0x29
#define I2C_PORT     I2C_NUM_0
#define I2C_SDA      21
#define I2C_SCL      22

/* i2c_write_bytes and i2c_read_bytes from i2c-communication-esp32-esp-idf.md */

/* Read a byte from sensor */
uint8_t vl53_read_byte(uint8_t reg) {
    uint8_t val = 0;
    i2c_read_bytes(VL53L0X_ADDR, reg, &val, 1);
    return val;
}

/* Write a byte to sensor */
void vl53_write_byte(uint8_t reg, uint8_t val) {
    i2c_write_bytes(VL53L0X_ADDR, reg, &val, 1);
}

/* Read 16-bit value */
uint16_t vl53_read_word(uint8_t reg) {
    uint8_t buf[2];
    i2c_read_bytes(VL53L0X_ADDR, reg, buf, 2);
    return ((uint16_t)buf[0] << 8) | buf[1];
}

/* Minimal init + single-shot read (assumes device is in default state) */
uint16_t vl53_read_range_mm(void) {
    /* Trigger single measurement */
    vl53_write_byte(0x80, 0x01);
    vl53_write_byte(0xFF, 0x01);
    vl53_write_byte(0x00, 0x00);
    vl53_write_byte(0x91, 0x3C);  /* stop variable
    vl53_write_byte(0x00, 0x01);
    vl53_write_byte(0xFF, 0x00);
    vl53_write_byte(0x80, 0x00);
    vl53_write_byte(0x00, 0x01);  /* SYSRANGE_START single-shot */

    /* Wait for data ready */
    uint32_t timeout = 500;
    while ((vl53_read_byte(0x13) & 0x07) == 0 && timeout--) {
        vTaskDelay(1);
    }

    /* Read range */
    uint16_t range = vl53_read_word(0x1E);

    /* Clear interrupt */
    vl53_write_byte(0x0B, 0x01);

    return range;
}

/* Preferred: Use Adafruit VL53L0X library (ESP32 Arduino) or pololu/vl53l0x */
```

### ESP32 + Arduino framework (recommended for VL53L0X)
```cpp
/* In Arduino mode on ESP32, use Adafruit VL53L0X library */
#include <Wire.h>
#include "Adafruit_VL53L0X.h"

Adafruit_VL53L0X lox;

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);

    if (!lox.begin()) {
        Serial.println("VL53L0X init failed");
        while (1);
    }
    /* Set timing budget: 200ms = higher accuracy */
    lox.setMeasurementTimingBudgetMicroSeconds(200000);
}

void loop() {
    VL53L0X_RangingMeasurementData_t measure;
    lox.rangingTest(&measure, false);

    if (measure.RangeStatus != 4) {  // 4 = out of range
        Serial.print("Distance: ");
        Serial.print(measure.RangeMilliMeter);
        Serial.println(" mm");
    } else {
        Serial.println("Out of range");
    }
    delay(100);
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Wire.h>
#include "Adafruit_VL53L0X.h"

Adafruit_VL53L0X lox;

void setup() {
    Wire.begin();
    Wire.setClock(400000);
    Serial.begin(115200);

    if (!lox.begin()) {
        Serial.println("VL53L0X init failed. Check wiring and I2C address.");
        while (1) delay(10);
    }
    Serial.println("VL53L0X ready");
}

void loop() {
    VL53L0X_RangingMeasurementData_t measure;
    lox.rangingTest(&measure, false);

    uint8_t status = measure.RangeStatus;
    uint16_t dist  = measure.RangeMilliMeter;

    if (status == 0) {
        Serial.print("Distance: ");
        Serial.print(dist);
        Serial.println(" mm");
    } else {
        Serial.print("Range error, status=");
        Serial.println(status);
    }
    delay(1000);
}
```

### Continuous Ranging Mode (Arduino)
```cpp
void setup() {
    Wire.begin();
    lox.begin();
    lox.startRangeContinuous(100);  // 100 ms interval
}

void loop() {
    if (lox.isRangeComplete()) {
        uint16_t dist = lox.readRangeResult();
        Serial.println(dist);
    }
}
```

### Single-Shot Mode (Arduino)
```cpp
// rangingTest() is single-shot by default
// For explicit single-shot:
VL53L0X_RangingMeasurementData_t measure;
lox.rangingTest(&measure, false);
uint16_t dist = measure.RangeMilliMeter;
```

### Timing Budget and Threshold (Arduino)
```cpp
// Set 200ms timing budget (more accurate)
lox.setMeasurementTimingBudgetMicroSeconds(200000);

// Threshold alert: if distance < 100mm
void loop() {
    VL53L0X_RangingMeasurementData_t m;
    lox.rangingTest(&m, false);
    if (m.RangeStatus == 0 && m.RangeMilliMeter < 100) {
        Serial.println("Distance < 100 mm");
    }
    delay(100);
}
```

### Advanced: Status + Distance + Timing Budget
```cpp
// Read range status and distance
VL53L0X_RangingMeasurementData_t m;
lox.rangingTest(&m, false);
Serial.print("status="); Serial.print(m.RangeStatus);
Serial.print(", distance="); Serial.print(m.RangeMilliMeter);
Serial.println(" mm");
```

---

## nRF52840 + Zephyr Implementation

Zephyr has a VL53L0X driver (`CONFIG_VL53L0X`) that uses the sensor API.

### prj.conf
```ini
CONFIG_I2C=y
CONFIG_SENSOR=y
CONFIG_VL53L0X=y
```

### board.overlay
```dts
&i2c0 {
    status = "okay";

    vl53l0x: vl53l0x@29 {
        compatible = "st,vl53l0x";
        reg = <0x29>;
        label = "VL53L0X";
        xshut-gpios = <&gpio0 4 GPIO_ACTIVE_LOW>;  /* optional XSHUT */
    };
};
```

### C Code (Zephyr Sensor API)
```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/sensor.h>

static const struct device *vl53l0x_dev = DEVICE_DT_GET_ANY(st_vl53l0x);

int main(void) {
    if (!device_is_ready(vl53l0x_dev)) {
        printk("VL53L0X not ready\n");
        return -1;
    }

    while (1) {
        struct sensor_value distance;

        int ret = sensor_sample_fetch(vl53l0x_dev);
        if (ret == 0) {
            sensor_channel_get(vl53l0x_dev, SENSOR_CHAN_DISTANCE, &distance);
            /* distance.val1 = meters integer, distance.val2 = micro-meters fractional */
            int mm = distance.val1 * 1000 + distance.val2 / 1000;
            printk("Distance: %d mm\n", mm);
        } else {
            printk("Sensor error: %d\n", ret);
        }
        k_msleep(1000);
    }
}
```

---

## Gesture Detection Pattern (Hand Swipe)

A rapid decrease then increase in distance within a short time window indicates a swipe gesture.

```cpp
/* Arduino example */
#define GESTURE_THRESHOLD_MM  200  // hand must be within 200mm
#define GESTURE_DELTA_MM      100  // must change by 100mm rapidly

int prev_dist = 9999;
bool output_state = false;
unsigned long last_gesture = 0;

void loop() {
    VL53L0X_RangingMeasurementData_t m;
    lox.rangingTest(&m, false);

    if (m.RangeStatus != 0) { prev_dist = 9999; return; }
    int dist = m.RangeMilliMeter;

    int delta = abs(dist - prev_dist);
    bool gesture = (delta > GESTURE_DELTA_MM) && (prev_dist < GESTURE_THRESHOLD_MM);

    if (gesture && (millis() - last_gesture) > 500) {
        output_state = !output_state;
        last_gesture = millis();
        Serial.print("gesture=detected, output=");
        Serial.println(output_state ? "on" : "off");
    } else {
        Serial.print("gesture=none, output=");
        Serial.println(output_state ? "on" : "off");
    }
    prev_dist = dist;
    delay(50);
}
```

## Best Practices
1. Use the Adafruit VL53L0X or Pololu library — the raw initialization sequence is very complex
2. Set timing budget to 200ms for better accuracy (default 33ms is fast but noisy)
3. The sensor reads ~8190mm when out of range — check `RangeStatus == 0` for valid readings
4. Place XSHUT pins on GPIO to enable address reconfiguration for multiple sensors
5. Keep I2C at 400 kHz (fast mode) for responsive measurements

## Common Pitfalls
- ❌ Not checking `RangeStatus`: 0 = valid, others = error
- ❌ Reading without initialization (the long calibration sequence must complete)
- ❌ Distance reads 8190 — object is out of range or no target
- ❌ Too-short timing budget (< 20ms) causes unreliable readings

## Related Skills
- `i2c-communication-esp32-esp-idf.md` - I2C setup for ESP32
- `i2c-communication-atmega2560-arduino.md` - I2C setup for Arduino
