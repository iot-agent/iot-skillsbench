---
name: GPS Module (PA1616S) - NMEA Parsing via UART
description: This skill covers the Adafruit PA1616S Ultimate GPS module (MTK MT3339 chip). Includes UART setup at 9600 baud, reading raw NMEA sentences, filtering by sentence type ($GPGGA, $GPRMC), parsing fix status, latitude/longitude, and timestamp. Covers ESP32+ESP-IDF, ATMega2560+Arduino, and nRF52840+Zephyr.
---
# GPS Module (PA1616S) - NMEA Parsing via UART

## Overview
The PA1616S (Adafruit Ultimate GPS) outputs NMEA 0183 sentences at 9600 baud by default. NMEA sentences are ASCII strings starting with `$` and ending with `*HH\r\n` (HH = 2-digit hex checksum).

## Hardware Specs
- **Interface:** UART (3.3V TTL)
- **Default Baud Rate:** 9600 bps, 8N1
- **Update Rate:** 1 Hz (default), up to 10 Hz
- **Fix Time:** Cold start ~30–60s, hot start ~1s
- **Power:** 3.3V, ~25mA active

## NMEA Sentence Types

### $GPGGA (Global Positioning System Fix Data)
```
$GPGGA,HHMMSS.ss,DDMM.MMMM,N,DDDMM.MMMM,W,FS,NoSV,HDOP,Alt,M,AltRef,M,DifAge,DifSta*cs<CR><LF>
Fields:
  [0] $GPGGA
  [1] UTC time: HHMMSS.ss
  [2] Latitude: DDMM.MMMM
  [3] N/S indicator
  [4] Longitude: DDDMM.MMMM
  [5] E/W indicator
  [6] Fix indicator: 0=invalid, 1=GPS fix, 2=DGPS fix
  [7] Satellites used
  [8] HDOP
  [9] MSL altitude
  [10] Units (M)
```

### $GPRMC (Recommended Minimum Specific GPS Data)
```
$GPRMC,HHMMSS.ss,A,DDMM.MMMM,N,DDDMM.MMMM,W,spd,crs,DDMMYY,,,*cs<CR><LF>
Fields:
  [0] $GPRMC
  [1] UTC time: HHMMSS.ss
  [2] Status: A=Active (fix), V=Void (no fix)
  [3] Latitude: DDMM.MMMM
  [4] N/S
  [5] Longitude: DDDMM.MMMM
  [6] E/W
  [7] Speed over ground (knots)
  [8] Course over ground (degrees)
  [9] Date: DDMMYY
```

## NMEA Parsing Utilities

### Split CSV fields
```c
/* Split sentence into tokens, return count. Modifies buf in-place. */
int nmea_split(char *buf, char *fields[], int max_fields) {
    int count = 0;
    fields[count++] = buf;
    for (char *p = buf; *p && count < max_fields; p++) {
        if (*p == ',') {
            *p = '\0';
            fields[count++] = p + 1;
        }
        /* strip checksum */
        if (*p == '*') { *p = '\0'; break; }
    }
    return count;
}

/* Convert NMEA DDMM.MMMM to decimal degrees */
double nmea_to_degrees(const char *field, char dir) {
    if (!field || field[0] == '\0') return 0.0;
    double raw = atof(field);
    int deg = (int)(raw / 100);
    double min = raw - (deg * 100);
    double result = deg + min / 60.0;
    if (dir == 'S' || dir == 'W') result = -result;
    return result;
}
```

---

## ESP32 + ESP-IDF Implementation

