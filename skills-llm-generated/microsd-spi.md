---
name: MicroSD Card via SPI
description: This skill covers reading/writing files on a microSD card via SPI. Includes card initialization, file create/read/append operations, and logging patterns. Covers ESP32+ESP-IDF, ATMega2560+Arduino (SD.h and SdFat), and nRF52840+Zephyr (disk_access API).
---
# MicroSD Card via SPI

## Overview
A microSD card communicates via SPI at up to 25 MHz (data transfer) after initialization at ≤400 kHz. The file system (FAT32/exFAT) is accessed using a library; never use raw SPI for file I/O.

## Hardware Specs
- **Interface:** SPI
- **Initialization speed:** ≤400 kHz
- **Data transfer speed:** up to 25 MHz (SDHC/SDXC)
- **CS:** Active-low, one per card
- **Supported FS:** FAT16, FAT32, exFAT (exFAT for >32GB cards)

## SPI Wiring
```
MicroSD MOSI → MCU MOSI
MicroSD MISO ← MCU MISO
MicroSD CLK  → MCU SCLK
MicroSD CS   → GPIO (any)
MicroSD VCC  → 3.3V or 5V (per module)
MicroSD GND  → GND
```

---

## ATMega2560 + Arduino Implementation

### Using SD.h (Standard Library)
```cpp
#include <SPI.h>
#include <SD.h>

#define SD_CS_PIN 10

void setup() {
    SPI.begin();
    Serial.begin(115200);

    if (!SD.begin(SD_CS_PIN)) {
        Serial.println("sd_init=fail");
        while (1);
    }
    Serial.print("sd_init=ok, card_type=");
    /* SD.h does not expose card type directly; use SdFat for that */
    Serial.println("SD");
}

/* Write initial content, append a line, read back */
void fileWriteReadAppend() {
    /* Create/overwrite with initial content */
    File f = SD.open("test.txt", FILE_WRITE);
    if (!f) { Serial.println("Open failed"); return; }
    f.println("hello world");
    f.close();

    /* Append: FILE_WRITE opens at end on SD.h (not exactly append) */
    /* For true append, use SdFat library */
    f = SD.open("test.txt", FILE_WRITE);
    if (!f) return;
    f.println("iot-skillsbench");
    f.close();

    /* Read back */
    f = SD.open("test.txt");
    if (!f) return;
    Serial.println("--- File contents ---");
    while (f.available()) {
        Serial.write(f.read());
    }
    f.close();
}

void loop() {
    fileWriteReadAppend();
    while (1);  /* run once */
}
```

### Using SdFat Library (Recommended for exFAT and better control)
```cpp
#include <SPI.h>
#include <SdFat.h>

#define SD_CS_PIN 10

SdExFat sd;   /* ExFat for >32GB; use SdFat for FAT32 */

void setup() {
    Serial.begin(115200);
    SPI.begin();

    if (!sd.begin(SD_CS_PIN, SD_SCK_MHZ(4))) {
        Serial.println("sd_init=fail");
        sd.initErrorHalt();
    }
    Serial.print("sd_init=ok, card_type=");
    switch (sd.card()->type()) {
        case SD_CARD_TYPE_SD1:  Serial.println("SD1"); break;
        case SD_CARD_TYPE_SD2:  Serial.println("SD2"); break;
        case SD_CARD_TYPE_SDHC: Serial.println("SDHC/SDXC"); break;
        default:                Serial.println("Unknown"); break;
    }
}

void appendLog(const char *filename, const char *msg) {
    ExFile f;
    f.open(filename, O_RDWR | O_CREAT | O_AT_END);
    f.println(msg);
    f.close();
}

void readFile(const char *filename) {
    ExFile f;
    if (!f.open(filename, O_RDONLY)) return;
    while (f.available()) Serial.write(f.read());
    f.close();
}

/* Write "hello world", append "iot-skillsbench", read back */
void loop() {
    ExFile f;
    f.open("log.txt", O_WRITE | O_CREAT | O_TRUNC);
    f.println("hello world");
    f.close();

    appendLog("log.txt", "iot-skillsbench");
    readFile("log.txt");
    while (1);
}
```

