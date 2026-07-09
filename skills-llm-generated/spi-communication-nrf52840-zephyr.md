---
name: SPI Communication - nRF52840 + Zephyr RTOS
description: This skill covers SPI master communication on nRF52840 using Zephyr RTOS. Covers device tree configuration, Zephyr SPI driver API, transceive operations, and patterns for SD cards and PN532 NFC controllers.
---
# SPI Communication - nRF52840 + Zephyr RTOS

## Overview
Zephyr provides a unified SPI driver API. SPI peripherals are configured in the device tree. The `spi_transceive()` function handles full-duplex transfers. Multiple slave devices can share the same bus with different CS configurations.

## Target Platform
- **MCU:** nRF52840
- **Board:** nRF52840-DK, Arduino Nano 33 BLE
- **Framework:** Zephyr RTOS
- **API:** `zephyr/drivers/spi.h`
- **SPI Peripherals:** SPIM0-SPIM3

## Device Tree Configuration

```dts
/* board.overlay */
&spi2 {
    compatible = "nordic,nrf-spim";
    status = "okay";
    pinctrl-0 = <&spi2_default>;
    pinctrl-names = "default";
    cs-gpios = <&gpio0 17 GPIO_ACTIVE_LOW>,   /* CS0: SD card */
               <&gpio0 22 GPIO_ACTIVE_LOW>;    /* CS1: NFC PN532 */

    sd_card: spi-dev@0 {
        compatible = "vnd,spi-device";
        reg = <0>;
        spi-max-frequency = <25000000>;
    };

    pn532: spi-dev@1 {
        compatible = "vnd,spi-device";
        reg = <1>;
        spi-max-frequency = <5000000>;
    };
};

&pinctrl {
    spi2_default: spi2_default {
        group1 {
            psels = <NRF_PSEL(SPIM_MOSI, 0, 13)>,
                    <NRF_PSEL(SPIM_MISO, 0, 12)>,
                    <NRF_PSEL(SPIM_SCK,  0, 14)>;
        };
    };
};
```

## prj.conf
```ini
CONFIG_SPI=y
CONFIG_SPI_NRFX=y
```

## Core SPI Functions

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/sys/printk.h>

static const struct device *spi_dev = DEVICE_DT_GET(DT_NODELABEL(spi2));

/* SPI config for a device: frequency, mode (CPOL/CPHA), CS */
static const struct spi_config spi_cfg_sd = {
    .frequency = 25000000,
    .operation = SPI_OP_MODE_MASTER | SPI_TRANSFER_MSB | SPI_WORD_SET(8),
    .cs = {
        .gpio = GPIO_DT_SPEC_GET_BY_IDX(DT_NODELABEL(spi2), cs_gpios, 0),
        .delay = 0,
    },
};

static const struct spi_config spi_cfg_nfc = {
    .frequency = 5000000,
    .operation = SPI_OP_MODE_MASTER | SPI_TRANSFER_MSB | SPI_WORD_SET(8),
    .cs = {
        .gpio = GPIO_DT_SPEC_GET_BY_IDX(DT_NODELABEL(spi2), cs_gpios, 1),
        .delay = 1,  /* 1μs CS delay */
    },
};

int spi_setup(void) {
    if (!device_is_ready(spi_dev)) {
        printk("SPI device not ready\n");
        return -ENODEV;
    }
    return 0;
}

/* Full-duplex transfer: send tx_buf, receive into rx_buf, both len bytes */
int spi_xfer(const struct spi_config *cfg,
             const uint8_t *tx_buf, uint8_t *rx_buf, size_t len) {
    const struct spi_buf tx = { .buf = (void *)tx_buf, .len = len };
    const struct spi_buf rx = { .buf = rx_buf,         .len = len };
    const struct spi_buf_set tx_set = { .buffers = &tx, .count = 1 };
    const struct spi_buf_set rx_set = { .buffers = &rx, .count = 1 };
    return spi_transceive(spi_dev, cfg, &tx_set, &rx_set);
}

/* Write-only (no read) */
int spi_write_only(const struct spi_config *cfg, const uint8_t *data, size_t len) {
    const struct spi_buf tx = { .buf = (void *)data, .len = len };
    const struct spi_buf_set tx_set = { .buffers = &tx, .count = 1 };
    return spi_write(spi_dev, cfg, &tx_set);
}

/* Scatter-gather: write command byte, then read N bytes */
int spi_cmd_read(const struct spi_config *cfg,
                 uint8_t cmd, uint8_t *rx_buf, size_t rx_len) {
    uint8_t dummy[rx_len];
    memset(dummy, 0xFF, rx_len);

    /* Two TX buffers: command byte + dummy bytes for clocking */
    const struct spi_buf tx_bufs[] = {
        { .buf = &cmd,    .len = 1      },
        { .buf = dummy,   .len = rx_len },
    };
    /* Two RX buffers: discard first, keep rest */
    uint8_t rx_cmd_byte;
    const struct spi_buf rx_bufs[] = {
        { .buf = &rx_cmd_byte, .len = 1      },
        { .buf = rx_buf,       .len = rx_len },
    };
    const struct spi_buf_set tx_set = { .buffers = tx_bufs, .count = 2 };
    const struct spi_buf_set rx_set = { .buffers = rx_bufs, .count = 2 };
    return spi_transceive(spi_dev, cfg, &tx_set, &rx_set);
}
```

## Manual CS Control (When Not Using DTS cs-gpios)

```c
#include <zephyr/drivers/gpio.h>

#define CS_NODE DT_ALIAS(cs_gpio)
static const struct gpio_dt_spec cs_gpio = GPIO_DT_SPEC_GET(CS_NODE, gpios);

/* SPI config without built-in CS management */
static const struct spi_config spi_cfg_manual = {
    .frequency = 5000000,
    .operation = SPI_OP_MODE_MASTER | SPI_TRANSFER_MSB | SPI_WORD_SET(8),
    .cs = { .gpio = { .port = NULL } },  /* no auto CS */
};

void cs_assert(void)   { gpio_pin_set_dt(&cs_gpio, 0); }
void cs_deassert(void) { gpio_pin_set_dt(&cs_gpio, 1); }

int spi_xfer_manual(const uint8_t *tx, uint8_t *rx, size_t len) {
    cs_assert();
    int ret = spi_xfer(&spi_cfg_manual, tx, rx, len);
    cs_deassert();
    return ret;
}
```

## Best Practices
1. Define one `spi_config` per device (each has its own frequency, mode, CS)
2. Use `cs-gpios` in DTS for automatic CS management — cleaner and safer
3. Scatter-gather (`spi_buf_set` with multiple buffers) avoids memcpy overhead
4. Buffers must be accessible by DMA — use stack with caution on some platforms
5. Check `device_is_ready()` in init, not in each transaction

## Common Pitfalls
- ❌ Forgetting `CONFIG_SPI=y` and `CONFIG_SPI_NRFX=y` in prj.conf
- ❌ Mixing tx/rx null pointers improperly — use `spi_write()` or `spi_read()` for half-duplex
- ❌ Wrong `SPI_MODE_CPOL` / `SPI_MODE_CPHA` flags for device
- ❌ Incorrect CS gpio index in `GPIO_DT_SPEC_GET_BY_IDX`
- ❌ DMA-restricted buffers (some nRF52 SPIM requires buffers in RAM, not flash)

## Related Skills
- `microsd-spi.md` - MicroSD card file operations
- `pn532-nfc-rfid.md` - PN532 NFC in SPI mode
