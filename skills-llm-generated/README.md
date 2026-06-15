# Self-Generated Skills - Task Analysis

## Overview
This directory contains modular skill documents generated from analyzing the tasks. Each skill focuses on a specific MCU, board, IoT tool, protocol, framework, or embedded technique with code examples and usage patterns designed to be reusable across similar tasks.

## Organization

### Platform-Specific Skills

#### ESP32 + ESP-IDF
- `gpio-interrupts-esp32-esp-idf.md` - GPIO interrupt handling with FreeRTOS queues
- `hardware-timers-esp32-esp-idf.md` - Hardware timer configuration and periodic tasks
- `adc-reading-esp32-esp-idf.md` - ADC configuration, calibration, and sensor reading
- `pwm-control-esp32-esp-idf.md` - PWM generation using LEDC peripheral
- `i2c-communication-esp32-esp-idf.md` - I2C master communication with sensors
- `uart-communication-esp32-esp-idf.md` - UART setup, line reading, binary packet protocols
- `spi-communication-esp32-esp-idf.md` - SPI master, multi-device, DMA transfers

#### ATMega2560 + Arduino
- `gpio-interrupts-atmega2560-arduino.md` - Hardware interrupts on specific pins
- `i2c-communication-atmega2560-arduino.md` - Wire library, register read/write patterns
- `uart-communication-atmega2560-arduino.md` - Hardware serial ports (Serial1-3), line/packet reading
- `spi-communication-atmega2560-arduino.md` - SPI library, multi-device chip select

#### nRF52840 + Zephyr RTOS
- `gpio-and-timers-nrf52840-zephyr.md` - GPIO control, interrupts, and timer usage with device tree
- `i2c-communication-nrf52840-zephyr.md` - Zephyr I2C driver API, DTS configuration
- `uart-communication-nrf52840-zephyr.md` - Polling and interrupt-driven UART, line buffering
- `spi-communication-nrf52840-zephyr.md` - Zephyr SPI driver API, scatter-gather transfers

### Generic/Cross-Platform Skills
- `software-debouncing-pattern.md` - Button debouncing techniques (applicable to all platforms)
- `matrix-keypad-scanning-generic.md` - 4x4 matrix keypad scanning algorithm
- `ultrasonic-hcsr04-generic.md` - HC-SR04 ultrasonic distance measurement

### Sensor and Device Skills (All Platforms)
- `vl53l0x-tof-sensor.md` - VL53L0X ToF distance sensor (I2C, all platforms + gesture detection)
- `gps-nmea-uart.md` - PA1616S GPS NMEA parsing, lat/lon, fix status (all platforms)
- `fingerprint-sensor-uart.md` - R307/AS608 fingerprint sensor UART protocol, enroll/match/delete
- `ina219-power-sensor.md` - INA219 voltage/current/power monitor (I2C, all platforms)
- `ltr390-uv-sensor.md` - LTR390 UV/ALS sensor, mode switching, alert (I2C, all platforms)
- `sgp40-voc-sensor.md` - SGP40 VOC sensor, CRC, humidity compensation, VOC index (I2C, all platforms)
- `pmsa003i-air-quality.md` - PMSA003I PM1.0/PM2.5/PM10 frame parsing, checksum, AQI (I2C, all platforms)
- `pn532-nfc-rfid.md` - PN532 NFC/RFID UID read, MIFARE auth/block read, door lock (I2C+SPI, all platforms)
- `max30101-heart-rate.md` - MAX30101+MAX32664 heart rate/SpO2, FIFO reading, alert (I2C, all platforms)
- `microsd-spi.md` - MicroSD SPI init, file create/read/append, GPS/power logging (all platforms)
- `lcd1602-i2c.md` - LCD1602 PCF8574 I2C backpack, text display, backlight blink, alerts (all platforms)
- `ds1307-rtc.md` - DS1307 RTC date/time read/write, BCD conversion, timestamp (I2C, all platforms)
- `relay-gpio-control.md` - Relay GPIO control, active-high/low, timed unlock, access control
- `speaker-buzzer-output.md` - Active/passive buzzer, GPIO toggle, PWM tone, non-blocking alert

## Skills Summary

### Core Techniques Covered

#### 1. GPIO Operations
- **Digital I/O**: Basic pin control, reading, and writing
- **Interrupts**: Edge-triggered and level-triggered interrupts
- **Debouncing**: Software debouncing for button inputs
- **Platforms**: ESP32, ATMega2560, nRF52840

#### 2. Timing and Scheduling
- **Hardware Timers**: Periodic and one-shot timers
- **Non-blocking Patterns**: Using millis() or tick counts
- **Timer Interrupts**: ISR-based periodic tasks
- **Platforms**: ESP32, ATMega2560, nRF52840

#### 3. Analog Input
- **ADC Configuration**: Resolution, attenuation, calibration
- **Sensor Reading**: Temperature (TMP36), light (photoresistor), joystick
- **Filtering**: Averaging, median filtering for noise reduction
- **Platforms**: ESP32 (ESP-IDF)

#### 4. PWM Output
- **LED Control**: Brightness, breathing effects
- **Buzzer Tones**: Frequency generation for passive buzzers
- **Servo Control**: Position control (similar techniques)
- **Platforms**: ESP32 (LEDC peripheral)

#### 5. Communication Protocols
- **I2C Master**: Device scanning, read/write operations
- **Sensor Examples**: MPU6050, DS3231 RTC, BME280
- **Error Handling**: Retry logic, timeout management
- **Platforms**: ESP32 (ESP-IDF)

#### 6. Input Devices
- **Matrix Keypad**: Row-column scanning, debouncing
- **Rotary Encoder**: Position and direction tracking
- **Buttons**: Simple and advanced debouncing
- **Platforms**: Generic, adaptable to all

