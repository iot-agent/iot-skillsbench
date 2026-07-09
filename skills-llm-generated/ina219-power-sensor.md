---
name: INA219 High-Side DC Current/Power Sensor
description: This skill covers the INA219 bidirectional current/power monitor via I2C. Includes register map, calibration for voltage/current/power measurement, alert on overcurrent, and complete code examples for ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# INA219 High-Side DC Current/Power Sensor

## Overview
The INA219 measures shunt voltage and bus voltage via I2C, computes current and power internally using a programmed calibration value. It monitors up to 26V bus and ±3.2A current (with 0.1Ω shunt).

## Hardware Specs
- **Interface:** I2C
- **Default I2C Address:** 0x40 (A0=GND, A1=GND); can be 0x41, 0x44, 0x45
- **Bus Voltage Range:** 0–16V or 0–32V (configurable)
- **Shunt Voltage Range:** ±40mV to ±320mV (configurable)
- **Shunt Resistor:** Typically 0.1Ω

## Register Map
```
0x00 Configuration  - bus range, gain, resolution, mode
0x01 Shunt Voltage  - signed 16-bit, LSB = 10μV
0x02 Bus Voltage    - bits[15:3] = raw value (LSB = 4mV), bit[1] = CNVR, bit[0] = OVF
0x03 Power          - raw power (LSB = 20 × Current_LSB)
0x04 Current        - signed 16-bit, LSB = Current_LSB (calibration-dependent)
0x05 Calibration    - Cal = trunc(0.04096 / (Current_LSB × R_shunt))
```

## Calibration Formula
```
Current_LSB (A) = Max_Current / 32768
Power_LSB       = 20 × Current_LSB
Cal_Value       = trunc(0.04096 / (Current_LSB × R_shunt))

Example: R_shunt = 0.1Ω, Max_Current = 3.2A
  Current_LSB = 3.2 / 32768 ≈ 0.0000977 A ≈ 0.1mA
  Cal_Value   = trunc(0.04096 / (0.0001 × 0.1)) = 4096
```

## Configuration Register (0x00)
```
Bit 13:    BRNG  - Bus voltage range: 0=16V, 1=32V
Bits 12-11: PG   - Shunt gain: 00=±40mV, 01=±80mV, 10=±160mV, 11=±320mV
Bits 10-7:  BADC - Bus ADC resolution: 0011=12-bit (default)
Bits 6-3:   SADC - Shunt ADC resolution: 0011=12-bit (default)
Bits 2-0:   MODE - Operating mode:
              000=Power-down, 001=Shunt only, 010=Bus only,
              011=Shunt+Bus, 100=ADC off, 101=Shunt continuous,
              110=Bus continuous, 111=Shunt+Bus continuous
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define INA219_ADDR  0x40
/* i2c_read_bytes, i2c_write_bytes from i2c-communication-esp32-esp-idf.md */

/* Write 16-bit register (MSB first) */
static esp_err_t ina219_write_reg(uint8_t reg, uint16_t value) {
    uint8_t data[2] = { (value >> 8) & 0xFF, value & 0xFF };
    return i2c_write_bytes(INA219_ADDR, reg, data, 2);
}

/* Read 16-bit register (MSB first) */
static uint16_t ina219_read_reg(uint8_t reg) {
    uint8_t buf[2];
    i2c_read_bytes(INA219_ADDR, reg, buf, 2);
    return ((uint16_t)buf[0] << 8) | buf[1];
}

void ina219_init(void) {
    /* Cal: 0.1Ω shunt, 3.2A max, Current_LSB=0.0001A */
    ina219_write_reg(0x05, 4096);
    /* Config: 32V, ±320mV, 12-bit, continuous shunt+bus */
    ina219_write_reg(0x00, 0x399F);
}

float ina219_get_bus_voltage(void) {
    uint16_t raw = ina219_read_reg(0x02);
    return (raw >> 3) * 0.004f;  /* bits[15:3], 4mV/LSB */
}

float ina219_get_current_mA(void) {
    int16_t raw = (int16_t)ina219_read_reg(0x04);
    return raw * 0.1f;  /* 0.1mA/LSB with Cal=4096 */
}

float ina219_get_power_mW(void) {
    uint16_t raw = ina219_read_reg(0x03);
    return raw * 2.0f;  /* 20 × 0.1mA = 2mW/LSB */
}

void ina219_task(void *arg) {
    ina219_init();
    while (1) {
        float v    = ina219_get_bus_voltage();
        float i_ma = ina219_get_current_mA();
        float p_mw = v * i_ma;  /* or use ina219_get_power_mW() */
        printf("Voltage: %.1f V, Current: %d mA, Power: %.1f mW\n",
               v, (int)i_ma, p_mw);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* Energy alert: detect when current exceeds threshold */
void ina219_alert_task(void *arg) {
    ina219_init();
    float threshold_ma  = 1000.0f;  /* 1A threshold */
    uint32_t alert_clear_ms = 5000; /* must be below threshold 5s to clear */
    bool alert_active = false;
    uint32_t below_since = 0;

    while (1) {
        float i_ma = ina219_get_current_mA();

        if (i_ma > threshold_ma) {
            alert_active = true;
            below_since  = 0;
            printf("current=%.0f, alert=on\n", i_ma);
        } else {
            if (alert_active) {
                if (below_since == 0) below_since = xTaskGetTickCount();
                uint32_t elapsed_ms = (xTaskGetTickCount() - below_since) * portTICK_PERIOD_MS;
                if (elapsed_ms >= alert_clear_ms) alert_active = false;
            }
            printf("current=%.0f, alert=%s\n", i_ma, alert_active ? "on" : "off");
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219(0x40);  /* default address */

void setup() {
    Wire.begin();
    Serial.begin(115200);
    if (!ina219.begin()) {
        Serial.println("INA219 not found");
        while (1);
    }
    /* Use setCalibration_32V_2A() for 32V bus, 2A max */
    ina219.setCalibration_32V_2A();
    /* Or custom: ina219.setCalibration_16V_400mA() for low-current */
}

void loop() {
    float v    = ina219.getBusVoltage_V();
    float i_mA = ina219.getCurrent_mA();
    float p_mW = v * i_mA;

    Serial.print("Voltage: "); Serial.print(v, 1); Serial.print(" V, ");
    Serial.print("Current: "); Serial.print((int)i_mA); Serial.print(" mA, ");
    Serial.print("Power: ");   Serial.print(p_mW, 1); Serial.println(" mW");
    delay(1000);
}
```

