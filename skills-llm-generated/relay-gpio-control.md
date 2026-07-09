---
name: Relay GPIO Control
description: This skill covers controlling a relay module via GPIO. Includes active-high and active-low wiring, safe activation patterns, timed unlock sequences, and relay state for access control systems. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# Relay GPIO Control

## Overview
A relay is an electrically-operated switch used to control high-voltage/high-current loads from a low-voltage MCU GPIO. Most IoT relay modules use active-low control (LOW = relay ON) with an optocoupler for isolation.

## Hardware Specs
- **Control Signal:** GPIO (3.3V or 5V)
- **Control Logic:**
  - Active-HIGH relay (some modules): HIGH = relay ON
  - Active-LOW relay (most modules with optocoupler): LOW = relay ON
- **Load:** Typically rated for 10A 250VAC / 10A 30VDC
- **Contacts:** COM (common), NO (normally open), NC (normally closed)

## Relay Wiring
```
NO  — load is disconnected when relay OFF, connected when ON
NC  — load is connected when relay OFF, disconnected when ON
COM — always connected to load supply (one side)
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Arduino.h>

#define RELAY_PIN   8

/* For active-LOW relay module (most common with optocoupler) */
#define RELAY_ON    LOW
#define RELAY_OFF   HIGH

void setup() {
    Serial.begin(115200);
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, RELAY_OFF);  /* Start in OFF state */
}

/* Simple toggle */
void relay_activate(bool on) {
    digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF);
}

/* Timed unlock: activate relay for N milliseconds, then deactivate */
void relay_unlock(unsigned long duration_ms) {
    relay_activate(true);
    delay(duration_ms);
    relay_activate(false);
}

/* Speaker toggle: turn on/off every second */
void loop_speaker_toggle() {
    relay_activate(true);
    Serial.println("speaker on");
    delay(1000);
    relay_activate(false);
    Serial.println("speaker off");
    delay(1000);
}

/* Door lock access control */
void loop_access_control() {
    /* Assume fingerprint/NFC returns auth result */
    bool authenticated = true;  /* replace with actual check */

    if (authenticated) {
        Serial.println("Access Granted");
        relay_unlock(5000);  /* unlock for 5 seconds */
    } else {
        Serial.println("Access Denied");
    }
}

void loop() {
    loop_speaker_toggle();
}
```

### Multiple Relays
```cpp
#define RELAY1_PIN  8
#define RELAY2_PIN  9

void setup() {
    pinMode(RELAY1_PIN, OUTPUT); digitalWrite(RELAY1_PIN, HIGH);  /* off */
    pinMode(RELAY2_PIN, OUTPUT); digitalWrite(RELAY2_PIN, HIGH);  /* off */
}

/* Activate relay N (1-indexed) */
void relay_set(int relay_num, bool on) {
    int pin = (relay_num == 1) ? RELAY1_PIN : RELAY2_PIN;
    digitalWrite(pin, on ? LOW : HIGH);  /* active-LOW */
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define RELAY_PIN   GPIO_NUM_26
#define RELAY_ON    0   /* active-LOW */
#define RELAY_OFF   1

void relay_init(void) {
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << RELAY_PIN),
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
    gpio_set_level(RELAY_PIN, RELAY_OFF);  /* safe default = OFF */
}

void relay_set(bool on) {
    gpio_set_level(RELAY_PIN, on ? RELAY_ON : RELAY_OFF);
}

/* Timed unlock: activate for duration_ms then deactivate */
void relay_timed_unlock(uint32_t duration_ms) {
    relay_set(true);
    vTaskDelay(pdMS_TO_TICKS(duration_ms));
    relay_set(false);
}

/* Speaker toggle task */
void relay_toggle_task(void *arg) {
    relay_init();
    while (1) {
        relay_set(true);
        printf("speaker on\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
        relay_set(false);
        printf("speaker off\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* Access control task (used with fingerprint or NFC) */
void relay_access_task(void *arg) {
    relay_init();
    /* extern bool auth_result; — set by fingerprint/NFC task */
    while (1) {
        /* In real use, receive auth result from a queue */
        bool auth = false;  /* placeholder */
        if (auth) {
            printf("unlock=yes\n");
            relay_timed_unlock(5000);
        } else {
            printf("unlock=no\n");
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>

#define RELAY_NODE DT_ALIAS(relay0)
static const struct gpio_dt_spec relay = GPIO_DT_SPEC_GET(RELAY_NODE, gpios);

/* DTS alias: add to board.overlay
   / { aliases { relay0 = &relay_gpio; };
       relay_gpio: relay_gpio { gpios = <&gpio0 26 GPIO_ACTIVE_LOW>; }; };
*/

int relay_init(void) {
    if (!gpio_is_ready_dt(&relay)) return -ENODEV;
    return gpio_pin_configure_dt(&relay, GPIO_OUTPUT_INACTIVE);
}

void relay_set(bool on) {
    /* GPIO_ACTIVE_LOW in DTS means gpio_pin_set(1) = physical LOW = relay ON */
    gpio_pin_set_dt(&relay, on ? 1 : 0);
}

void relay_timed_unlock(uint32_t ms) {
    relay_set(true);
    k_msleep(ms);
    relay_set(false);
}

int main(void) {
    relay_init();

    /* Toggle every second */
    while (1) {
        relay_set(true);
        printk("relay ON\n");
        k_msleep(1000);
        relay_set(false);
        printk("relay OFF\n");
        k_msleep(1000);
    }
}
```

## Best Practices
1. Always initialize relay GPIO to OFF state immediately in setup()
2. Use active-LOW logic for safety (relay turns OFF on MCU reset/crash)
3. For timed locks, prefer non-blocking patterns with a timeout timer
4. Never exceed relay contact ratings (current, voltage)
5. Add a flyback diode across the relay coil to protect the MCU from voltage spikes (some modules include this)

## Common Pitfalls
- ❌ Forgetting that most relay modules are active-LOW: HIGH = OFF, LOW = ON
- ❌ Not initializing to OFF state (relay may activate briefly at boot)
- ❌ Using delay() while relay is active — blocks other system tasks
- ❌ Driving relay coil directly from MCU GPIO without transistor/optocoupler (exceeds GPIO current limit)

## Related Skills
- `fingerprint-sensor-uart.md` - Fingerprint auth to control relay
- `pn532-nfc-rfid.md` - NFC auth to control relay
- `speaker-buzzer-output.md` - Speaker via relay or PWM
