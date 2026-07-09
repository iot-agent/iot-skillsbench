---
name: UART Communication - ATMega2560 + Arduino
description: This skill covers UART (Serial) communication on Arduino Mega 2560 (ATMega2560) using the Arduino framework. ATMega2560 has 4 hardware serial ports. Covers reading NMEA from GPS, binary packet protocol for fingerprint sensors, and software buffering patterns.
---
# UART Communication - ATMega2560 + Arduino

## Overview
The ATMega2560 has 4 hardware UART ports (Serial, Serial1, Serial2, Serial3), making it ideal for peripherals that need dedicated serial channels alongside the debug console.

## Target Platform
- **MCU:** ATMega2560
- **Board:** Arduino Mega 2560
- **Framework:** Arduino
- **Hardware Serials:** 4 (Serial, Serial1, Serial2, Serial3)
- **Max Baud Rate:** ~2 Mbps (practical limit ~115200 for most peripherals)

## Serial Port Pin Mapping
```
Serial  (UART0): TX=Pin1,  RX=Pin0  (USB/debug)
Serial1 (UART1): TX=Pin18, RX=Pin19
Serial2 (UART2): TX=Pin16, RX=Pin17
Serial3 (UART3): TX=Pin14, RX=Pin15
```

## Basic UART Setup

```cpp
void setup() {
    Serial.begin(115200);  // Debug output on USB

    // GPS module at 9600 baud on Serial1
    Serial1.begin(9600);

    // Fingerprint sensor at 57600 baud on Serial2
    Serial2.begin(57600);
}
```

## Polling-Based Line Reader (GPS NMEA)

```cpp
// Read a complete NMEA line from Serial1 into buf
// Returns true when a full line (ending \n) is received
bool readNMEALine(HardwareSerial &port, char *buf, size_t buf_size) {
    static char line[128];
    static size_t pos = 0;

    while (port.available()) {
        char c = port.read();
        if (c == '\n') {
            // Strip trailing \r if present
            if (pos > 0 && line[pos-1] == '\r') pos--;
            line[pos] = '\0';
            if (pos > 0) {
                strncpy(buf, line, buf_size - 1);
                buf[buf_size - 1] = '\0';
                pos = 0;
                return true;
            }
            pos = 0;
        } else if (pos < sizeof(line) - 1) {
            line[pos++] = c;
        }
    }
    return false;
}

void loop() {
    char line[128];
    if (readNMEALine(Serial1, line, sizeof(line))) {
        Serial.println(line);
    }
}
```

## Read with Timeout

```cpp
// Read up to max_len bytes, stop on timeout
int serialReadTimeout(HardwareSerial &port, uint8_t *buf, size_t max_len, unsigned long timeout_ms) {
    unsigned long start = millis();
    size_t received = 0;

    while (received < max_len && (millis() - start) < timeout_ms) {
        if (port.available()) {
            buf[received++] = port.read();
        }
    }
    return received;
}

// Read exactly N bytes (block until received or timeout)
bool serialReadExact(HardwareSerial &port, uint8_t *buf, size_t len, unsigned long timeout_ms) {
    unsigned long start = millis();
    size_t received = 0;

    while (received < len) {
        if ((millis() - start) >= timeout_ms) return false;
        if (port.available()) {
            buf[received++] = port.read();
        }
    }
    return true;
}
```

## Binary Packet Protocol (Fingerprint Sensor)

```cpp
// Fingerprint sensor packet: 0xEF01 + 4-byte addr + type + 2-byte len + data + 2-byte checksum

void sendPacket(HardwareSerial &port, uint8_t pkt_type, const uint8_t *data, uint16_t data_len) {
    uint16_t checksum = pkt_type + (data_len + 2 >> 8) + ((data_len + 2) & 0xFF);
    
    // Header
    port.write(0xEF); port.write(0x01);
    // Default address
    port.write(0xFF); port.write(0xFF); port.write(0xFF); port.write(0xFF);
    // Packet type
    port.write(pkt_type);
    // Length (data + 2 for checksum)
    uint16_t pkt_len = data_len + 2;
    port.write((pkt_len >> 8) & 0xFF);
    port.write(pkt_len & 0xFF);
    // Data
    for (uint16_t i = 0; i < data_len; i++) {
        port.write(data[i]);
        checksum += data[i];
    }
    // Checksum
    port.write((checksum >> 8) & 0xFF);
    port.write(checksum & 0xFF);
}

// Read response packet, returns confirmation code byte
int readResponse(HardwareSerial &port, uint8_t *out_buf, uint16_t *out_len, unsigned long timeout_ms) {
    uint8_t hdr[9];
    if (!serialReadExact(port, hdr, 9, timeout_ms)) return -1;
    if (hdr[0] != 0xEF || hdr[1] != 0x01) return -2;  // invalid header
    
    uint16_t pkt_len = ((uint16_t)hdr[7] << 8) | hdr[8];
    if (pkt_len < 2 || pkt_len > 256) return -3;
    
    uint8_t payload[256];
    if (!serialReadExact(port, payload, pkt_len, timeout_ms)) return -4;
    
    uint8_t confirm_code = payload[0];
    if (out_buf && out_len) {
        *out_len = pkt_len - 2;
        memcpy(out_buf, payload + 1, pkt_len - 2);
    }
    return confirm_code;
}

// Send command and get response
int sendCommand(HardwareSerial &port, uint8_t cmd) {
    uint8_t data[1] = { cmd };
    sendPacket(port, 0x01, data, 1);
    return readResponse(port, NULL, NULL, 2000);
}
```

## SoftwareSerial (for boards without enough hardware serials)

```cpp
// NOT needed for ATMega2560 (has 4 hardware serials), but shown for reference
#include <SoftwareSerial.h>
SoftwareSerial gpsSerial(10, 11);  // RX=10, TX=11

void setup() {
    gpsSerial.begin(9600);
}
```

## Best Practices
1. Use hardware serial ports (Serial1-3) instead of SoftwareSerial for reliability
2. Keep Serial (UART0) for USB debug; use Serial1+ for peripherals
3. Always flush incoming data before sending a command (`while(port.available()) port.read();`)
4. Use non-blocking `available()` checks in loop() to avoid stalling
5. Increase baud rate on both sides together (both must match exactly)

## Common Pitfalls
- ❌ TX/RX crossed: ATMega TX pin → sensor RX pin, ATMega RX pin ← sensor TX pin
- ❌ Baud rate mismatch causes garbage characters
- ❌ Reading GPS data in blocking mode while using `delay()` elsewhere — miss data
- ❌ Not draining the buffer before sending a command (stale data in response)

## Related Skills
- `gps-nmea-uart.md` - GPS NMEA sentence parsing
- `fingerprint-sensor-uart.md` - Fingerprint sensor packet protocol
