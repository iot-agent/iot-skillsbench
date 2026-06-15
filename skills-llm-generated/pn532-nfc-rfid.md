---
name: PN532 NFC/RFID Controller (I2C and SPI)
description: This skill covers the Adafruit PN532 NFC/RFID shield/breakout via I2C and SPI. Includes SAMConfiguration, reading NFC tag UID, MIFARE Classic block authentication and reading, and authorized tag matching. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# PN532 NFC/RFID Controller (I2C and SPI)

## Overview
The PN532 is an NFC controller IC from NXP. It supports ISO 14443A/B cards (MIFARE Classic, Ultralight, NTAG) and NFC peer-to-peer. The Adafruit breakout supports I2C, SPI, or UART via mode select switches.

## Hardware Specs
- **I2C Address:** 0x24 (SEL1=1, SEL0=0 for I2C mode)
- **SPI:** Up to 5 MHz, Mode 0 (CPOL=0, CPHA=0)
- **IRQ Pin:** LOW when data is ready (optional but recommended)
- **RESET Pin:** Active-low reset
- **Supply:** 3.3V–5V

## Interface Mode Selection (Adafruit breakout)
```
SEL1=LOW,  SEL0=LOW  → UART
SEL1=HIGH, SEL0=LOW  → I2C   (I2C address 0x24)
SEL1=LOW,  SEL0=HIGH → SPI
```

## Key PN532 Commands
```
0x14 SAMConfiguration   - Configure Secure Access Module
0x4A InListPassiveTarget - Detect one passive NFC target, read UID
0x40 InDataExchange     - Exchange data with activated target
0x60 InCommunicateThru  - Pass-through communication
```

## PN532 Packet Format (I2C/SPI)
```
Preamble:  0x00
Start Code: 0x00 0xFF
LEN:       N  (data length, TFI + data)
LCS:       ~LEN + 1  (length checksum)
TFI:       0xD4  (host-to-PN532)
CMD:       command byte
DATA:      optional parameters
DCS:       checksum of TFI+CMD+DATA (sum should make 0x00 mod 256)
Postamble: 0x00

Response:
TFI:       0xD5
CMD+1:     response code = command + 1
DATA:      response data
```

---

## ATMega2560 + Arduino Implementation (Using Adafruit Library)

This is the recommended approach — the Adafruit_PN532 library handles the full protocol.

```cpp
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_PN532.h>

/* I2C mode (connect IRQ=2, RESET=3, SDA=20, SCL=21 on Mega) */
#define PN532_IRQ   2
#define PN532_RESET 3
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);  /* I2C mode */

/* SPI mode (alternatively): */
// #define PN532_SCK  52, MISO=50, MOSI=51
// #define PN532_SS   10
// Adafruit_PN532 nfc(PN532_SCK, MISO, MOSI, PN532_SS);

void setup() {
    Wire.begin();
    Serial.begin(115200);
    nfc.begin();

    uint32_t versiondata = nfc.getFirmwareVersion();
    if (!versiondata) {
        Serial.println("PN532 not found");
        while (1);
    }
    Serial.print("PN532 firmware v");
    Serial.print((versiondata >> 16) & 0xFF);
    Serial.print('.'); Serial.println((versiondata >> 8) & 0xFF);

    nfc.SAMConfig();  /* Configure SAM (required before any target detection) */
    Serial.println("Waiting for NFC tag...");
}

void loop() {
    uint8_t uid[7], uid_len;

    /* Detect ISO14443A card (includes MIFARE Classic, Ultralight, NTAG) */
    if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uid_len)) {
        Serial.print("UID (");
        Serial.print(uid_len);
        Serial.print(" bytes): ");
        for (uint8_t i = 0; i < uid_len; i++) {
            if (i) Serial.print(":");
            if (uid[i] < 0x10) Serial.print("0");
            Serial.print(uid[i], HEX);
        }
        Serial.println();
    }
    delay(100);
}
```

