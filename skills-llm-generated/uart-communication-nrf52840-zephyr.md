---
name: UART Communication - nRF52840 + Zephyr RTOS
description: This skill covers UART communication on nRF52840 using Zephyr RTOS. Covers DTS configuration, polling-based and interrupt-driven UART, line-buffered reading, and binary packet protocols for GPS and fingerprint sensors.
---
# UART Communication - nRF52840 + Zephyr RTOS

## Overview
Zephyr provides a UART driver API for serial communication. The nRF52840 has multiple UARTE peripherals. For simple polling use `uart_poll_in()`; for high-throughput use `uart_irq_callback_set()` or the async API.

## Target Platform
- **MCU:** nRF52840
- **Board:** nRF52840-DK, Arduino Nano 33 BLE
- **Framework:** Zephyr RTOS
- **API:** `zephyr/drivers/uart.h`
- **UART Peripherals:** UARTE0, UARTE1

## Device Tree Configuration

```dts
/* board.overlay */
/ {
    chosen {
        zephyr,console = &uart0;  /* debug output */
    };
};

/* UART1 for GPS at 9600 baud */
&uart1 {
    compatible = "nordic,nrf-uarte";
    status = "okay";
    current-speed = <9600>;
    pinctrl-0 = <&uart1_default>;
    pinctrl-names = "default";
};

&pinctrl {
    uart1_default: uart1_default {
        group1 {
            psels = <NRF_PSEL(UART_TX, 0, 6)>,  /* TX on P0.06 */
                    <NRF_PSEL(UART_RX, 0, 8)>;   /* RX on P0.08 */
        };
    };
};
```

## prj.conf
```ini
CONFIG_UART_ASYNC_API=y    # for async mode
CONFIG_UART_INTERRUPT_DRIVEN=y   # for interrupt-driven mode
CONFIG_SERIAL=y
```

## Polling-Based UART (Simple, Blocking)

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/printk.h>

static const struct device *uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart1));

int uart_setup(void) {
    if (!device_is_ready(uart_dev)) {
        printk("UART device not ready\n");
        return -ENODEV;
    }
    return 0;
}

/* Send a byte */
void uart_send_byte(uint8_t c) {
    uart_poll_out(uart_dev, c);
}

/* Send a buffer */
void uart_send(const uint8_t *buf, size_t len) {
    for (size_t i = 0; i < len; i++) {
        uart_poll_out(uart_dev, buf[i]);
    }
}

/* Send null-terminated string */
void uart_print(const char *str) {
    while (*str) {
        uart_poll_out(uart_dev, *str++);
    }
}

/* Receive with timeout using polling */
int uart_receive_timeout(uint8_t *buf, size_t max_len, int64_t timeout_ms) {
    int64_t deadline = k_uptime_get() + timeout_ms;
    size_t received = 0;

    while (received < max_len && k_uptime_get() < deadline) {
        uint8_t c;
        if (uart_poll_in(uart_dev, &c) == 0) {
            buf[received++] = c;
        }
    }
    return received;
}
```

## Interrupt-Driven UART (Line Buffering for GPS)

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>

#define LINE_BUF_SIZE 256
#define QUEUE_SIZE    4

K_MSGQ_DEFINE(uart_line_queue, LINE_BUF_SIZE, QUEUE_SIZE, 4);

static char rx_buf[LINE_BUF_SIZE];
static int  rx_pos = 0;

static void uart_cb(const struct device *dev, void *user_data) {
    if (!uart_irq_update(dev)) return;

    while (uart_irq_rx_ready(dev)) {
        uint8_t c;
        uart_fifo_read(dev, &c, 1);

        if (c == '\n') {
            if (rx_pos > 0 && rx_buf[rx_pos-1] == '\r') rx_pos--;
            rx_buf[rx_pos] = '\0';
            if (rx_pos > 0) {
                k_msgq_put(&uart_line_queue, rx_buf, K_NO_WAIT);
            }
            rx_pos = 0;
        } else if (rx_pos < LINE_BUF_SIZE - 1) {
            rx_buf[rx_pos++] = c;
        }
    }
}

int uart_irq_init(void) {
    if (!device_is_ready(uart_dev)) return -ENODEV;
    uart_irq_callback_user_data_set(uart_dev, uart_cb, NULL);
    uart_irq_rx_enable(uart_dev);
    return 0;
}

/* Call from main to get next complete line */
bool uart_get_line(char *out, size_t size, k_timeout_t timeout) {
    char buf[LINE_BUF_SIZE];
    if (k_msgq_get(&uart_line_queue, buf, timeout) == 0) {
        strncpy(out, buf, size - 1);
        out[size - 1] = '\0';
        return true;
    }
    return false;
}
```

## Reading Exact N Bytes (Binary Packets)

```c
/* Read exactly len bytes with timeout */
int uart_read_exact(uint8_t *buf, size_t len, int64_t timeout_ms) {
    int64_t deadline = k_uptime_get() + timeout_ms;
    size_t received = 0;

    while (received < len && k_uptime_get() < deadline) {
        uint8_t c;
        if (uart_poll_in(uart_dev, &c) == 0) {
            buf[received++] = c;
        } else {
            k_sleep(K_USEC(100));  /* brief yield */
        }
    }
    return received == len ? 0 : -ETIMEDOUT;
}
```

## GPS Main Loop Example

```c
int main(void) {
    uart_irq_init();

    char line[256];
    while (1) {
        if (uart_get_line(line, sizeof(line), K_MSEC(2000))) {
            printk("GPS: %s\n", line);
        }
    }
}
```

## Best Practices
1. Use interrupt-driven mode for continuously streaming devices (GPS)
2. Use a Zephyr message queue (`K_MSGQ_DEFINE`) to pass data from ISR to main thread
3. `uart_poll_in()` returns 0 on success, -1 if no data — it's non-blocking
4. Call `uart_irq_rx_enable()` only after setting the callback
5. Keep ISR short: just buffer data, parse in main thread

## Common Pitfalls
- ❌ Forgetting `CONFIG_UART_INTERRUPT_DRIVEN=y` in prj.conf for IRQ mode
- ❌ Calling blocking functions (printk, k_sleep) inside UART ISR
- ❌ Wrong baud rate in DTS (`current-speed = <9600>`)
- ❌ Missing pinctrl config causing UART to not respond
- ❌ `uart_poll_in()` with a busy-wait loop consuming 100% CPU

## Related Skills
- `gps-nmea-uart.md` - GPS NMEA sentence parsing
- `fingerprint-sensor-uart.md` - Fingerprint sensor packet protocol
