---
name: I2C Communication - nRF52840 + Zephyr RTOS
description: This skill covers I2C master communication on nRF52840 using Zephyr RTOS. Covers device tree configuration, Zephyr I2C driver API, register read/write patterns, and multi-byte transfers for sensors like INA219, VL53L0X, LTR390, SGP40, PMSA003I, and LCD1602.
---
# I2C Communication - nRF52840 + Zephyr RTOS

## Overview
Zephyr provides a unified I2C driver API that abstracts hardware differences. I2C peripherals are declared in the device tree (DTS), and Zephyr's `i2c.h` API is used to communicate with them.

## Target Platform
- **MCU:** nRF52840
- **Board:** nRF52840-DK, Arduino Nano 33 BLE
- **Framework:** Zephyr RTOS
- **API:** `zephyr/drivers/i2c.h`
- **Default I2C pins (nRF52840-DK):** SDA=P0.26, SCL=P0.27

## Key Concepts
- **Device Tree (DTS):** Hardware is described in `.overlay` files; Zephyr binds drivers to nodes
- **`DEVICE_DT_GET`:** Macro to get device pointer from DTS node at compile time
- **`i2c_write_read()`:** Combined write+read in one transaction (repeated START)
- **`i2c_reg_read_byte()`:** Helper to read one byte from a register
- **`i2c_reg_write_byte()`:** Helper to write one byte to a register
- **Thread safety:** Zephyr I2C driver is thread-safe (uses internal mutex)

## Device Tree Configuration

### board.overlay
```dts
&i2c0 {
    status = "okay";
    pinctrl-0 = <&i2c0_default>;
    pinctrl-names = "default";
    clock-frequency = <I2C_BITRATE_FAST>;  /* 400 kHz */

    ina219: ina219@40 {
        compatible = "i2c-device";
        reg = <0x40>;
        label = "INA219";
    };

    vl53l0x: vl53l0x@29 {
        compatible = "i2c-device";
        reg = <0x29>;
        label = "VL53L0X";
    };
};

&pinctrl {
    i2c0_default: i2c0_default {
        group1 {
            psels = <NRF_PSEL(TWIM_SDA, 0, 26)>,
                    <NRF_PSEL(TWIM_SCL, 0, 27)>;
        };
    };
};
```

## C Code: Core I2C Functions

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

/* Get I2C bus device from DTS */
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

int i2c_setup(void) {
    if (!device_is_ready(i2c_dev)) {
        printk("I2C device not ready\n");
        return -ENODEV;
    }
    return 0;
}

/* Write a byte to a register */
int i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t value) {
    uint8_t buf[2] = { reg, value };
    return i2c_write(i2c_dev, buf, sizeof(buf), addr);
}

/* Write 16-bit value MSB first */
int i2c_write_word(uint8_t addr, uint8_t reg, uint16_t value) {
    uint8_t buf[3] = { reg, (value >> 8) & 0xFF, value & 0xFF };
    return i2c_write(i2c_dev, buf, sizeof(buf), addr);
}

/* Write multiple bytes to a register */
int i2c_write_bytes(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len) {
    uint8_t buf[len + 1];
    buf[0] = reg;
    memcpy(buf + 1, data, len);
    return i2c_write(i2c_dev, buf, len + 1, addr);
}

/* Read N bytes from a register (write reg addr, then read) */
int i2c_read_bytes(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
    return i2c_write_read(i2c_dev, addr, &reg, 1, buf, len);
}

/* Read a single register byte */
int i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *value) {
    return i2c_write_read(i2c_dev, addr, &reg, 1, value, 1);
}

/* Read 16-bit value MSB first */
int i2c_read_word(uint8_t addr, uint8_t reg, uint16_t *value) {
    uint8_t buf[2];
    int ret = i2c_write_read(i2c_dev, addr, &reg, 1, buf, 2);
    if (ret == 0) {
        *value = ((uint16_t)buf[0] << 8) | buf[1];
    }
    return ret;
}

