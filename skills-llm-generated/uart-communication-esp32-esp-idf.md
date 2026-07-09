---
name: UART Communication - ESP32 + ESP-IDF
description: This skill covers UART (Universal Asynchronous Receiver/Transmitter) communication on ESP32 using ESP-IDF framework. Includes configuration, interrupt-driven and polling-based reading, and UART event handling for GPS, fingerprint sensors, and other serial peripherals.
---
# UART Communication - ESP32 + ESP-IDF

## Overview
UART is a serial communication protocol widely used for GPS modules, fingerprint sensors, Bluetooth modules, and debug output. ESP32 has 3 hardware UART controllers (UART0, UART1, UART2).

## Target Platform
- **MCU:** ESP32
- **Framework:** ESP-IDF
- **API:** `driver/uart.h`
- **UART Ports:** UART0 (debug, USB), UART1 (general), UART2 (general)

## Key Concepts
- **Baud Rate:** Data rate in bits per second (e.g., 9600, 57600, 115200)
- **8N1:** 8 data bits, no parity, 1 stop bit (most common)
- **Ring Buffer:** ESP-IDF uses ring buffers for RX FIFO overflow protection
- **Event Queue:** Asynchronous UART events (data received, break, error)
- **TX/RX Pins:** Assignable to any GPIO on ESP32

## UART Pin Defaults
```
UART0: TX=GPIO1,  RX=GPIO3  (USB/debug)
UART1: TX=GPIO10, RX=GPIO9  (configurable)
UART2: TX=GPIO17, RX=GPIO16 (configurable)
```

## Basic UART Setup

```c
#include <stdio.h>
#include <string.h>
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "UART";

#define UART_PORT       UART_NUM_1
#define UART_BAUD_RATE  9600
#define UART_TX_PIN     17
#define UART_RX_PIN     16
#define UART_BUF_SIZE   1024

esp_err_t uart_init(void)
{
    uart_config_t uart_config = {
        .baud_rate  = UART_BAUD_RATE,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    ESP_ERROR_CHECK(uart_driver_install(UART_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_PORT, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_PORT, UART_TX_PIN, UART_RX_PIN,
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    return ESP_OK;
}

// Send data over UART
void uart_send(const char *data, size_t len)
{
    uart_write_bytes(UART_PORT, data, len);
}

// Read with timeout (returns bytes read, 0 on timeout)
int uart_receive(uint8_t *buf, size_t max_len, uint32_t timeout_ms)
{
    return uart_read_bytes(UART_PORT, buf, max_len, pdMS_TO_TICKS(timeout_ms));
}
```

## Reading NMEA Lines from GPS (Line-by-Line)

```c
#define GPS_UART_PORT   UART_NUM_1
#define GPS_BAUD        9600
#define GPS_TX_PIN      17
#define GPS_RX_PIN      16
#define GPS_BUF_SIZE    512

static char line_buf[256];
static int  line_pos = 0;

// Read one complete NMEA line ending with \r\n
bool uart_read_line(char *out_buf, size_t buf_size, uint32_t timeout_ms)
{
    uint8_t ch;
    TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);

    while (xTaskGetTickCount() < deadline) {
        int len = uart_read_bytes(GPS_UART_PORT, &ch, 1, pdMS_TO_TICKS(10));
        if (len <= 0) continue;

        if (ch == '\n') {
            if (line_pos > 0 && line_buf[line_pos - 1] == '\r') {
                line_pos--;
            }
            line_buf[line_pos] = '\0';
            if (line_pos > 0) {
                strncpy(out_buf, line_buf, buf_size - 1);
                out_buf[buf_size - 1] = '\0';
                line_pos = 0;
                return true;
            }
            line_pos = 0;
        } else if (line_pos < (int)sizeof(line_buf) - 1) {
            line_buf[line_pos++] = ch;
        }
    }
    return false;
}

void gps_task(void *arg)
{
    char line[256];

    uart_config_t cfg = {
        .baud_rate  = GPS_BAUD,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(GPS_UART_PORT, GPS_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(GPS_UART_PORT, &cfg);
    uart_set_pin(GPS_UART_PORT, GPS_TX_PIN, GPS_RX_PIN,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    while (1) {
        if (uart_read_line(line, sizeof(line), 1000)) {
            printf("GPS: %s\n", line);
        }
    }
}
```

## Event-Queue Driven Reading (for high-throughput)

```c
#define UART_EVENT_QUEUE_SIZE 10

static QueueHandle_t uart_event_queue;

void uart_event_task(void *arg)
{
    uart_event_t event;
    uint8_t buf[UART_BUF_SIZE];

    while (1) {
        if (xQueueReceive(uart_event_queue, &event, portMAX_DELAY)) {
            switch (event.type) {
            case UART_DATA:
                {
                    int len = uart_read_bytes(UART_PORT, buf, event.size, pdMS_TO_TICKS(100));
                    buf[len] = '\0';
                    ESP_LOGI(TAG, "RX %d bytes: %s", len, buf);
                }
                break;
            case UART_FIFO_OVF:
                ESP_LOGW(TAG, "FIFO overflow");
                uart_flush_input(UART_PORT);
                xQueueReset(uart_event_queue);
                break;
            case UART_BUFFER_FULL:
                ESP_LOGW(TAG, "Ring buffer full");
                uart_flush_input(UART_PORT);
                xQueueReset(uart_event_queue);
                break;
            default:
                break;
            }
        }
    }
}

esp_err_t uart_event_init(void)
{
    uart_config_t cfg = {
        .baud_rate  = 115200,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART_PORT, UART_BUF_SIZE * 2, UART_BUF_SIZE * 2,
                        UART_EVENT_QUEUE_SIZE, &uart_event_queue, 0);
    uart_param_config(UART_PORT, &cfg);
    uart_set_pin(UART_PORT, UART_TX_PIN, UART_RX_PIN,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    xTaskCreate(uart_event_task, "uart_events", 4096, NULL, 5, NULL);
    return ESP_OK;
}
```

## Binary Packet Protocol (e.g., Fingerprint Sensor)

```c
// Read exact N bytes with timeout
int uart_read_exact(uint8_t *buf, size_t len, uint32_t timeout_ms)
{
    size_t received = 0;
    TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);

    while (received < len && xTaskGetTickCount() < deadline) {
        int got = uart_read_bytes(UART_PORT, buf + received, len - received,
                                  pdMS_TO_TICKS(10));
        if (got > 0) received += got;
    }
    return received;
}

// Send raw packet bytes
void uart_send_packet(const uint8_t *pkt, size_t len)
{
    uart_write_bytes(UART_PORT, (const char *)pkt, len);
}
```

## Best Practices
1. Use UART1 or UART2 for peripherals; keep UART0 for debug output
2. Set buffer size to at least 2× the largest expected message
3. Always handle FIFO overflow events to prevent data loss
4. For sensors sending continuous data, use a dedicated FreeRTOS task
5. Use `uart_flush_input()` to discard stale data before reading a command response

## Common Pitfalls
- ❌ TX and RX pins swapped (connect ESP TX→sensor RX, ESP RX←sensor TX)
- ❌ Baud rate mismatch (sensor defaults differ: GPS=9600, fingerprint=57600)
- ❌ Blocking the main loop with uart_read_bytes long timeout
- ❌ Not flushing old data before sending a command

## Related Skills
- `gps-nmea-uart.md` - GPS NMEA sentence parsing
- `fingerprint-sensor-uart.md` - Fingerprint sensor packet protocol