### NFC Door Lock (UID whitelist)
```cpp
/* Pre-authorized UID list */
uint8_t authorized_uids[][4] = {
    {0xDE, 0xAD, 0xBE, 0xEF},
    {0xAB, 0xCD, 0x12, 0x34},
};
int num_authorized = 2;

bool isAuthorized(const uint8_t *uid, uint8_t len) {
    if (len != 4) return false;
    for (int i = 0; i < num_authorized; i++) {
        if (memcmp(uid, authorized_uids[i], 4) == 0) return true;
    }
    return false;
}

void loop() {
    uint8_t uid[7], uid_len;
    if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uid_len)) {
        bool auth = isAuthorized(uid, uid_len);
        if (auth) {
            Serial.println("Unlocking...");
            digitalWrite(RELAY_PIN, HIGH);  /* Unlock relay */
            delay(5000);
            digitalWrite(RELAY_PIN, LOW);
        }
        Serial.print("uid="); for(int i=0;i<uid_len;i++) { Serial.print(uid[i],HEX); Serial.print(":"); }
        Serial.print(", access="); Serial.println(auth ? "granted" : "denied");
    }
}
```

### MIFARE Classic Block Authentication and Read
```cpp
/* Authenticate and read block from MIFARE Classic 1K */
bool readMifareBlock(uint8_t block, uint8_t *data) {
    /* Default MIFARE Key A: {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF} */
    uint8_t key[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    uint8_t uid[7]; uint8_t uid_len;

    if (!nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uid_len)) return false;

    if (!nfc.mifareclassic_AuthenticateBlock(uid, uid_len, block, 0, key)) {
        Serial.println("Auth failed");
        return false;
    }
    if (!nfc.mifareclassic_ReadDataBlock(block, data)) {
        Serial.println("Read failed");
        return false;
    }
    return true;
}

void loop() {
    uint8_t block_data[16];
    if (readMifareBlock(4, block_data)) {
        Serial.print("auth=ok, block_data=");
        for (int i = 0; i < 16; i++) {
            if (block_data[i] < 0x10) Serial.print("0");
            Serial.print(block_data[i], HEX);
            Serial.print(" ");
        }
        Serial.println();
    } else {
        Serial.println("auth=fail, block_data=N/A");
    }
    delay(1000);
}
```

### SPI Mode Setup (Arduino)
```cpp
#include <SPI.h>
#include <Adafruit_PN532.h>

#define PN532_SCK  52
#define PN532_MISO 50
#define PN532_MOSI 51
#define PN532_SS   10

Adafruit_PN532 nfc(PN532_SCK, PN532_MISO, PN532_MOSI, PN532_SS);

void setup() {
    SPI.begin();
    nfc.begin();
    nfc.SAMConfig();
}
```

---

## ESP32 + ESP-IDF Implementation

