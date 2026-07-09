---
name: Fingerprint Sensor (R307/AS608) - UART Protocol
description: This skill covers Adafruit optical fingerprint sensor (R307/AS608 compatible) communication via UART. Includes packet structure, commands for enroll/match/delete, LED control, and UART protocol implementation. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# Fingerprint Sensor (R307/AS608) - UART Protocol

## Overview
The Adafruit optical fingerprint sensor uses an UART serial protocol with a structured packet format. The sensor has onboard flash memory that stores fingerprint templates (up to 162 slots).

## Hardware Specs
- **Interface:** UART
- **Default Baud Rate:** 57600 bps (configurable)
- **Supply Voltage:** 3.3–6V
- **Pins:** TX, RX, 3.3V/5V, GND, WAKEUP (optional)
- **Default Address:** 0xFFFFFFFF
- **Default Password:** 0x00000000

## Packet Structure

```
Header:   0xEF 0x01          (2 bytes)
Address:  0xFF 0xFF 0xFF 0xFF (4 bytes, default)
PID:      1 byte             (0x01=command, 0x02=data, 0x07=end_of_data, 0x08=ack)
Length:   2 bytes MSB-first  (data bytes + 2 for checksum)
Data:     N bytes            (command or response)
Checksum: 2 bytes MSB-first  (sum of PID + Length_high + Length_low + all data bytes)
```

## Key Commands
```
0x01 GenImg    - Capture fingerprint image to ImageBuffer
0x02 Img2Tz    - Convert image to template in CharBuffer (slot 1 or 2)
0x03 Match     - Precise match of CharBuffer1 vs CharBuffer2
0x04 Search    - Search database for matching template
0x05 RegModel  - Combine CharBuffer1+2 into template in CharBuffer1
0x06 StoreChar - Store CharBuffer1 template to specified ID slot
0x0C VerifyPwd - Verify password
0x0D SetSysPara- Set system parameter (baud, security level, size)
0x0E ReadSysPara-Read system parameters
0x13 DeleteChar - Delete template at specified ID
0x1A Empty      - Empty (clear) entire database
0x35 LedControl - Control LED (requires AuraControl for some variants)
```

## Confirmation Codes (Response Byte 0)
```
0x00 = OK
0x01 = Packet receive error
0x02 = No finger detected
0x03 = Fail to enroll finger
0x06 = Fail to generate character file
0x07 = Fail to generate template (templates in CharBuffer1/2 don't match)
0x08 = Template upload fail
0x09 = Cannot receive following data packets
0x0A = Template download fail
0x0B = Fail to delete template
0x0C = Fail to clear library
0x0F = Fail to verify password
0x11 = No valid primary image
0x15 = Address code
0x18 = No definition error
0x19 = Invalid register number
0x1A = Register content incorrect
0x1B = Wrong notepad page number
0x1C = Communication port register setting error
```

---

## Packet Builder / Parser

