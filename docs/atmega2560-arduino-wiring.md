## Pin Mapping for Testing with IoT-SkillsBench

[ATmega2560 Pinout Diagram](https://docs.arduino.cc/resources/pinouts/A000067-full-pinout.pdf)

- Outputs / actuators
	- LED1: D12
	- LED2: D11
	- Active buzzer: D9
	- Passive buzzer: D7

- Human input / simple digital sensors
	- Push button: D10 
	- DHT11 data: D8
	- Sound sensor (digital output): D3 (with Interrupt)
	- HC-SR04 ultrasonic distance sensor: D23 (TRIG), D22 (ECHO)

- Analog inputs
	- TMP36 temperature sensor: A0
	- Sound sensor (analog output): A1
	- Photoresistor light sensor (KY-018): A2

- LCD1602 (4-bit mode)
	- RS: D48
	- E:  D49
	- D4: D46
	- D5: D47
	- D6: D44
	- D7: D45