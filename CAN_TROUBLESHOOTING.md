# CAN Connection Troubleshooting Guide

## Problem: "No buffer space available" / Arm Not Responding

When you see errors like:
- `No buffer space available`
- `Send failed - no ACK from arm`
- `No CAN messages from the arm at all`

This means the **CAN interface exists but the arm controller is not responding**.

---

## Quick Diagnostic

Run the diagnostic script:

```bash
python3 diagnose_can_connection.py
```

This will check:
1. ✅ CAN interface exists
2. ✅ CAN interface is UP and configured
3. ✅ Can receive messages from arm
4. ✅ Can send messages to arm
5. ✅ Physical connection checklist

---

## Common Causes & Solutions

### 1. CAN Interface Not Activated

**Symptoms:** Interface exists but is DOWN

**Solution:**
```bash
cd piper_sdk/piper_sdk
bash can_activate.sh can0 1000000
```

**Verify:**
```bash
ip link show can0
# Should show "UP" status
```

---

### 2. Arm Controller Not Powered

**Symptoms:** No messages received, "No buffer space available"

**Check:**
- [ ] Arm controller box has power LED on
- [ ] Power supply is connected
- [ ] Controller is not in emergency stop mode

**Solution:** Power cycle the arm controller

---

### 3. CAN Cable Not Connected

**Symptoms:** No messages at all

**Check:**
- [ ] CAN cable connected to arm controller
- [ ] CAN cable connected to USB-to-CAN adapter
- [ ] USB-to-CAN adapter plugged into computer
- [ ] All connections are firm (not loose)

---

### 4. Wrong CAN Interface Name

**Symptoms:** Interface not found, wrong device

**Solution:**
```bash
# Find all CAN devices
cd piper_sdk/piper_sdk
bash find_all_can_port.sh

# Output will show something like:
# Interface can0 is connected to USB port 3-1.1:1.0
# Interface can1 is connected to USB port 3-1.4:1.0

# If you have multiple, activate the one connected to arm:
bash can_activate.sh can_piper 1000000 "3-1.4:1.0"
```

Then update your script to use the correct interface:
```python
pp = PickAndPlace(can_interface="can_piper")  # Instead of "can0"
```

---

### 5. CAN Bitrate Mismatch

**Symptoms:** Interface works but no communication

**Check current bitrate:**
```bash
ip -details link show can0 | grep bitrate
```

**Should be:** `bitrate 1000000`

**Fix if wrong:**
```bash
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

---

## Step-by-Step Setup

### First Time Setup:

1. **Install CAN utilities:**
   ```bash
   sudo apt update
   sudo apt install can-utils ethtool iproute2
   ```

2. **Find CAN device:**
   ```bash
   cd piper_sdk/piper_sdk
   bash find_all_can_port.sh
   ```

3. **Activate CAN interface:**
   ```bash
   # If only one CAN device:
   bash can_activate.sh can0 1000000
   
   # If multiple devices, use USB port:
   bash can_activate.sh can_piper 1000000 "USB_PORT_ADDRESS"
   ```

4. **Verify it's working:**
   ```bash
   # Check interface is UP
   ip link show can0
   
   # Listen for messages (arm should be powered)
   candump can0
   # You should see messages if arm is on
   ```

5. **Test send:**
   ```bash
   # In another terminal:
   cansend can0 123#00.00.00.00
   ```

---

## Testing CAN Connection

### Manual Test:

```bash
# Terminal 1: Listen
candump can0

# Terminal 2: Send test
cansend can0 123#00.00.00.00

# If you see messages in Terminal 1, CAN is working!
```

### Python Test:

```python
from piper_sdk import C_PiperInterface_V2

try:
    piper = C_PiperInterface_V2('can0')
    piper.ConnectPort()
    print("✓ CAN connection successful!")
    
    # Try to get arm status
    status = piper.GetArmEnableStatus()
    print(f"Arm status: {status}")
except Exception as e:
    print(f"✗ CAN connection failed: {e}")
```

---

## What the Error Messages Mean

| Error | Meaning | Solution |
|-------|---------|----------|
| `No buffer space available` | No device acknowledging CAN messages | Check arm power & connection |
| `No such device` | CAN interface doesn't exist | Activate CAN interface |
| `Operation not permitted` | Need sudo for CAN operations | Run with sudo or fix permissions |
| `Interface is DOWN` | CAN interface not activated | Run `can_activate.sh` |
| `Timeout enabling arm` | Arm not responding | Check power, connection, enable sequence |

---

## Still Not Working?

1. **Run diagnostic:**
   ```bash
   python3 diagnose_can_connection.py
   ```

2. **Check system logs:**
   ```bash
   dmesg | grep -i can
   journalctl -u can*  # If using systemd
   ```

3. **Try different CAN interface:**
   - Maybe it's `can1` instead of `can0`
   - Check with `ip link show type can`

4. **Power cycle everything:**
   - Unplug USB-to-CAN adapter
   - Power off arm controller
   - Wait 10 seconds
   - Power on arm controller
   - Plug in USB-to-CAN adapter
   - Run `can_activate.sh` again

5. **Check hardware:**
   - Try different USB port
   - Try different CAN cable
   - Check if USB-to-CAN adapter works with other devices

---

## Quick Reference Commands

```bash
# Check CAN interfaces
ip link show type can

# Check specific interface
ip link show can0

# Activate CAN
cd piper_sdk/piper_sdk
bash can_activate.sh can0 1000000

# Find CAN ports
bash find_all_can_port.sh

# Listen for messages
candump can0

# Send test message
cansend can0 123#00.00.00.00

# Reset CAN interface
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up

# Check CAN statistics
ip -s link show can0
```

---

## Need More Help?

- Check `CAN_DEBUG_FIX.md` for enable sequence issues
- Check `piper_sdk/README.MD` for SDK documentation
- Check `piper_sdk/asserts/can_config.MD` for detailed CAN setup
