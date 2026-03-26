## Pin Mapping for Testing with IoT-SkillsBench

[ATmega2560 Pinout Diagram](https://docs.arduino.cc/resources/pinouts/A000067-full-pinout.pdf)

- Outputs / actuators
	- LED1: D12
	- LED2: D11
	- Active buzzer: D9
	- Passive buzzer: D7
	- Laser emitter (KY-008): D24

- Human input / simple digital sensors
	- Push button: D10 
	- Temperature & humidity sensor (DHT11): D8
	- Sound sensor digital output (KY-037): D3 (with Interrupt)
	- Ultrasonic distance sensor (HC-SR04): D23 (TRIG), D22 (ECHO)

- Analog inputs
	- Temperature sensor (TMP36): A0
	- Sound sensor analog output (KY-037): A1
	- Photoresistor light sensor (KY-018): A2
	- Joystick (KY-023): A3 (x-axis), A4 (y-axis)

- Display
	- LCD1602 (4-bit mode): D48 (RS), D49(E), D46 (D4), D47 (D5), D44 (D6), D45 (D7)

- I2C
	- IMU (MPU6050, GY-521): D20 (SDA), D21 (SCL)
	- RTC (DS1307): D20 (SDA), D21 (SCL)