#### 7. Sensors
- **Ultrasonic**: Distance measurement with HC-SR04
- **IMU**: Accelerometer and gyroscope data (MPU6050)
- **Environmental**: Temperature, humidity, pressure (DHT11, BME280)
- **Platforms**: Generic algorithms, platform-specific I/O

## Task Coverage

These skills enable implementation of the following task categories:

### Basic GPIO Tasks
- LED blinking (blocking and non-blocking)
- Button reading with debouncing
- Multiple LED control at different frequencies
- Morse code generation

### Sensor Integration Tasks
- DHT11 temperature and humidity reading
- MPU6050 IMU data acquisition
- DS3231 RTC time/date retrieval
- BME280 pressure and temperature reading
- Ultrasonic distance measurement (HC-SR04)
- Analog sensors (TMP36, photoresistor)

### User Interface Tasks
- 16-key matrix keypad input
- LCD1602 display (requires LCD-specific skill)
- Rotary encoder position tracking

### Interrupt-Driven Tasks
- Button-triggered sensor reading
- Button-triggered display update
- Timer-triggered periodic sampling
- GPIO interrupt-based event handling

### Complex Integration Tasks
- Safe box with keypad and relay
- Parking sensor with distance-based feedback
- Automatic brightness control
- Multi-sensor data fusion and averaging

## Skill Usage Pattern

### 1. Identify Task Requirements
- Determine required hardware components
- Identify needed techniques (GPIO, timer, ADC, I2C, etc.)
- Choose target platform (ESP32, ATMega2560, nRF52840)

### 2. Select Relevant Skills
- Load platform-specific skills for core operations
- Add generic skills for common patterns
- Reference sensor-specific implementations

### 3. Combine and Adapt
- Follow code examples from multiple skills
- Adapt GPIO pin assignments to task requirements
- Integrate multiple techniques (e.g., interrupt + I2C + LCD)

### 4. Implement and Test
- Start with simple examples from skills
- Gradually add complexity
- Test on target hardware

## Example: Implementing "Button_triggered_DHT11_display"

**Required Skills:**
1. `gpio-interrupts-esp32-esp-idf.md` - Button interrupt handling
2. `i2c-communication-esp32-esp-idf.md` - If LCD uses I2C
3. Existing `dht11-sensor` skill - DHT11 communication
4. Existing `lcd1602` skill - LCD display control
5. `software-debouncing-pattern.md` - Button debouncing

**Integration Approach:**
```c
// From gpio-interrupts skill: Setup button interrupt
// From debouncing skill: Add debounce logic in ISR task
// From dht11-sensor skill: Read temperature and humidity
// From lcd1602 skill: Display formatted data
```

## Example: Implementing "Timer_triggered_MPU6050_average_display"

**Required Skills:**
1. `hardware-timers-esp32-esp-idf.md` - 100ms periodic timer
2. `i2c-communication-esp32-esp-idf.md` - MPU6050 I2C reading
3. Existing `lcd1602` skill - LCD display
4. Data averaging pattern (from ADC or I2C skill)

## Best Practices

### Skill Selection
1. **Start with platform-specific skills** for core I/O operations
2. **Use generic skills** for algorithms and patterns
3. **Combine multiple skills** for complex tasks
4. **Reference existing skills/** directory for device-specific implementations

### Code Integration
1. **Keep modular** - Separate concerns (GPIO, communication, display)
2. **Follow skill patterns** - Use proven code structures
3. **Adapt pin assignments** - Match task GPIO requirements
4. **Test incrementally** - Validate each component before integration

### Documentation
1. **Reference skills used** - Document which skills were combined
2. **Note adaptations** - Document changes from skill examples
3. **Include pin mapping** - Clearly show GPIO assignments
4. **Provide usage examples** - Show how to run and test

## Future Additions

### Recommended Additional Skills
1. **SPI Communication** - For MPU6050 SPI mode, BME280 SPI
2. **1-Wire Protocol** - For DHT11, DS18B20 temperature sensor
3. **Hardware PWM Advanced** - Servo control, motor control
4. **LCD1602 4-bit Mode** - Direct GPIO LCD control
5. **LCD1602 I2C Mode** - I2C backpack LCD control
6. **Data Filtering** - Advanced filtering techniques
7. **State Machines** - Complex task orchestration
8. **Power Management** - Sleep modes, low power techniques

### Platform Completion
- More ATMega2560 + Arduino specific skills
- More nRF52840 + Zephyr specific skills
- Zephyr I2C, SPI, PWM implementations

## Contributing

When adding new skills:
1. **Follow naming convention**: `[technique]-[platform]-[framework].md` or `[technique]-generic.md`
2. **Include complete examples**: Full working code, not just snippets
3. **Document best practices**: Common pitfalls, optimization tips
4. **Cross-reference**: Link to related skills
5. **Test on hardware**: Verify examples work on actual hardware

## Related Directories
- `../skills/` - Official pre-existing skills (dht11-sensor, lcd1602, esp32-s3, etc.)
- `../tasks/` - Task definitions and requirements
- `../tasks/level[X]/` - Level-specific task implementations

## References
- ESP-IDF Documentation: https://docs.espressif.com/projects/esp-idf/
- Arduino Reference: https://www.arduino.cc/reference/
- Zephyr Documentation: https://docs.zephyrproject.org/
- nRF52840 Documentation: https://infocenter.nordicsemi.com/

---

**Last Updated:** 2026-03-04
**Skills Created:** 11
**Platforms Covered:** ESP32 + ESP-IDF, ATMega2560 + Arduino, nRF52840 + Zephyr
**Task Categories:** GPIO, Timers, ADC, PWM, I2C, Input Devices, Sensors
