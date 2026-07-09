---
name: SPI Communication - ATMega2560 + Arduino
description: This skill covers SPI (Serial Peripheral Interface) communication on Arduino Mega 2560 using the Arduino SPI library. Covers hardware SPI configuration, chip-select management, and patterns for SD cards and PN532 NFC controllers.
---
# SPI Communication - ATMega2560 + Arduino

## Overview
SPI is a synchronous 4-wire serial protocol. The ATMega2560 has one hardware SPI controller with dedicated pins. The Arduino `SPI` library provides a clean API for SPI master communication.

## Target Platform
- **MCU:** ATMega2560
- **Board:** Arduino Mega 2560
- **Framework:** Arduino
- **Library:** `SPI.h`
- **Hardware SPI Pins:** MOSI=51, MISO=50, SCLK=52, CS=manual

## Key Concepts
- **SPI Modes (CPOL/CPHA):**
  - Mode 0 (0,0): Clock idle LOW, sample on rising edge — most common
  - Mode 1 (0,1): Clock idle LOW, sample on falling edge
  - Mode 2 (1,0): Clock idle HIGH, sample on falling edge
  - Mode 3 (1,1): Clock idle HIGH, sample on rising edge
- **CS (Chip Select):** ATMega2560 Pin53 is hardware SS but any GPIO can be CS
- **MSBFIRST / LSBFIRST:** Bit order; most devices use MSBFIRST

## Basic SPI Setup

```cpp
#include <SPI.h>

#define CS_PIN 10  // Chip Select pin (any GPIO)

void setup() {
    SPI.begin();
    pinMode(CS_PIN, OUTPUT);
    digitalWrite(CS_PIN, HIGH);  // Deselect device

    // Optional: configure explicitly
    // SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
}

// Assert chip select (active LOW)
void cs_assert()   { digitalWrite(CS_PIN, LOW);  }
void cs_deassert() { digitalWrite(CS_PIN, HIGH); }
```

## Core Transfer Functions

```cpp
// Transfer one byte (full-duplex: sends tx, returns rx)
uint8_t spi_transfer_byte(uint8_t tx) {
    SPI.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0));
    cs_assert();
    uint8_t rx = SPI.transfer(tx);
    cs_deassert();
    SPI.endTransaction();
    return rx;
}

// Transfer a buffer (in-place: tx_rx overwritten with received data)
void spi_transfer_buf(uint8_t *tx_rx, size_t len) {
    SPI.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0));
    cs_assert();
    for (size_t i = 0; i < len; i++) {
        tx_rx[i] = SPI.transfer(tx_rx[i]);
    }
    cs_deassert();
    SPI.endTransaction();
}

// Write-only (ignore MISO)
void spi_write(const uint8_t *data, size_t len) {
    SPI.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0));
    cs_assert();
    for (size_t i = 0; i < len; i++) {
        SPI.transfer(data[i]);
    }
    cs_deassert();
    SPI.endTransaction();
}

// Write command byte, then read N response bytes
void spi_write_read(uint8_t cmd, uint8_t *rx_buf, size_t rx_len) {
    SPI.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0));
    cs_assert();
    SPI.transfer(cmd);
    for (size_t i = 0; i < rx_len; i++) {
        rx_buf[i] = SPI.transfer(0xFF);  // send dummy byte to clock in data
    }
    cs_deassert();
    SPI.endTransaction();
}
```

## Multiple SPI Devices (Separate CS Pins)

```cpp
#include <SPI.h>

#define CS_SD   10
#define CS_NFC  9

void setup() {
    SPI.begin();
    pinMode(CS_SD,  OUTPUT); digitalWrite(CS_SD,  HIGH);
    pinMode(CS_NFC, OUTPUT); digitalWrite(CS_NFC, HIGH);
}

// Access SD card
void sd_write(const uint8_t *data, size_t len) {
    SPI.beginTransaction(SPISettings(25000000, MSBFIRST, SPI_MODE0));
    digitalWrite(CS_SD, LOW);
    for (size_t i = 0; i < len; i++) SPI.transfer(data[i]);
    digitalWrite(CS_SD, HIGH);
    SPI.endTransaction();
}

// Access NFC controller
void nfc_write(const uint8_t *data, size_t len) {
    SPI.beginTransaction(SPISettings(5000000, MSBFIRST, SPI_MODE0));
    digitalWrite(CS_NFC, LOW);
    delay(1);  // some devices need CS setup time
    for (size_t i = 0; i < len; i++) SPI.transfer(data[i]);
    digitalWrite(CS_NFC, HIGH);
    SPI.endTransaction();
}
```

## SD Card Low-Level Init (without library)

```cpp
// Most projects use SD.h or SdFat library instead.
// This shows the raw SPI init sequence for reference.
void sd_init_sequence() {
    // Power-up: 74+ clock pulses with CS HIGH
    SPI.beginTransaction(SPISettings(250000, MSBFIRST, SPI_MODE0));
    cs_deassert();
    for (int i = 0; i < 10; i++) SPI.transfer(0xFF);  // 80 clocks
    
    // CMD0: Go idle (software reset)
    cs_assert();
    uint8_t cmd0[] = {0x40, 0x00, 0x00, 0x00, 0x00, 0x95};
    for (int i = 0; i < 6; i++) SPI.transfer(cmd0[i]);
    // Read response (R1) - expect 0x01
    uint8_t r1;
    for (int i = 0; i < 10; i++) {
        r1 = SPI.transfer(0xFF);
        if (r1 != 0xFF) break;
    }
    cs_deassert();
    SPI.endTransaction();
    // ... continue with CMD8, ACMD41, etc. (Use SD library instead)
}
```

## Best Practices
1. Always call `SPI.beginTransaction()` / `SPI.endTransaction()` to protect from interrupt conflicts
2. Keep CS HIGH when device is idle; only assert during an active transaction
3. Do not call `delay()` between `beginTransaction()` and `endTransaction()`
4. Use the SD library (`SD.h` or `SdFat.h`) instead of raw SPI for file systems
5. For PN532, use the Adafruit PN532 library — handles complex protocol automatically

## Common Pitfalls
- ❌ Forgetting `SPI.begin()` in `setup()`
- ❌ Leaving CS LOW after transaction (blocks other devices on shared bus)
- ❌ Wrong clock speed: SD init needs ≤400 kHz; data transfer can be up to 25 MHz
- ❌ Wrong SPI mode causes garbled data
- ❌ Calling `SPI.setClockDivider()` (deprecated in modern Arduino SPI API)

## Related Skills
- `microsd-spi.md` - MicroSD card file operations
- `pn532-nfc-rfid.md` - PN532 NFC in SPI mode
