# RGI Series Rotating Gripper - English Manual

## Product Overview

The RGI Series is an electric rotating gripper that communicates via **Modbus RTU protocol** over a serial (RS485/USB) connection.

**Key Specifications:**
- Communication: Modbus RTU
- Default Baud Rate: 115200
- Data Format: 8N1 (8 data bits, no parity, 1 stop bit)
- Slave ID: 1 (default)

---

## Connection Setup

### Hardware Connection
1. Connect the gripper to your computer via USB-to-RS485 adapter
2. On Linux, the device appears as `/dev/ttyUSB0` (or similar)
3. On Windows, the device appears as `COM6` (or similar)

### Serial Port Settings
| Parameter | Value |
|-----------|-------|
| Baud Rate | 115200 |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Flow Control | None |

---

## Modbus RTU Protocol

### Command Format
```
[Slave ID] [Function Code] [Register Address] [Data] [CRC16]
   1 byte      1 byte          2 bytes       2 bytes  2 bytes
```

### Function Codes
| Code | Function | Description |
|------|----------|-------------|
| 0x03 | Read Holding Registers | Read register values |
| 0x06 | Write Single Register | Write to a single register |

### CRC16 Calculation
The CRC16 uses polynomial 0xA001 (Modbus standard).

---

## Register Map

### Control Registers (Write)

| Register | Address | Range | Description |
|----------|---------|-------|-------------|
| Initialize | 0x0100 | 0xA5 | Write 0xA5 to initialize gripper |
| Rotation Speed | 0x0107 | 0-100 | Speed as percentage (%) |
| Rotation Force | 0x0108 | 0-100 | Force/torque as percentage (%) |
| Target Angle | 0x0109 | -32768 to 32767 | Target rotation in degrees |

### Status Registers (Read)

| Register | Address | Description |
|----------|---------|-------------|
| Current Angle | 0x0208 | Current rotation angle in degrees |
| Rotation Status | 0x020B | 0 = Moving, 1 = Complete |

---

## Basic Operations

### 1. Initialize Gripper
Before any operation, initialize the gripper:
```
Write 0xA5 to register 0x0100
```

**Modbus Command:**
```
01 06 01 00 00 A5 [CRC]
```

### 2. Set Rotation Speed
Set speed as percentage (0-100%):
```
Write speed value to register 0x0107
```

**Example (50% speed):**
```
01 06 01 07 00 32 [CRC]
```

### 3. Set Rotation Force
Set force/torque as percentage (0-100%):
```
Write force value to register 0x0108
```

**Example (50% force):**
```
01 06 01 08 00 32 [CRC]
```

### 4. Rotate to Target Angle
Command rotation in degrees:
```
Write target angle to register 0x0109
```

**Example (rotate 1000 degrees):**
```
01 06 01 09 03 E8 [CRC]
```

**Note:** Positive values = clockwise, Negative values = counter-clockwise

### 5. Read Current Angle
```
Read register 0x0208
```

**Modbus Command:**
```
01 03 02 08 00 01 [CRC]
```

### 6. Check Rotation Status
```
Read register 0x020B
```
- Returns 0: Still moving
- Returns 1: Rotation complete

### 7. Stop Rotation
Write 0 to target angle register:
```
Write 0 to register 0x0109
```

---

## Python Code Examples

### Basic Connection Test
```python
import serial

# Connect
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

# Build Modbus command with CRC
def calc_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def build_cmd(slave_id, func, reg, value):
    import struct
    cmd = struct.pack('>BBHH', slave_id, func, reg, value)
    crc = calc_crc16(cmd)
    return cmd + struct.pack('<H', crc)

# Initialize gripper
cmd = build_cmd(1, 0x06, 0x0100, 0xA5)
ser.write(cmd)
```

### Rotate Gripper
```python
# Set speed to 30%
cmd = build_cmd(1, 0x06, 0x0107, 30)
ser.write(cmd)

# Set force to 50%
cmd = build_cmd(1, 0x06, 0x0108, 50)
ser.write(cmd)

# Rotate 500 degrees
cmd = build_cmd(1, 0x06, 0x0109, 500)
ser.write(cmd)
```

### Read Current Angle
```python
import struct
import time

def read_reg(ser, reg):
    cmd = build_cmd(1, 0x03, reg, 1)
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.05)
    resp = ser.read(100)

    # Parse response
    if len(resp) >= 7:
        for i in range(len(resp) - 6):
            if resp[i] == 0x01 and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                val = (resp[i+3] << 8) | resp[i+4]
                if val > 32767:
                    val -= 65536
                return val
    return None

# Read angle
angle = read_reg(ser, 0x0208)
print(f"Current angle: {angle} degrees")
```

---

## Troubleshooting

### No Response from Gripper
1. Check power supply to gripper
2. Verify cable connections (RS485 A/B polarity)
3. Confirm baud rate is 115200
4. Check if another program is using the serial port

### Permission Denied (Linux)
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in
```

### Wrong Rotation Direction
- Swap A and B lines on RS485 connection, OR
- Use negative angle values

### Gripper Not Moving
1. Ensure gripper is initialized (write 0xA5 to 0x0100)
2. Check that speed > 0
3. Check that force > 0
4. Verify target angle is different from current angle

---

## Safety Notes

1. **Keep hands clear** of rotating gripper during operation
2. **Do not exceed** rated force/torque limits
3. **Initialize properly** before each session
4. **Stop rotation** before disconnecting power
5. **Secure workpiece** properly before gripping

---

## Quick Reference Card

| Action | Register | Value |
|--------|----------|-------|
| Initialize | 0x0100 | 0xA5 |
| Set Speed 50% | 0x0107 | 50 |
| Set Force 50% | 0x0108 | 50 |
| Rotate 1000° | 0x0109 | 1000 |
| Stop | 0x0109 | 0 |
| Read Angle | 0x0208 | (read) |
| Read Status | 0x020B | (read) |

**Status Values:** 0 = Moving, 1 = Complete
