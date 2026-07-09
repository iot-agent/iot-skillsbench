---
name: Speaker and Buzzer Output
description: This skill covers active and passive buzzer/speaker output. Active buzzers use a GPIO toggle; passive buzzers use PWM to generate tones. Includes toggle patterns, tone generation, alert sequences. Covers ESP32+ESP-IDF (LEDC), ATMega2560+Arduino (tone()), and nRF52840+Zephyr (PWM API).
---
# Speaker and Buzzer Output

## Overview
Two types of buzzers are common in IoT:
- **Active buzzer**: Has internal oscillator; GPIO HIGH = sound. Simple but single frequency.
- **Passive buzzer**: No oscillator; requires PWM to produce sound. Can generate any frequency.

A small speaker connected through an amplifier (or directly with a series resistor) behaves like a passive buzzer.

## Key Concepts
- **Active buzzer toggle**: HIGH=on, LOW=off; no PWM needed
- **Passive buzzer tone**: PWM at desired frequency, 50% duty cycle
- **Alert pattern**: Periodic blink/beep with a non-blocking state machine
- **Relay-based speaker**: If the speaker is driven through a relay, toggle the relay

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Arduino.h>

#define BUZZER_PIN   8    /* connect buzzer/speaker here */

/* Active buzzer: simple on/off */
void buzzer_on()  { digitalWrite(BUZZER_PIN, HIGH); }
void buzzer_off() { digitalWrite(BUZZER_PIN, LOW);  }

/* Passive buzzer: generate tone using Arduino tone() */
void play_tone(uint16_t freq_hz, uint16_t duration_ms) {
    tone(BUZZER_PIN, freq_hz, duration_ms);
    delay(duration_ms);
    noTone(BUZZER_PIN);
}

/* Speaker toggle: on for 1s, off for 1s */
void setup() {
    Serial.begin(115200);
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);  /* start OFF */
}

void loop() {
    buzzer_on();
    Serial.println("speaker on");
    delay(1000);
    buzzer_off();
    Serial.println("speaker off");
    delay(1000);
}
```

### Non-Blocking Alert Beeper (Wearable / Alert System)
```cpp
#define BUZZER_PIN    8
#define BEEP_ON_MS   200
#define BEEP_OFF_MS  800

bool alert_active     = false;
bool buzzer_state     = false;
unsigned long buzzer_last_change = 0;

void buzzer_init() {
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
}

/* Call from loop() — non-blocking */
void buzzer_update() {
    if (!alert_active) {
        if (buzzer_state) { digitalWrite(BUZZER_PIN, LOW); buzzer_state = false; }
        return;
    }

    unsigned long now = millis();
    if (buzzer_state && (now - buzzer_last_change >= BEEP_ON_MS)) {
        digitalWrite(BUZZER_PIN, LOW);
        buzzer_state = false;
        buzzer_last_change = now;
    } else if (!buzzer_state && (now - buzzer_last_change >= BEEP_OFF_MS)) {
        digitalWrite(BUZZER_PIN, HIGH);
        buzzer_state = true;
        buzzer_last_change = now;
    }
}

void set_alert(bool active) { alert_active = active; }

/* tone() usage for specific frequencies */
void alarm_sequence() {
    for (int i = 0; i < 3; i++) {
        play_tone(1000, 200);
        delay(100);
        play_tone(800, 200);
        delay(100);
    }
}
```

### PWM Frequency Control (Passive Buzzer)
```cpp
/* Generate 1kHz square wave manually */
void tone_manual(uint8_t pin, uint32_t freq, uint32_t duration_ms) {
    uint32_t half_period_us = 500000 / freq;  /* half period in microseconds */
    uint32_t cycles = (uint32_t)((uint64_t)duration_ms * 1000 / (half_period_us * 2));
    for (uint32_t i = 0; i < cycles; i++) {
        digitalWrite(pin, HIGH); delayMicroseconds(half_period_us);
        digitalWrite(pin, LOW);  delayMicroseconds(half_period_us);
    }
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include "driver/ledc.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>

#define BUZZER_PIN    GPIO_NUM_26
#define LEDC_CHANNEL  LEDC_CHANNEL_0
#define LEDC_TIMER    LEDC_TIMER_0
#define LEDC_MODE     LEDC_LOW_SPEED_MODE
#define LEDC_FREQ_HZ  1000   /* 1kHz */
#define LEDC_DUTY     2048   /* 50% duty for 13-bit resolution (4096/2) */

/* Passive buzzer via LEDC (PWM) */
void buzzer_pwm_init(void) {
    ledc_timer_config_t timer_cfg = {
        .speed_mode       = LEDC_MODE,
        .timer_num        = LEDC_TIMER,
        .duty_resolution  = LEDC_TIMER_13_BIT,
        .freq_hz          = LEDC_FREQ_HZ,
        .clk_cfg          = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_cfg);

    ledc_channel_config_t channel_cfg = {
        .channel    = LEDC_CHANNEL,
        .duty       = 0,
        .gpio_num   = BUZZER_PIN,
        .speed_mode = LEDC_MODE,
        .timer_sel  = LEDC_TIMER,
    };
    ledc_channel_config(&channel_cfg);
}

void buzzer_pwm_on(uint32_t freq_hz) {
    ledc_set_freq(LEDC_MODE, LEDC_TIMER, freq_hz);
    ledc_set_duty(LEDC_MODE, LEDC_CHANNEL, LEDC_DUTY);
    ledc_update_duty(LEDC_MODE, LEDC_CHANNEL);
}

void buzzer_pwm_off(void) {
    ledc_set_duty(LEDC_MODE, LEDC_CHANNEL, 0);
    ledc_update_duty(LEDC_MODE, LEDC_CHANNEL);
}

/* Active buzzer via GPIO toggle */
void buzzer_gpio_init(void) {
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << BUZZER_PIN),
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
    gpio_set_level(BUZZER_PIN, 0);
}

