---
name: I2C Communication - ATMega2560 + Arduino
description: This skill covers I2C (Wire library) communication on Arduino Mega 2560 (ATMega2560). Includes master read/write operations, register access patterns, and practical examples for sensors like INA219, VL53L0X, LTR390, SGP40, PMSA003I, and LCD1602.
---
# I2C Communication - ATMega2560 + Arduino

## Overview
I2C (Inter-Integrated Circuit) is a two-wire serial bus used to connect sensors and peripherals. Arduino's `Wire` library provides I2C master functionality on the ATMega2560.

## Target Platform
- **MCU:** ATMega2560
- **Board:** Arduino Mega 2560
- **Framework:** Arduino
- **Library:** `Wire.h`
- **Pins:** SDA=Pin20, SCL=Pin21 (hardware I2C on ATMega2560)
- **Max Speed:** 400 kHz (Fast Mode)

## Key Concepts
- **7-bit addressing:** Device addresses range 0x00–0x7F
- **Master-initiated:** ATMega2560 always initiates transactions
- **Wire.begin():** Must be called once in setup()
- **Wire.setClock():** Sets bus frequency (default 100 kHz)
- **endTransmission(true):** Sends STOP; `(false)` sends repeated START

## Basic Setup

```cpp
#include <Wire.h>

void setup() {
    Wire.begin();           // Join I2C bus as master
    Wire.setClock(400000);  // 400 kHz fast mode (optional)
    Serial.begin(115200);
}
```

## Core Read/Write Functions

```cpp
// Write one or more bytes to a register
bool i2c_write_register(uint8_t addr, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
}

bool i2c_write_bytes(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(data, len);
    return Wire.endTransmission() == 0;
}

// Write 16-bit value (MSB first)
bool i2c_write_word(uint8_t addr, uint8_t reg, uint16_t value) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write((value >> 8) & 0xFF);
    Wire.write(value & 0xFF);
    return Wire.endTransmission() == 0;
}

// Read N bytes from a register address
bool i2c_read_bytes(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;  // repeated START

    Wire.requestFrom((uint8_t)addr, len);
    if (Wire.available() < len) return false;

    for (uint8_t i = 0; i < len; i++) {
        buf[i] = Wire.read();
    }
    return true;
}

// Read single register byte
bool i2c_read_register(uint8_t addr, uint8_t reg, uint8_t *value) {
    return i2c_read_bytes(addr, reg, value, 1);
}

// Read 16-bit value (MSB first)
bool i2c_read_word(uint8_t addr, uint8_t reg, uint16_t *value) {
    uint8_t buf[2];
    if (!i2c_read_bytes(addr, reg, buf, 2)) return false;
    *value = ((uint16_t)buf[0] << 8) | buf[1];
    return true;
}

// Read N bytes without register (e.g., PMSA003I streams 32 bytes)
bool i2c_read_raw(uint8_t addr, uint8_t *buf, uint8_t len) {
    Wire.requestFrom((uint8_t)addr, len);
    if (Wire.available() < len) return false;
    for (uint8_t i = 0; i < len; i++) {
        buf[i] = Wire.read();
    }
    return true;
}
```

## Read-Modify-Write Pattern

```cpp
bool i2c_set_bits(uint8_t addr, uint8_t reg, uint8_t mask, uint8_t value) {
    uint8_t current;
    if (!i2c_read_register(addr, reg, &current)) return false;
    current = (current & ~mask) | (value & mask);
    return i2c_write_register(addr, reg, current);
}
```

## I2C Device Scanner

```cpp
void i2c_scan() {
    Serial.println("Scanning I2C bus...");
    int found = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.print("Device at 0x");
            Serial.println(addr, HEX);
            found++;
        }
        delay(1);
    }
    if (found == 0) Serial.println("No devices found");
}
```

## Complete Example: INA219 Register Read

```cpp
#include <Wire.h>

#define INA219_ADDR 0x40

// Calibrate for 0.1Ω shunt, 3.2A max: Current_LSB = 0.1mA
#define INA219_CAL_VALUE 4096

void setup() {
    Wire.begin();
    Serial.begin(115200);

    // Write calibration register (0x05)
    i2c_write_word(INA219_ADDR, 0x05, INA219_CAL_VALUE);
    // Write config: 32V range, ±320mV shunt, 12-bit, continuous
    i2c_write_word(INA219_ADDR, 0x00, 0x399F);
}

void loop() {
    uint16_t raw;

    // Read shunt voltage (reg 0x01), LSB = 10μV
    i2c_read_word(INA219_ADDR, 0x01, &raw);
    float shunt_mv = (int16_t)raw * 0.01;

    // Read bus voltage (reg 0x02), shift right 3, LSB = 4mV
    i2c_read_word(INA219_ADDR, 0x02, &raw);
    float bus_v = (raw >> 3) * 0.004;

    // Read current (reg 0x04), LSB = 0.1mA
    i2c_read_word(INA219_ADDR, 0x04, &raw);
    float current_ma = (int16_t)raw * 0.1;

    Serial.print("V="); Serial.print(bus_v, 2);
    Serial.print("V, I="); Serial.print(current_ma, 1);
    Serial.println("mA");
    delay(1000);
}
```

## Best Practices
1. Call `Wire.begin()` once in `setup()`, not in loops
2. Use `Wire.setClock(400000)` for faster sensors that support it
3. Always check `endTransmission()` return value (0 = success)
4. ATMega2560 Wire buffer is 32 bytes — split large transfers
5. Add short `delay(1)` after writes before reading to let devices process

## Common Pitfalls
- ❌ Missing pull-up resistors (4.7kΩ on SDA and SCL)
- ❌ `Wire.requestFrom()` returns bytes available, not error code — check with `Wire.available()`
- ❌ Not using `(false)` in `endTransmission()` for repeated START (register select + read)
- ❌ Wire buffer overflow (ATMega2560 limit is 32 bytes)
- ❌ Wrong I2C pins (SDA=Pin20, SCL=Pin21 on Mega, not Pin18/19)

## I2C Addresses for Common Sensors
```
LCD1602 (PCF8574):  0x27 or 0x3F
INA219:             0x40 (default)
VL53L0X:            0x29
LTR390:             0x53
SGP40:              0x59
PMSA003I:           0x12
PN532 (I2C):        0x24
MAX32664:           0x55
DS1307:             0x68
```

## Related Skills
- `i2c-communication-esp32-esp-idf.md` - ESP32 ESP-IDF I2C reference
- `i2c-communication-nrf52840-zephyr.md` - Zephyr I2C reference