```c
/* C (generic) — used by all three platforms */

#define FP_HEADER_1   0xEF
#define FP_HEADER_2   0x01
#define FP_ADDR_0     0xFF
#define FP_ADDR_1     0xFF
#define FP_ADDR_2     0xFF
#define FP_ADDR_3     0xFF
#define FP_PID_CMD    0x01
#define FP_PID_ACK    0x07

/* Build command packet into buf, returns total length */
int fp_build_packet(uint8_t *buf, const uint8_t *data, uint16_t data_len) {
    uint16_t pkt_len = data_len + 2;  /* data + checksum */
    uint16_t checksum = FP_PID_CMD + (pkt_len >> 8) + (pkt_len & 0xFF);
    for (uint16_t i = 0; i < data_len; i++) checksum += data[i];

    int pos = 0;
    buf[pos++] = FP_HEADER_1;
    buf[pos++] = FP_HEADER_2;
    buf[pos++] = FP_ADDR_0; buf[pos++] = FP_ADDR_1;
    buf[pos++] = FP_ADDR_2; buf[pos++] = FP_ADDR_3;
    buf[pos++] = FP_PID_CMD;
    buf[pos++] = (pkt_len >> 8) & 0xFF;
    buf[pos++] = pkt_len & 0xFF;
    for (uint16_t i = 0; i < data_len; i++) buf[pos++] = data[i];
    buf[pos++] = (checksum >> 8) & 0xFF;
    buf[pos++] = checksum & 0xFF;
    return pos;
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

#define FP_UART    UART_NUM_2
#define FP_TX_PIN  17
#define FP_RX_PIN  16
#define FP_BAUD    57600
#define FP_BUF_SZ  512

void fp_uart_init(void) {
    uart_config_t cfg = {
        .baud_rate  = FP_BAUD,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(FP_UART, FP_BUF_SZ * 2, 0, 0, NULL, 0);
    uart_param_config(FP_UART, &cfg);
    uart_set_pin(FP_UART, FP_TX_PIN, FP_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
}

void fp_send(const uint8_t *data, uint16_t len) {
    uint8_t buf[64];
    int pkt_len = fp_build_packet(buf, data, len);
    uart_write_bytes(FP_UART, (char *)buf, pkt_len);
}

/* Read response, returns confirmation code; -1 on timeout */
int fp_read_response(uint8_t *out_data, uint16_t *out_len, uint32_t timeout_ms) {
    uint8_t hdr[9];
    size_t got = 0;
    TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);
    
    /* Read 9 header bytes */
    while (got < 9 && xTaskGetTickCount() < deadline) {
        int n = uart_read_bytes(FP_UART, hdr + got, 9 - got, pdMS_TO_TICKS(50));
        if (n > 0) got += n;
    }
    if (got < 9) return -1;
    if (hdr[0] != 0xEF || hdr[1] != 0x01) return -2;

    uint16_t pkt_len = ((uint16_t)hdr[7] << 8) | hdr[8];
    if (pkt_len < 2 || pkt_len > 256) return -3;

    uint8_t payload[256];
    got = 0;
    while (got < pkt_len && xTaskGetTickCount() < deadline) {
        int n = uart_read_bytes(FP_UART, payload + got, pkt_len - got, pdMS_TO_TICKS(50));
        if (n > 0) got += n;
    }
    if (got < pkt_len) return -4;

    if (out_data && out_len) {
        *out_len = pkt_len - 2;
        memcpy(out_data, payload + 1, pkt_len - 2);
    }
    return payload[0];  /* confirmation code */
}

int fp_send_cmd(uint8_t cmd) {
    fp_send(&cmd, 1);
    return fp_read_response(NULL, NULL, 2000);
}

/* GenImg: capture fingerprint; returns 0x00 if finger detected */
int fp_gen_image(void) {
    return fp_send_cmd(0x01);
}

/* Img2Tz: convert image to template in CharBuffer slot (1 or 2) */
int fp_img2tz(uint8_t slot) {
    uint8_t cmd[2] = {0x02, slot};
    fp_send(cmd, 2);
    return fp_read_response(NULL, NULL, 2000);
}

/* RegModel: merge CharBuffer1+2 into template */
int fp_reg_model(void) {
    return fp_send_cmd(0x05);
}

/* StoreChar: store CharBuffer1 to ID slot */
int fp_store(uint16_t id) {
    uint8_t cmd[4] = {0x06, 0x01, (id >> 8) & 0xFF, id & 0xFF};
    fp_send(cmd, 4);
    return fp_read_response(NULL, NULL, 2000);
}

/* Search: search all templates, returns matched ID and score */
int fp_search(uint16_t *matched_id, uint16_t *score) {
    uint8_t cmd[5] = {0x04, 0x01, 0x00, 0x00, 0xA3};  /* search CharBuffer1, start=0, count=163 */
    fp_send(cmd, 5);
    uint8_t resp[4];
    uint16_t resp_len;
    int conf = fp_read_response(resp, &resp_len, 2000);
    if (conf == 0x00 && resp_len >= 4) {
        *matched_id = ((uint16_t)resp[0] << 8) | resp[1];
        *score      = ((uint16_t)resp[2] << 8) | resp[3];
    }
    return conf;
}

/* DeleteChar: delete template at ID */
int fp_delete(uint16_t id) {
    uint8_t cmd[5] = {0x0C, (id >> 8) & 0xFF, id & 0xFF, 0x00, 0x01};
    fp_send(cmd, 5);
    return fp_read_response(NULL, NULL, 2000);
}

/* LED control (AuraControl for optical sensors with LED ring) */
int fp_led_on(void) {
    uint8_t cmd[5] = {0x35, 0x03, 0x01, 0x00, 0x00};
    fp_send(cmd, 5);
    return fp_read_response(NULL, NULL, 1000);
}

int fp_led_off(void) {
    uint8_t cmd[5] = {0x35, 0x04, 0x01, 0x00, 0x00};
    fp_send(cmd, 5);
    return fp_read_response(NULL, NULL, 1000);
}

/* Enroll procedure: place finger twice, store at ID */
void fp_enroll(uint16_t id) {
    printf("Place finger...\n");
    while (fp_gen_image() != 0x00) vTaskDelay(pdMS_TO_TICKS(100));
    fp_img2tz(1);

    printf("Remove finger...\n");
    while (fp_gen_image() != 0x02) vTaskDelay(pdMS_TO_TICKS(100));
    vTaskDelay(pdMS_TO_TICKS(500));

    printf("Place same finger again...\n");
    while (fp_gen_image() != 0x00) vTaskDelay(pdMS_TO_TICKS(100));
    fp_img2tz(2);

    if (fp_reg_model() != 0x00) {
        printf("Enrollment failed: fingerprints don't match\n");
        return;
    }
    if (fp_store(id) == 0x00) {
        printf("Enrolled at ID %d\n", id);
    }
}

/* Match loop: scan and identify */
void fp_match_loop(void) {
    uint16_t id, score;
    if (fp_gen_image() != 0x00) return;
    if (fp_img2tz(1) != 0x00) return;
    int conf = fp_search(&id, &score);
    if (conf == 0x00) {
        printf("Match: ID=%d, confidence=%d\n", id, score);
    } else {
        printf("No match\n");
    }
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Adafruit_Fingerprint.h>

/* Use Serial2 for fingerprint (TX=16, RX=17 on Mega) */
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&Serial2);

void setup() {
    Serial.begin(115200);
    finger.begin(57600);

    if (!finger.verifyPassword()) {
        Serial.println("Fingerprint sensor not found");
        while (1);
    }
    Serial.println("Fingerprint sensor ready");
}

/* LED control */
void led_on()  { finger.LEDcontrol(FINGERPRINT_LED_ON,  0, FINGERPRINT_LED_BLUE, 0); }
void led_off() { finger.LEDcontrol(FINGERPRINT_LED_OFF, 0, FINGERPRINT_LED_BLUE, 0); }

/* Enroll at given ID */
void enrollFinger(uint16_t id) {
    Serial.println("Place finger...");
    while (finger.getImage() != FINGERPRINT_OK) delay(100);
    finger.image2Tz(1);

    Serial.println("Remove finger...");
    while (finger.getImage() != FINGERPRINT_NOFINGER) delay(100);
    delay(500);

    Serial.println("Place same finger again...");
    while (finger.getImage() != FINGERPRINT_OK) delay(100);
    finger.image2Tz(2);

    if (finger.createModel() != FINGERPRINT_OK) {
        Serial.println("Enroll failed");
        return;
    }
    if (finger.storeModel(id) == FINGERPRINT_OK) {
        Serial.print("Stored at ID "); Serial.println(id);
    }
}

/* Match and return ID, -1 if not found */
int matchFinger() {
    if (finger.getImage() != FINGERPRINT_OK) return -1;
    if (finger.image2Tz() != FINGERPRINT_OK) return -1;
    if (finger.fingerSearch() != FINGERPRINT_OK) return -1;
    return finger.fingerID;
}

/* Delete a template */
void deleteFinger(uint16_t id) {
    if (finger.deleteModel(id) == FINGERPRINT_OK) {
        Serial.print("Deleted ID "); Serial.println(id);
    }
}

/* UART Protocol: send command packet, read response */
void uartProtocolExample(uint8_t cmd_id) {
    uint8_t cmd[1] = { cmd_id };
    uint8_t buf[64];
    int len = fp_build_packet(buf, cmd, 1);

    /* Clear buffer */
    while (Serial2.available()) Serial2.read();
    /* Send */
    Serial2.write(buf, len);
    delay(100);

    /* Read response header (9 bytes) */
    uint8_t resp[32];
    int received = 0;
    unsigned long t = millis();
    while (received < 9 && millis() - t < 2000) {
        if (Serial2.available()) resp[received++] = Serial2.read();
    }
    Serial.print("command=0x"); Serial.print(cmd_id, HEX);
    Serial.print(", response=0x"); Serial.println(received >= 9 ? resp[9] : 0xFF, HEX);
}

void loop() {
    int id = matchFinger();
    if (id >= 0) {
        Serial.print("Matched ID="); Serial.print(id);
        Serial.print(", confidence="); Serial.println(finger.confidence);
    }
    delay(500);
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* Use UART interrupt-driven from uart-communication-nrf52840-zephyr.md */
/* Then use fp_build_packet + uart_send + uart_read_exact pattern */

#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>

static const struct device *fp_uart = DEVICE_DT_GET(DT_NODELABEL(uart1));

void fp_uart_send(const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) uart_poll_out(fp_uart, data[i]);
}

int fp_uart_recv(uint8_t *buf, size_t len, int timeout_ms) {
    int64_t deadline = k_uptime_get() + timeout_ms;
    size_t n = 0;
    while (n < len && k_uptime_get() < deadline) {
        uint8_t c;
        if (uart_poll_in(fp_uart, &c) == 0) buf[n++] = c;
        else k_sleep(K_USEC(200));
    }
    return n == len ? 0 : -ETIMEDOUT;
}

int zephyr_fp_send_cmd(uint8_t cmd) {
    uint8_t pkt[16];
    int pkt_len = fp_build_packet(pkt, &cmd, 1);
    fp_uart_send(pkt, pkt_len);

    uint8_t hdr[9], payload[32];
    if (fp_uart_recv(hdr, 9, 2000) != 0) return -1;
    uint16_t pkt_data_len = ((uint16_t)hdr[7] << 8) | hdr[8];
    if (fp_uart_recv(payload, pkt_data_len, 1000) != 0) return -1;
    return payload[0];
}

/* LED blink example */
int main(void) {
    while (1) {
        fp_led_on();   /* uses zephyr_fp_send_cmd(0x35 ...) variant */
        k_msleep(1000);
        fp_led_off();
        k_msleep(1000);
    }
}
```

## Best Practices
1. Use the Adafruit Fingerprint library on Arduino — it wraps the full protocol
2. Flush the RX buffer before sending a command (stale data corrupts response)
3. Always check the confirmation code before acting on results
4. Enroll each user twice (two images, merged into one template) for better accuracy
5. LED commands use `AuraControl` (0x35) — some older sensors use different commands

## Common Pitfalls
- ❌ Wrong baud rate (default 57600, not 9600)
- ❌ TX/RX swapped: sensor TX → MCU RX, sensor RX ← MCU TX
- ❌ Not waiting for finger removal between enroll steps
- ❌ Ignoring confirmation code 0x02 (no finger) — should retry in a loop
- ❌ Wrong slot number in Img2Tz (1 for first scan, 2 for second)

## Related Skills
- `uart-communication-esp32-esp-idf.md` - ESP32 UART
- `uart-communication-atmega2560-arduino.md` - Arduino UART
- `relay-gpio-control.md` - Relay for door lock on auth
