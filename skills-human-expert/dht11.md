---
name: DHT11 Temperature Sensor
description: A digital sensor for temperature and relative humidity (RH).
---

## Pinout

| Name | Description |
|---|---|
| VCC | Voltage supply |
| GND | Ground |
| DATA | Serial data output |


## Operation

- DHT11 communicates via a **single-wire** **half-duplex** interface. It is powered from 3.3V to 5V and outputs 40 bits per read. Minimum interval between reads is **2 seconds**.

- Attributes and detection range: 
    - **Temperature range**: 0°C to 50°C;
    - **Temperature accuracy**: ±2°C;
    - **Humidity range**: 20% to 90% relative humidity (RH)
    - **Humidity accuracy**: ±5% RH

---

### Start Signal (Host → Sensor)
```
Host pulls LOW for at least 18ms    → Start pulse
Host releases HIGH for 20–40µs      → Preparation
Sensor responds...
```

---

### Sensor Response (Sensor → Host)
```
Sensor pulls LOW for 80µs           → Response LOW
Sensor pulls HIGH for 80µs          → Response HIGH
Data transmission begins...
```

---

### Bit Encoding

DHT11 encodes each bit by the **duration of the HIGH phase**:
```
LOW  54µs + HIGH ~28µs  → bit 0
LOW  54µs + HIGH ~70µs  → bit 1
```

Threshold: HIGH duration **> 40µs = bit 1**, otherwise bit 0.

---

### Data Format (40 bits = 5 bytes)
```
Byte 0: Humidity integer
Byte 1: Humidity decimal (always 0 for DHT11)
Byte 2: Temperature integer
Byte 3: Temperature decimal (always 0 for DHT11)
Byte 4: Checksum = byte0 + byte1 + byte2 + byte3
```

Always verify the checksum before using the data.