```c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define GPS_UART    UART_NUM_1
#define GPS_TX_PIN  17
#define GPS_RX_PIN  16
#define GPS_BUF     512

static void gps_init(void) {
    uart_config_t cfg = {
        .baud_rate  = 9600,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(GPS_UART, GPS_BUF * 2, 0, 0, NULL, 0);
    uart_param_config(GPS_UART, &cfg);
    uart_set_pin(GPS_UART, GPS_TX_PIN, GPS_RX_PIN,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
}

/* Read one NMEA line into buf; returns true on success */
static char line[256];
static int  line_pos = 0;

bool gps_read_line(char *out, size_t out_size, uint32_t timeout_ms) {
    uint8_t ch;
    TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);
    while (xTaskGetTickCount() < deadline) {
        if (uart_read_bytes(GPS_UART, &ch, 1, pdMS_TO_TICKS(10)) <= 0) continue;
        if (ch == '\n') {
            if (line_pos > 0 && line[line_pos-1] == '\r') line_pos--;
            line[line_pos] = '\0';
            if (line_pos > 0 && line[0] == '$') {
                strncpy(out, line, out_size - 1);
                out[out_size - 1] = '\0';
                line_pos = 0;
                return true;
            }
            line_pos = 0;
        } else if (line_pos < (int)sizeof(line) - 1) {
            line[line_pos++] = ch;
        }
    }
    return false;
}

/* Task: forward all NMEA to console */
void gps_task_raw(void *arg) {
    gps_init();
    char buf[256];
    while (1) {
        if (gps_read_line(buf, sizeof(buf), 2000)) {
            printf("%s\n", buf);
        }
    }
}

/* Task: filter only $GPGGA sentences */
void gps_task_filter(void *arg) {
    gps_init();
    char buf[256];
    while (1) {
        if (gps_read_line(buf, sizeof(buf), 2000)) {
            if (strncmp(buf, "$GPGGA", 6) == 0) {
                printf("%s\n", buf);
            }
        }
    }
}

/* Parse fix status from any NMEA sentence */
void gps_task_fix(void *arg) {
    gps_init();
    char buf[256];
    char *fields[20];
    while (1) {
        if (gps_read_line(buf, sizeof(buf), 2000)) {
            int n = nmea_split(buf, fields, 20);
            /* $GPGGA: field[6]=fix indicator (0=invalid) */
            if (strncmp(buf, "$GPGGA", 6) == 0 && n >= 7) {
                int fix = atoi(fields[6]);
                printf("%s\n", fix > 0 ? "fix valid" : "fix invalid");
            }
        }
    }
}

/* Parse lat/lon from $GPGGA */
void gps_task_latlon(void *arg) {
    gps_init();
    char buf[256];
    char *fields[20];
    while (1) {
        if (gps_read_line(buf, sizeof(buf), 2000)) {
            if (strncmp(buf, "$GPGGA", 6) != 0) continue;
            int n = nmea_split(buf, fields, 20);
            if (n < 7 || atoi(fields[6]) == 0) continue;  // no fix
            double lat = nmea_to_degrees(fields[2], fields[3][0]);
            double lon = nmea_to_degrees(fields[4], fields[5][0]);
            printf("Lat=%.6f, Lon=%.6f\n", lat, lon);
        }
    }
}
```

---

## ATMega2560 + Arduino Implementation

```cpp
#include <Arduino.h>

/* GPS on Serial1 (pins TX=18, RX=19 on Mega) */
void setup() {
    Serial.begin(115200);
    Serial1.begin(9600);
}

/* Read one NMEA line, return true when complete */
bool readNMEA(char *buf, int buf_size) {
    static char tmp[128];
    static int pos = 0;
    while (Serial1.available()) {
        char c = Serial1.read();
        if (c == '\n') {
            if (pos > 0 && tmp[pos-1] == '\r') pos--;
            tmp[pos] = '\0';
            if (pos > 0 && tmp[0] == '$') {
                strncpy(buf, tmp, buf_size - 1);
                buf[buf_size - 1] = '\0';
                pos = 0;
                return true;
            }
            pos = 0;
        } else if (pos < (int)sizeof(tmp) - 1) {
            tmp[pos++] = c;
        }
    }
    return false;
}

/* Split NMEA sentence into fields */
int splitNMEA(char *sentence, char *fields[], int max_fields) {
    int count = 0;
    fields[count++] = sentence;
    for (char *p = sentence; *p && count < max_fields; p++) {
        if (*p == ',') { *p = '\0'; fields[count++] = p + 1; }
        if (*p == '*') { *p = '\0'; break; }
    }
    return count;
}

double nmeaToDeg(const char *field, char dir) {
    double raw = atof(field);
    int deg = (int)(raw / 100);
    double result = deg + (raw - deg * 100) / 60.0;
    if (dir == 'S' || dir == 'W') result = -result;
    return result;
}

char line[128];
char *fields[20];

/* GPS_NMEA_Output: forward all sentences */
void loop_raw() {
    if (readNMEA(line, sizeof(line))) {
        Serial.println(line);
    }
}

/* GPS_Raw_Data_Filter: only $GPGGA */
void loop_filter() {
    if (readNMEA(line, sizeof(line))) {
        if (strncmp(line, "$GPGGA", 6) == 0) {
            Serial.println(line);
        }
    }
}

/* GPS_Fix_Status: print fix valid/invalid */
void loop_fix() {
    if (readNMEA(line, sizeof(line))) {
        char tmp[128];
        strcpy(tmp, line);
        int n = splitNMEA(tmp, fields, 20);
        if (strncmp(line, "$GPGGA", 6) == 0 && n >= 7) {
            int fix = atoi(fields[6]);
            Serial.println(fix > 0 ? "fix valid" : "fix invalid");
        }
    }
}

/* GPS_Latitude_Longitude_Parsing: lat/lon from $GPGGA */
void loop_latlon() {
    if (readNMEA(line, sizeof(line))) {
        char tmp[128];
        strcpy(tmp, line);
        int n = splitNMEA(tmp, fields, 20);
        if (strncmp(line, "$GPGGA", 6) == 0 && n >= 6 && atoi(fields[6]) > 0) {
            double lat = nmeaToDeg(fields[2], fields[3][0]);
            double lon = nmeaToDeg(fields[4], fields[5][0]);
            Serial.print("Lat="); Serial.print(lat, 6);
            Serial.print(", Lon="); Serial.println(lon, 6);
        }
    }
}

void loop() { loop_latlon(); }
```

