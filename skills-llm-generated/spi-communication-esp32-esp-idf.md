---
name: SPI Communication - ESP32 + ESP-IDF
description: This skill covers SPI (Serial Peripheral Interface) master communication on ESP32 using ESP-IDF. Covers bus initialization, device add, full-duplex transactions, DMA, and patterns for SD cards and NFC controllers (PN532).
---
# SPI Communication - ESP32 + ESP-IDF

## Overview
SPI is a synchronous serial protocol that uses 4 signals: MOSI, MISO, SCLK, and CS (chip select). ESP32 has 4 SPI buses: SPI0/SPI1 (internal flash), SPI2 (HSPI), SPI3 (VSPI). Use SPI2 or SPI3 for custom peripherals.

## Target Platform
- **MCU:** ESP32
- **Framework:** ESP-IDF
- **API:** `driver/spi_master.h`
- **Buses Available:** SPI2 (HSPI), SPI3 (VSPI)

## Key Concepts
- **Full-Duplex:** MOSI and MISO transfer simultaneously in one transaction
- **Clock Phase/Polarity (CPOL/CPHA):** Mode 0 (0,0) is most common
- **CS (Chip Select):** Active-low signal selects one device; ESP-IDF manages it per transaction
- **DMA:** For transfers >64 bytes, DMA improves efficiency
- **Max Speed:** Up to 80 MHz (practically 20-26 MHz for most devices)

## Default SPI Pin Mapping
```
SPI2 (HSPI): MOSI=GPIO13, MISO=GPIO12, SCLK=GPIO14, CS=GPIO15
SPI3 (VSPI): MOSI=GPIO23, MISO=GPIO19, SCLK=GPIO18, CS=GPIO5
```

## Basic SPI Master Setup

```c
#include <stdio.h>
#include <string.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "SPI";

#define SPI_BUS        SPI2_HOST
#define PIN_MOSI       13
#define PIN_MISO       12
#define PIN_SCLK       14
#define PIN_CS         15
#define SPI_CLK_HZ     1000000   // 1 MHz

static spi_device_handle_t spi_handle;

esp_err_t spi_master_init(void)
{
    spi_bus_config_t bus_cfg = {
        .mosi_io_num   = PIN_MOSI,
        .miso_io_num   = PIN_MISO,
        .sclk_io_num   = PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };

    ESP_ERROR_CHECK(spi_bus_initialize(SPI_BUS, &bus_cfg, SPI_DMA_CH_AUTO));

    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = SPI_CLK_HZ,
        .mode           = 0,       // CPOL=0, CPHA=0
        .spics_io_num   = PIN_CS,
        .queue_size     = 7,
        .pre_cb         = NULL,
        .post_cb        = NULL,
    };

    ESP_ERROR_CHECK(spi_bus_add_device(SPI_BUS, &dev_cfg, &spi_handle));
    ESP_LOGI(TAG, "SPI master initialized");
    return ESP_OK;
}

// Transmit and receive N bytes (full-duplex)
esp_err_t spi_transfer(const uint8_t *tx_buf, uint8_t *rx_buf, size_t len)
{
    spi_transaction_t t = {
        .length    = len * 8,  // length in bits
        .tx_buffer = tx_buf,
        .rx_buffer = rx_buf,
    };
    return spi_device_transmit(spi_handle, &t);
}

// Write-only transaction (no MISO read)
esp_err_t spi_write(const uint8_t *data, size_t len)
{
    spi_transaction_t t = {
        .length    = len * 8,
        .tx_buffer = data,
        .rx_buffer = NULL,
        .flags     = SPI_TRANS_USE_RXDATA,  // discard RX
    };
    return spi_device_transmit(spi_handle, &t);
}

// Write register then read response (common pattern)
esp_err_t spi_write_read(uint8_t reg, uint8_t *rx_buf, size_t rx_len)
{
    uint8_t tx_buf[rx_len + 1];
    uint8_t full_rx[rx_len + 1];
    memset(tx_buf, 0xFF, sizeof(tx_buf));
    tx_buf[0] = reg;

    spi_transaction_t t = {
        .length    = (rx_len + 1) * 8,
        .tx_buffer = tx_buf,
        .rx_buffer = full_rx,
    };
    esp_err_t ret = spi_device_transmit(spi_handle, &t);
    if (ret == ESP_OK) {
        memcpy(rx_buf, full_rx + 1, rx_len);
    }
    return ret;
}
```

## Multiple SPI Devices on Same Bus

```c
#define PIN_CS_SD    5
#define PIN_CS_NFC   22

static spi_device_handle_t sd_handle;
static spi_device_handle_t nfc_handle;

esp_err_t spi_multi_device_init(void)
{
    // Initialize bus once
    spi_bus_config_t bus_cfg = {
        .mosi_io_num   = PIN_MOSI,
        .miso_io_num   = PIN_MISO,
        .sclk_io_num   = PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };
    spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO);

    // SD card: up to 25 MHz, mode 0
    spi_device_interface_config_t sd_cfg = {
        .clock_speed_hz = 25000000,
        .mode           = 0,
        .spics_io_num   = PIN_CS_SD,
        .queue_size     = 7,
    };
    spi_bus_add_device(SPI2_HOST, &sd_cfg, &sd_handle);

    // PN532 NFC: up to 5 MHz, mode 0
    spi_device_interface_config_t nfc_cfg = {
        .clock_speed_hz = 5000000,
        .mode           = 0,
        .spics_io_num   = PIN_CS_NFC,
        .queue_size     = 7,
    };
    spi_bus_add_device(SPI2_HOST, &nfc_cfg, &nfc_handle);

    return ESP_OK;
}
```

## Polling vs. Interrupt-Driven Transactions

```c
// Polling (blocking, simpler)
esp_err_t spi_send_polling(const uint8_t *data, size_t len)
{
    spi_transaction_t t = {
        .length    = len * 8,
        .tx_buffer = data,
    };
    return spi_device_polling_transmit(spi_handle, &t);
}

// Queued (non-blocking, use spi_device_get_trans_result to wait)
esp_err_t spi_send_queued(const uint8_t *data, size_t len)
{
    static spi_transaction_t t;
    t.length    = len * 8;
    t.tx_buffer = data;
    t.rx_buffer = NULL;
    spi_device_queue_trans(spi_handle, &t, portMAX_DELAY);

    spi_transaction_t *result;
    return spi_device_get_trans_result(spi_handle, &result, portMAX_DELAY);
}
```

## Best Practices
1. Call `spi_bus_initialize()` once per bus; add multiple devices with `spi_bus_add_device()`
2. Use `SPI_DMA_CH_AUTO` for transfers >64 bytes; use `SPI_DMA_DISABLED` for tiny transfers
3. Set `max_transfer_sz` to the largest single transfer size
4. For SD cards, start at 400 kHz for init, then switch to 25 MHz
5. Buffers for DMA transfers must be in DMA-capable memory (`heap_caps_malloc(sz, MALLOC_CAP_DMA)`)

## Common Pitfalls
- ❌ Using SPI0/SPI1 (reserved for internal flash)
- ❌ Not setting `max_transfer_sz` large enough (causes assertion failure)
- ❌ Stack-allocated buffers for DMA (must be in DMA-capable region)
- ❌ Wrong SPI mode for device (check CPOL/CPHA in datasheet)
- ❌ CS toggling manually instead of letting ESP-IDF manage it

## Related Skills
- `microsd-spi.md` - MicroSD card via SPI
- `pn532-nfc-rfid.md` - PN532 NFC/RFID in SPI mode
