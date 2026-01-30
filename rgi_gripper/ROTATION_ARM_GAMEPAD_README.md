# Rotation Arm Gamepad Control

## Overview

This script provides combined gamepad control for both the **Piper Robotic Arm** (6 joints) and the **RGI Rotating Gripper** (open/close + rotation).

## Hardware Requirements

- **Piper Robotic Arm** - Connected via CAN bus (`can0`)
- **RGI Rotating Gripper** - Connected via USB serial (`/dev/ttyUSB1`)
- **Gamepad Controller** - Any USB gamepad (tested with Logitech Dual Action)

## Controls

### Piper Arm Controls

| Control | Action |
|---------|--------|
| Left Stick X | Joint 1 (base rotation) |
| Left Stick Y | Joint 2 (shoulder/arm lifting) |
| Right Stick Y | Joint 3 (elbow) |
| Right Stick X | Joint 4 (wrist yaw) |
| D-Pad UP/DOWN | Joint 5 (wrist pitch) |
| D-Pad LEFT/RIGHT | Joint 6 (wrist rotation) |
| LB (button 4) | Decrease arm speed (25% steps) |
| RB (button 5) | Increase arm speed (25% steps) |
| R3 (button 9) | Go to home position (all joints to 0°) |

### RGI Gripper Controls

| Control | Action |
|---------|--------|
| X (button 0) | OPEN gripper (position 1000) |
| B (button 2) | CLOSE gripper (position 0) |
| LT/L2 (button 6) | Rotate counterclockwise |
| RT/R2 (button 7) | Rotate clockwise |
| Y (button 3) | Increase rotation step size |
| A (button 1) | Decrease rotation step size |

### Rotation Step Sizes

Available step sizes: `[1, 10, 90, 180, 360, 720, 1080]` degrees

Use Y/A buttons to cycle through step sizes for faster or more precise rotation.

## Architecture

### The Problem

Initially, having both arm control and RGI gripper control in the same loop caused **choppy, slow movement**. This was because:

1. The RGI gripper uses **serial communication** (Modbus RTU protocol)
2. Each serial read/write has a small delay (~5-20ms)
3. Multiple serial operations per loop **blocked** the arm control
4. The arm update rate dropped from 50Hz to ~15Hz

### The Solution: Multi-Threading

The code uses **two separate threads**:

```
┌─────────────────────────────────────────────────────────────┐
│                     MAIN THREAD (50Hz)                       │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Read       │───▶│  Update     │───▶│  Send Arm   │      │
│  │  Gamepad    │    │  Joints     │    │  Commands   │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│         │                                                    │
│         │ Set flags (non-blocking)                          │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  RGI Command Flags: open, close, rotate_ccw, etc.   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Thread-safe flags
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   RGI THREAD (50Hz)                          │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Read       │───▶│  Send RGI   │───▶│  Read RGI   │      │
│  │  Flags      │    │  Commands   │    │  Status     │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                                         (every 0.3s)         │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Arm control in main thread** - Runs at full 50Hz without any serial blocking
2. **RGI control in background thread** - Handles all serial communication independently
3. **Thread-safe command flags** - Main thread sets flags, RGI thread reads them
4. **Reduced status reads** - Only read RGI status every 0.3s to prioritize commands

## RGI Gripper Protocol

The RGI gripper uses **Modbus RTU** protocol over serial (RS485/USB).

### Registers

| Register | Address | Description |
|----------|---------|-------------|
| Initialize | 0x0100 | Write 0xA5 to initialize |
| Force | 0x0101 | Gripper force (20-100%) |
| Position | 0x0103 | Gripper position (0=closed, 1000=open) |
| Speed | 0x0104 | Gripper speed (1-100%) |
| Rotation Speed | 0x0107 | Rotation speed (0-100%) |
| Rotation Force | 0x0108 | Rotation force (0-100%) |
| Target Angle | 0x0109 | Rotation target (relative movement) |
| Current Angle | 0x0208 | Current rotation angle (read) |

### Command Format

```
[Slave ID] [Function] [Register] [Value] [CRC16]
  1 byte     1 byte     2 bytes   2 bytes  2 bytes
```

- Function 0x03 = Read register
- Function 0x06 = Write register
- CRC16 uses polynomial 0xA001 (Modbus standard)

## Usage

### Running the Script

```bash
cd /home/robotics_urop/Documents/Robotic\ AI/Robotic-AI/rgi_gripper
python3 rotation_arm_gamepad.py
```

### Startup Sequence

1. Connects to gamepad
2. Connects to RGI gripper (USB serial)
3. Initializes RGI gripper
4. Starts RGI background thread
5. Connects to Piper arm (CAN bus)
6. Clears emergency stop if needed
7. Enables motors
8. Moves arm to home position
9. Starts main control loop

### Stopping

- Press **Ctrl+C** to stop
- You'll be prompted to activate emergency stop (optional)

## Troubleshooting

### Arm not moving smoothly
- Check that RGI thread is running (background)
- Verify no other serial operations in main loop

### Gripper rotation choppy
- Increase RGI thread speed (reduce sleep time)
- Reduce status read frequency
- Use larger step sizes for faster rotation

### Serial port errors
- Check `/dev/ttyUSB1` exists
- Verify no other program using the port
- Try `sudo chmod 666 /dev/ttyUSB1`

### CAN bus errors
- Check `can0` interface is up
- Run `sudo ip link set can0 up type can bitrate 1000000`

## Files

| File | Description |
|------|-------------|
| `rotation_arm_gamepad.py` | Main combined control script |
| `test_4buttons.py` | Standalone RGI gripper test (X/B/LT/RT) |
| `MANUAL_ENGLISH.md` | RGI gripper protocol documentation |

## Performance

| Metric | Value |
|--------|-------|
| Arm update rate | 50 Hz (20ms loop) |
| RGI update rate | 50 Hz (20ms loop) |
| RGI status read | Every 300ms |
| Serial delay | 5ms per command |

## Author

Created for robotics research at MIT UROP.