```c
/* For ESP32, use ESP-IDF I2C to talk to PN532 */
/* Or use Arduino framework with Adafruit_PN532 via Wire+ESP-IDF backend */

#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>

#define PN532_ADDR 0x24

/* PN532 frame builder and transaction functions */
static uint8_t pn532_calc_dcs(const uint8_t *data, uint8_t len) {
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; i++) sum += data[i];
    return (uint8_t)(~sum + 1);  /* two's complement */
}

static void pn532_build_cmd(uint8_t *buf, uint8_t *out_len,
                             const uint8_t *data, uint8_t data_len) {
    uint8_t len = data_len + 1;  /* TFI + data */
    uint8_t lcs = (~len + 1) & 0xFF;
    uint8_t dcs = pn532_calc_dcs(data, data_len);
    /* TFI (0xD4) is included in data[0] = 0xD4, data[1] = cmd, ... */
    int pos = 0;
    buf[pos++] = 0x00;   /* preamble */
    buf[pos++] = 0x00;   /* start code */
    buf[pos++] = 0xFF;
    buf[pos++] = len;
    buf[pos++] = lcs;
    for (uint8_t i = 0; i < data_len; i++) buf[pos++] = data[i];
    buf[pos++] = dcs;
    buf[pos++] = 0x00;   /* postamble */
    *out_len = pos;
}

/* SAMConfiguration: put SAM in Normal mode */
static bool pn532_sam_config(void) {
    uint8_t cmd_data[] = {0xD4, 0x14, 0x01, 0x14, 0x01};
    uint8_t buf[12]; uint8_t buf_len;
    pn532_build_cmd(buf, &buf_len, cmd_data, sizeof(cmd_data));

    /* Write to PN532 */
    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (PN532_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(hdl, buf, buf_len, true);
    i2c_master_stop(hdl);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);
    if (ret != ESP_OK) return false;
    vTaskDelay(pdMS_TO_TICKS(10));
    return true;
}

/* Read passive target (MIFARE ISO14443A), fill uid[] and uid_len */
bool pn532_read_uid(uint8_t *uid, uint8_t *uid_len) {
    uint8_t cmd_data[] = {0xD4, 0x4A, 0x01, 0x00};
    uint8_t buf[12]; uint8_t buf_len;
    pn532_build_cmd(buf, &buf_len, cmd_data, sizeof(cmd_data));

    /* Write command */
    i2c_cmd_handle_t hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (PN532_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(hdl, buf, buf_len, true);
    i2c_master_stop(hdl);
    i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);
    vTaskDelay(pdMS_TO_TICKS(100));  /* wait for response */

    /* Read response (20 bytes should be enough) */
    uint8_t resp[20];
    hdl = i2c_cmd_link_create();
    i2c_master_start(hdl);
    i2c_master_write_byte(hdl, (PN532_ADDR << 1) | I2C_MASTER_READ, true);
    i2c_master_read(hdl, resp, 19, I2C_MASTER_ACK);
    i2c_master_read_byte(hdl, resp + 19, I2C_MASTER_NACK);
    i2c_master_stop(hdl);
    i2c_master_cmd_begin(I2C_NUM_0, hdl, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(hdl);

    /* Parse: resp[7] = targets found, resp[8] = ATQA[0], [9]=ATQA[1],
       resp[10]=SAK, resp[11]=NfcIdLength, resp[12+] = UID */
    if (resp[0] != 0x00 || resp[1] != 0x00 || resp[2] != 0xFF) return false;
    if (resp[7] == 0) return false;  /* no targets */
    *uid_len = resp[12];
    memcpy(uid, resp + 13, *uid_len);
    return true;
}

void pn532_task(void *arg) {
    pn532_sam_config();
    uint8_t uid[7]; uint8_t uid_len;
    while (1) {
        if (pn532_read_uid(uid, &uid_len)) {
            printf("UID: ");
            for (int i = 0; i < uid_len; i++) printf("%02X ", uid[i]);
            printf("\n");
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* Zephyr: no built-in PN532 driver; use raw I2C from i2c-communication-nrf52840-zephyr.md */
/* Pattern: same as ESP32 approach using i2c_write / i2c_read on i2c_dev */

#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <string.h>

#define PN532_ADDR 0x24
static const struct device *i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

/* Use same packet building functions as ESP32 version */
/* pn532_build_cmd(), pn532_sam_config(), pn532_read_uid() — adapt i2c calls */

static bool zephyr_pn532_write(const uint8_t *buf, size_t len) {
    return i2c_write(i2c_dev, buf, len, PN532_ADDR) == 0;
}

static bool zephyr_pn532_read(uint8_t *buf, size_t len) {
    return i2c_read(i2c_dev, buf, len, PN532_ADDR) == 0;
}

int main(void) {
    if (!device_is_ready(i2c_dev)) return -1;
    /* Initialize SAM, then poll for tags using pn532_read_uid() */
    while (1) {
        uint8_t uid[7]; uint8_t uid_len;
        if (pn532_read_uid(uid, &uid_len)) {
            printk("UID: ");
            for (int i = 0; i < uid_len; i++) printk("%02X ", uid[i]);
            printk("\n");
        }
        k_msleep(500);
    }
}
```

## Best Practices
1. Always call SAMConfig() after power-on/reset before reading tags
2. Use the Adafruit_PN532 library on Arduino — it handles ACK polling and protocol details
3. For I2C, check the IRQ pin (LOW = data ready) instead of polling blindly
4. MIFARE Classic blocks 0, 4, 8, ... are "sector trailers" — don't overwrite them
5. For SPI, PN532 requires LSB-first (SPI_LSBFIRST) on some implementations

## Common Pitfalls
- ❌ Wrong interface mode (check SEL1/SEL0 on breakout)
- ❌ Missing SAMConfig() — reading targets returns no response
- ❌ Reading I2C before PN532 is ready (no IRQ pin check)
- ❌ MIFARE Classic: reading block without authentication first
- ❌ Reading UID too quickly after presentation (add 50–100ms delay)

## Related Skills
- `i2c-communication-atmega2560-arduino.md` - Arduino I2C
- `spi-communication-atmega2560-arduino.md` - Arduino SPI for PN532 SPI mode
- `relay-gpio-control.md` - Relay for door lock on NFC auth