### Manual I2C (without library)
```cpp
#include <Wire.h>
#define INA219_ADDR 0x40

uint16_t ina219_read(uint8_t reg) {
    Wire.beginTransmission(INA219_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)INA219_ADDR, (uint8_t)2);
    uint16_t val = (Wire.read() << 8) | Wire.read();
    return val;
}

void ina219_write(uint8_t reg, uint16_t val) {
    Wire.beginTransmission(INA219_ADDR);
    Wire.write(reg);
    Wire.write((val >> 8) & 0xFF);
    Wire.write(val & 0xFF);
    Wire.endTransmission();
}

void setup() {
    Wire.begin();
    Serial.begin(115200);
    ina219_write(0x05, 4096);   /* calibration */
    ina219_write(0x00, 0x399F); /* config */
}

void loop() {
    float v    = ((ina219_read(0x02) >> 3) * 4) / 1000.0f;
    float i_mA = (int16_t)ina219_read(0x04) * 0.1f;
    float p_mW = v * i_mA;
    Serial.print("Voltage: "); Serial.print(v, 1); Serial.print(" V, ");
    Serial.print("Current: "); Serial.print((int)i_mA); Serial.print(" mA, ");
    Serial.print("Power: "); Serial.print(p_mW, 1); Serial.println(" mW");
    delay(1000);
}
```

---

## nRF52840 + Zephyr Implementation

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

#define INA219_ADDR 0x40
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

static void ina219_write(uint8_t reg, uint16_t val) {
    uint8_t buf[3] = { reg, (val >> 8) & 0xFF, val & 0xFF };
    i2c_write(i2c_dev, buf, 3, INA219_ADDR);
}

static uint16_t ina219_read(uint8_t reg) {
    uint8_t buf[2];
    i2c_write_read(i2c_dev, INA219_ADDR, &reg, 1, buf, 2);
    return ((uint16_t)buf[0] << 8) | buf[1];
}

void ina219_init(void) {
    ina219_write(0x05, 4096);
    ina219_write(0x00, 0x399F);
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    ina219_init();

    while (1) {
        float v    = ((ina219_read(0x02) >> 3) * 4) / 1000.0f;
        float i_mA = (int16_t)ina219_read(0x04) * 0.1f;
        float p_mW = v * i_mA;
        printk("Voltage: %.1f V, Current: %d mA, Power: %.1f mW\n",
               v, (int)i_mA, p_mW);
        k_msleep(1000);
    }
}
```

## Best Practices
1. Match calibration to your shunt resistor value for accurate readings
2. Use `Adafruit_INA219` library on Arduino for simplified setup
3. Read current from register 0x04 (not derived from shunt voltage) for accuracy
4. Shunt voltage register (0x01) is signed — cast to `int16_t` before using

## Common Pitfalls
- ❌ Reading power register before calibration register is set (gives garbage)
- ❌ Forgetting to set calibration register (0x05) — current/power registers read 0
- ❌ Using wrong shunt resistance value in calibration
- ❌ Bus voltage register bits [2:0] are flags, not data — must shift right 3

## Related Skills
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C setup
- `lcd1602-i2c.md` - Display power info on LCD
- `microsd-spi.md` - Log power data to SD card