/* Raw read without register address (e.g., PMSA003I) */
int i2c_read_raw(uint8_t addr, uint8_t *buf, uint8_t len) {
    return i2c_read(i2c_dev, buf, len, addr);
}
```

## I2C Device Scanner

```c
void i2c_scan(void) {
    printk("Scanning I2C bus...\n");
    int found = 0;

    for (uint8_t addr = 1; addr < 127; addr++) {
        uint8_t dummy;
        /* Try to read 1 byte from each address */
        if (i2c_read(i2c_dev, &dummy, 1, addr) == 0) {
            printk("Device at 0x%02X\n", addr);
            found++;
        }
    }
    if (found == 0) printk("No devices found\n");
}
```

## Complete Example: INA219 Power Monitor

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

#define INA219_ADDR 0x40

static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

void ina219_init(void) {
    /* Calibration register for 0.1Ω shunt, 3.2A max, 0.1mA/LSB */
    i2c_write_word(INA219_ADDR, 0x05, 4096);
    /* Config: 32V bus, ±320mV shunt, 12-bit, continuous */
    i2c_write_word(INA219_ADDR, 0x00, 0x399F);
}

void ina219_read(float *bus_v, float *current_ma, float *power_mw) {
    uint16_t raw;

    /* Bus voltage (reg 0x02): bits[15:3], 4mV/LSB */
    i2c_read_word(INA219_ADDR, 0x02, &raw);
    *bus_v = (raw >> 3) * 0.004f;

    /* Current (reg 0x04): signed, 0.1mA/LSB */
    i2c_read_word(INA219_ADDR, 0x04, &raw);
    *current_ma = (int16_t)raw * 0.1f;

    *power_mw = *bus_v * (*current_ma);
}

int main(void) {
    if (!device_is_ready(i2c_dev)) {
        printk("I2C not ready\n");
        return -1;
    }

    ina219_init();

    float v, i_ma, p_mw;
    while (1) {
        ina219_read(&v, &i_ma, &p_mw);
        printk("Voltage: %.1f V, Current: %d mA, Power: %.1f mW\n",
               v, (int)i_ma, p_mw);
        k_msleep(1000);
    }
}
```

## Zephyr I2C Convenience Macros

```c
/* Built-in helper macros */
i2c_reg_read_byte(dev, addr, reg, &value);   /* read 1 byte from register */
i2c_reg_write_byte(dev, addr, reg, value);   /* write 1 byte to register */
i2c_burst_read(dev, addr, reg, buf, len);    /* read N bytes from register */
i2c_burst_write(dev, addr, reg, data, len);  /* write N bytes to register */
```

## CMakeLists.txt / Kconfig (required)

```cmake
# CMakeLists.txt — nothing special needed, I2C enabled via Kconfig

# prj.conf
CONFIG_I2C=y
CONFIG_I2C_NRFX=y    # or CONFIG_I2C_STM32 etc.
```

## Best Practices
1. Always call `device_is_ready()` before using the device
2. Use `DEVICE_DT_GET` with the DTS node label for compile-time checks
3. `i2c_write_read()` is the standard read-register pattern (writes reg addr, reads data)
4. For thread-safe access, Zephyr I2C driver already uses a mutex internally
5. Set `clock-frequency = <I2C_BITRATE_FAST>` in DTS for 400 kHz

## Common Pitfalls
- ❌ Forgetting `CONFIG_I2C=y` in `prj.conf`
- ❌ Using wrong DTS node label (check `gpio0` vs `i2c0` etc.)
- ❌ Confusing `i2c_write_read()` arg order (write buf then read buf)
- ❌ Not calling `device_is_ready()` — device may not be initialized yet
- ❌ Missing pinctrl configuration in overlay for custom boards

## Related Skills
- `i2c-communication-esp32-esp-idf.md` - ESP32 I2C reference
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C reference