### GPS + DS1307 Data Logger
```cpp
#include <SD.h>
#define SD_CS 10

void logGPS(float lat, float lon, const char *timestamp) {
    File f = SD.open("gps_log.csv", FILE_WRITE);
    if (!f) return;
    f.print(timestamp); f.print(",");
    f.print(lat, 6);    f.print(",");
    f.println(lon, 6);
    f.close();
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include <stdio.h>
#include <string.h>
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"
#include "driver/sdspi_host.h"
#include "driver/spi_common.h"

#define MOUNT_POINT "/sdcard"
#define SD_MOSI   23
#define SD_MISO   19
#define SD_CLK    18
#define SD_CS     5

static sdmmc_card_t *card;

esp_err_t sd_init(void) {
    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = false,
        .max_files              = 5,
        .allocation_unit_size   = 16 * 1024,
    };

    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = SD_MOSI,
        .miso_io_num = SD_MISO,
        .sclk_io_num = SD_CLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4000,
    };
    spi_bus_initialize(host.slot, &bus_cfg, SDSPI_DEFAULT_DMA);

    sdspi_device_config_t slot_config = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot_config.gpio_cs = SD_CS;
    slot_config.host_id = host.slot;

    esp_err_t ret = esp_vfs_fat_sdspi_mount(MOUNT_POINT, &host, &slot_config,
                                             &mount_config, &card);
    if (ret != ESP_OK) {
        printf("sd_init=fail\n");
        return ret;
    }
    printf("sd_init=ok, card_type=%s\n",
           card->is_mmc ? "MMC" : (card->ocr & SD_OCR_SDHC_CAP) ? "SDHC/SDXC" : "SDSC");
    return ESP_OK;
}

void sd_write_file(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "%s", content);
    fclose(f);
}

void sd_append_file(const char *path, const char *content) {
    FILE *f = fopen(path, "a");
    if (!f) return;
    fprintf(f, "%s", content);
    fclose(f);
}

void sd_read_file(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return;
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        printf("%s", line);
    }
    fclose(f);
}

void app_main(void) {
    if (sd_init() != ESP_OK) return;

    sd_write_file(MOUNT_POINT "/test.txt", "hello world\n");
    sd_append_file(MOUNT_POINT "/test.txt", "iot-skillsbench\n");
    sd_read_file(MOUNT_POINT "/test.txt");
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* prj.conf */
// CONFIG_DISK_ACCESS=y
// CONFIG_FAT_FILESYSTEM_ELM=y
// CONFIG_FILE_SYSTEM=y
// CONFIG_FILE_SYSTEM_FAT=y

#include <zephyr/kernel.h>
#include <zephyr/fs/fs.h>
#include <zephyr/storage/disk_access.h>
#include <ff.h>
#include <zephyr/sys/printk.h>

static FATFS fat_fs;
static struct fs_mount_t mp = {
    .type    = FS_FATFS,
    .fs_data = &fat_fs,
};

int sd_init(void) {
    /* SD card is typically registered as "SD" disk */
    if (disk_access_init("SD") != 0) {
        printk("sd_init=fail\n");
        return -1;
    }
    mp.mnt_point = "/SD:";
    int ret = fs_mount(&mp);
    if (ret < 0) {
        printk("sd_init=fail (mount=%d)\n", ret);
        return ret;
    }
    printk("sd_init=ok\n");
    return 0;
}

void sd_write(const char *path, const char *content) {
    struct fs_file_t f;
    fs_file_t_init(&f);
    if (fs_open(&f, path, FS_O_CREATE | FS_O_WRITE) < 0) return;
    fs_write(&f, content, strlen(content));
    fs_close(&f);
}

void sd_append(const char *path, const char *content) {
    struct fs_file_t f;
    fs_file_t_init(&f);
    if (fs_open(&f, path, FS_O_CREATE | FS_O_WRITE | FS_O_APPEND) < 0) return;
    fs_write(&f, content, strlen(content));
    fs_close(&f);
}

void sd_read(const char *path) {
    struct fs_file_t f;
    fs_file_t_init(&f);
    if (fs_open(&f, path, FS_O_READ) < 0) return;
    char buf[128];
    int n;
    while ((n = fs_read(&f, buf, sizeof(buf) - 1)) > 0) {
        buf[n] = '\0';
        printk("%s", buf);
    }
    fs_close(&f);
}

int main(void) {
    if (sd_init() < 0) return -1;
    sd_write("/SD:/test.txt", "hello world\n");
    sd_append("/SD:/test.txt", "iot-skillsbench\n");
    sd_read("/SD:/test.txt");
    return 0;
}
```

## Best Practices
1. Use SdFat library on Arduino — it supports exFAT for >32GB cards and proper append mode
2. Always close files after writing to flush the FAT table to the card
3. Start at ≤400 kHz for initialization, then increase to 4–25 MHz for transfers
4. Use a dedicated CS pin — don't share with other SPI devices on same pin
5. Add a short `delay(100)` or `k_msleep(100)` after power-on before initializing

## Common Pitfalls
- ❌ FILE_WRITE in SD.h opens at the end — use O_TRUNC for overwrite, O_AT_END for append
- ❌ Not closing the file before power loss — corrupts the FAT
- ❌ Using SPI speed >25 MHz (most cards limit to 25 MHz)
- ❌ exFAT cards (>32GB) need SdFat, not SD.h on Arduino
- ❌ Forgetting that file paths on Zephyr/FatFS are case-insensitive but must start with mount point

## Related Skills
- `spi-communication-esp32-esp-idf.md` - SPI setup for ESP32
- `spi-communication-atmega2560-arduino.md` - SPI setup for Arduino
- `gps-nmea-uart.md` - GPS data logging
- `ina219-power-sensor.md` - Power data logging
