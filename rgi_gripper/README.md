# RGI Series Rotating Gripper Control

Python interface for the RGI series rotating gripper using Modbus RTU protocol.

## Setup

### 1. Install dependencies
```bash
pip install pyserial
```

### 2. Add user to dialout group (required for serial port access)
```bash
sudo usermod -a -G dialout $USER
```
**Then log out and log back in** for the group change to take effect.

### 3. Check if gripper is connected
```bash
ls -la /dev/ttyUSB*
```
You should see `/dev/ttyUSB0` or similar.

## Usage

### Test Connection
```bash
python rgi_connection.py
```

### Rotate Gripper
```bash
# Default: 60 seconds at 20% speed on /dev/ttyUSB0
python rotate_gripper.py

# Custom: [port] [duration_seconds] [speed_percent]
python rotate_gripper.py /dev/ttyUSB0 30 50
```

## Modbus Register Map

| Register | Address | Description |
|----------|---------|-------------|
| Initialize | 0x0100 | Write 0xA5 to initialize |
| Speed | 0x0107 | Rotation speed (0-100%) |
| Force | 0x0108 | Rotation force (0-100%) |
| Target | 0x0109 | Target rotation (degrees) |
| Current Angle | 0x0208 | Read current angle |
| Status | 0x020B | 0=moving, 1=complete |

## Example Code

```python
from rotate_gripper import RGIGripper

# Connect
gripper = RGIGripper(port='/dev/ttyUSB0')
gripper.connect()

# Initialize
gripper.initialize()

# Set speed and force
gripper.set_speed(30)  # 30%
gripper.set_force(50)  # 50%

# Rotate 1000 degrees
gripper.rotate(1000)

# Check status
while gripper.get_status() != 1:
    angle = gripper.get_angle()
    print(f"Current angle: {angle}")
    time.sleep(0.5)

# Stop and disconnect
gripper.stop()
gripper.disconnect()
```

## Troubleshooting

1. **Permission denied on /dev/ttyUSB0**
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and log back in
   ```

2. **Port not found**
   ```bash
   # Check connected USB devices
   dmesg | tail -20
   ls -la /dev/ttyUSB*
   ```

3. **No response from gripper**
   - Check cable connections
   - Verify baud rate (default: 115200)
   - Check power supply to gripper

## Files

- `rgi_connection.py` - Basic connection testing
- `rotate_gripper.py` - Gripper control with rotation commands
- `manual.pdf` - Product manual (Chinese)
- `requirements.txt` - Python dependencies
