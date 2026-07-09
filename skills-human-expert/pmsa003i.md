---
name: PMSA003I
description: A laser-based particular matter (PM) air quality sensor.
---

## Pinout

| Name | Description |
|---|---|
| VIN | Voltage supply, 3-5V, use same voltage as MCU logic level |
| 3Vo | 3.3V output from onboard LDO, maximum 100mA |
| GND | Ground |
| SCL | I2C clock line; includes 10k pull up onboard |
| SDA | I2C data line |
| RST | Reset input; active low; optional |
| SET | Sleep input; active low to turn off fan and laser; optional |

## Operation

- I2C interface with address 0x12
- The I2C data stream updates once per second, you'll get:
    - PM1.0, PM2.5 and PM10.0 concentration in both standard & environmental units.
    - Particulate matter per 0.1L air, categorized into 0.3um, 0.5um, 1.0um, 2.5um, 5.0um, and 10um size bins.
    - checksum, in binary format.
- For Arduino framework, use `Adafruit_PM25AQI.h` in `Adafruit PM25 AQI Sensor` library.
    - Use `Adafruit_PM25AQI.begin_I2C()` to connect, then use `read(PM25_AQI_Data *data)` to read.
    - Fields in PM25_AQI_Data includes the following
        - pm10_standard, pm25_standard, pm100_standard, pm10_env, pm25_env, pm100_env, particles_03um, particles_05um, particles_10um, particles_25um, particles_50um, particles_100um
        - AQI conversion result fields include the following: aqi_pm25_us, aqi_pm100_us, aqi_pm25_china, aqi_pm100_china