void buzzer_gpio_on(void)  { gpio_set_level(BUZZER_PIN, 1); }
void buzzer_gpio_off(void) { gpio_set_level(BUZZER_PIN, 0); }

/* Speaker toggle task */
void speaker_toggle_task(void *arg) {
    buzzer_gpio_init();
    while (1) {
        buzzer_gpio_on();
        printf("speaker on\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
        buzzer_gpio_off();
        printf("speaker off\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* Alert task with non-blocking beep pattern */
void alert_task(void *arg) {
    buzzer_pwm_init();
    bool alert = false;
    bool beeping = false;
    uint32_t last_toggle = 0;
    const uint32_t ON_MS = 200, OFF_MS = 800;

    while (1) {
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;

        if (alert) {
            if (beeping && (now - last_toggle >= ON_MS)) {
                buzzer_pwm_off(); beeping = false; last_toggle = now;
            } else if (!beeping && (now - last_toggle >= OFF_MS)) {
                buzzer_pwm_on(1000); beeping = true; last_toggle = now;
            }
        } else if (beeping) {
            buzzer_pwm_off(); beeping = false;
        }

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* prj.conf: CONFIG_PWM=y */
#include <zephyr/kernel.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/printk.h>

/* For passive buzzer: use PWM API */
static const struct pwm_dt_spec buzzer_pwm = PWM_DT_SPEC_GET(DT_ALIAS(buzzer_pwm));

/* board.overlay:
   / { aliases { buzzer-pwm = &pwm0; }; };
   &pwm0 { status = "okay"; };
   (pin defined in pinctrl)
*/

void buzzer_pwm_on(uint32_t freq_hz) {
    uint32_t period_ns = 1000000000 / freq_hz;
    pwm_set_dt(&buzzer_pwm, period_ns, period_ns / 2);  /* 50% duty */
}

void buzzer_pwm_off(void) {
    pwm_set_dt(&buzzer_pwm, 1000, 0);  /* duty = 0 = no output */
}

/* For active buzzer: use GPIO */
static const struct gpio_dt_spec buzzer_gpio = GPIO_DT_SPEC_GET(DT_ALIAS(buzzer), gpios);

void buzzer_gpio_init(void) {
    gpio_pin_configure_dt(&buzzer_gpio, GPIO_OUTPUT_INACTIVE);
}

void buzzer_on(void)  { gpio_pin_set_dt(&buzzer_gpio, 1); }
void buzzer_off(void) { gpio_pin_set_dt(&buzzer_gpio, 0); }

int main(void) {
    buzzer_gpio_init();
    while (1) {
        buzzer_on();
        printk("speaker on\n");
        k_msleep(1000);
        buzzer_off();
        printk("speaker off\n");
        k_msleep(1000);
    }
}
```

## Best Practices
1. For active buzzer: use GPIO; for passive buzzer/speaker: use PWM at desired frequency
2. Keep buzzer/speaker alerts non-blocking — use a timer or state machine, not `delay()`
3. PWM at 1000–2000 Hz is the most audible range for buzzers
4. Series resistor (100–470Ω) protects GPIO and limits buzzer volume
5. Active buzzers draw 30–100mA — don't drive directly from 3.3V GPIO; use a transistor

## Common Pitfalls
- ❌ Mixing active and passive buzzer wiring (active buzzer with PWM produces wrong sound)
- ❌ Using `delay()` in alert patterns (blocks the main loop)
- ❌ Connecting buzzer directly to GPIO without current limiting (exceeds GPIO drive capability)
- ❌ Forgetting to call `noTone()` after `tone()` on Arduino (tone continues indefinitely)

## Related Skills
- `pwm-control-esp32-esp-idf.md` - ESP32 LEDC PWM setup
- `relay-gpio-control.md` - Relay for high-power speaker
- `gpio-interrupts-esp32-esp-idf.md` - Non-blocking GPIO patterns