### Using Adafruit GPS Library (Recommended for Arduino)
```cpp
#include <Adafruit_GPS.h>

#define GPS_SERIAL Serial1
Adafruit_GPS GPS(&GPS_SERIAL);

void setup() {
    Serial.begin(115200);
    GPS.begin(9600);
    GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
    GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);
}

void loop() {
    GPS.read();
    if (GPS.newNMEAreceived() && GPS.parse(GPS.lastNMEA())) {
        if (GPS.fix) {
            Serial.print("Lat="); Serial.print(GPS.latitudeDegrees, 6);
            Serial.print(", Lon="); Serial.println(GPS.longitudeDegrees, 6);
        } else {
            Serial.println("fix invalid");
        }
    }
}
```

---

## nRF52840 + Zephyr Implementation

```c
/* prj.conf */
// CONFIG_SERIAL=y
// CONFIG_UART_INTERRUPT_DRIVEN=y

#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include <string.h>
#include <stdlib.h>

static const struct device *gps_uart = DEVICE_DT_GET(DT_NODELABEL(uart1));

#define LINE_SIZE 256
K_MSGQ_DEFINE(nmea_queue, LINE_SIZE, 8, 4);

static char rx_line[LINE_SIZE];
static int  rx_pos = 0;

static void uart_isr(const struct device *dev, void *ctx) {
    if (!uart_irq_update(dev)) return;
    while (uart_irq_rx_ready(dev)) {
        uint8_t c;
        uart_fifo_read(dev, &c, 1);
        if (c == '\n') {
            if (rx_pos > 0 && rx_line[rx_pos-1] == '\r') rx_pos--;
            rx_line[rx_pos] = '\0';
            if (rx_pos > 0 && rx_line[0] == '$') {
                k_msgq_put(&nmea_queue, rx_line, K_NO_WAIT);
            }
            rx_pos = 0;
        } else if (rx_pos < LINE_SIZE - 1) {
            rx_line[rx_pos++] = c;
        }
    }
}

/* Split and helper — same logic as ESP32 version */
static int split(char *s, char *f[], int max) {
    int n = 0; f[n++] = s;
    for (char *p = s; *p && n < max; p++) {
        if (*p == ',') { *p = '\0'; f[n++] = p+1; }
        if (*p == '*') { *p = '\0'; break; }
    }
    return n;
}

static double to_deg(const char *f, char dir) {
    double r = atof(f); int d = (int)(r/100);
    double res = d + (r - d*100)/60.0;
    if (dir=='S'||dir=='W') res = -res;
    return res;
}

int main(void) {
    uart_irq_callback_user_data_set(gps_uart, uart_isr, NULL);
    uart_irq_rx_enable(gps_uart);

    char buf[LINE_SIZE];
    char *f[20];
    while (1) {
        if (k_msgq_get(&nmea_queue, buf, K_MSEC(2000)) == 0) {
            char tmp[LINE_SIZE];
            strcpy(tmp, buf);
            int n = split(tmp, f, 20);
            if (strncmp(buf, "$GPGGA", 6) == 0 && n >= 7 && atoi(f[6]) > 0) {
                double lat = to_deg(f[2], f[3][0]);
                double lon = to_deg(f[4], f[5][0]);
                printk("Lat=%.6f, Lon=%.6f\n", lat, lon);
            }
        }
    }
}
```

## Geographic Region Check (for Location_Based_Reminder)

```c
/* Check if coordinates are within a rectangular region */
typedef struct { double lat_min, lat_max, lon_min, lon_max; } geo_region_t;

bool inside_region(double lat, double lon, const geo_region_t *r) {
    return (lat >= r->lat_min && lat <= r->lat_max &&
            lon >= r->lon_min && lon <= r->lon_max);
}

/* Example: San Francisco area */
const geo_region_t sf_region = {37.7, 37.85, -122.52, -122.35};
bool inside = inside_region(lat, lon, &sf_region);
```

## Best Practices
1. Always check fix status before using lat/lon values
2. Use non-blocking reads (`available()` on Arduino, `uart_poll_in()` on Zephyr)
3. Sentence parsing: duplicate the string before calling `strtok()` or manual split
4. NMEA DDMM.MMMM ≠ decimal degrees — always convert using the formula
5. Cold fix can take 30-60s; ensure antenna has clear sky view

## Common Pitfalls
- ❌ Using raw lat/lon directly (DDMM.MMMM format, not decimal degrees)
- ❌ Parsing sentences with no fix (field 6 of GPGGA = 0)
- ❌ Blocking the UART read loop with delay() — miss incoming sentences
- ❌ Not stripping `*CS` checksum before parsing last field

## Related Skills
- `uart-communication-esp32-esp-idf.md` - ESP32 UART setup
- `uart-communication-atmega2560-arduino.md` - Arduino UART setup
- `ds1307-rtc.md` - Timestamp for GPS data logging
- `microsd-spi.md` - SD card for GPS data logging
