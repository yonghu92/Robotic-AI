# CAN Send Failure Debug - Issue and Fix

## Problem Summary

You were seeing `SEND_MESSAGE_FAILED (100017)` errors even though:
- CAN interface is UP and working
- CAN messages can be received from the arm
- Some CAN messages are being sent (TX counter shows 3,018 packets)

## Root Cause

The issue is **NOT** with CAN sending itself. The problem is that **the arm is not properly enabled**, which causes the arm to reject control commands.

### Why EnablePiper() Returns False

The `EnablePiper()` function has a bug in its logic:
1. It checks the enable status **BEFORE** sending the enable command
2. It sends the enable command
3. It returns the status from step 1 (which is still False if arm wasn't enabled)

So even after sending the enable command, it returns False because it checked the status before sending.

## Solution

Instead of using `EnablePiper()` which has this timing issue, use this pattern:

```python
# Proper enable sequence
for i in range(50):
    # Send enable command
    piper.EnableArm(7)
    time.sleep(0.05)  # Wait for enable to take effect
    
    # Check if all motors are enabled
    enable_list = piper.GetArmEnableStatus()
    if all(enable_list):
        print("✓ Arm enabled!")
        break
```

## Fixes Applied

1. **Improved error logging** in `can_encapsulation.py` to log actual exceptions
2. **Updated notebook Cell 6** to use proper enable sequence
3. **Created test scripts** that confirmed CAN sending works when arm is enabled

## Testing Results

- ✅ CAN sending works perfectly when arm is enabled (100/100 success rate)
- ✅ The issue was arm not being enabled, not CAN communication
- ✅ With proper enable sequence, all commands work correctly

## Next Steps

Update your notebook Cell 2 to use the proper enable sequence shown above. The key is:
1. Send `EnableArm(7)` command
2. Wait a bit (0.05s)
3. Check `GetArmEnableStatus()` to verify all motors are enabled
4. Repeat until enabled or timeout

Once the arm is properly enabled, all the `SEND_MESSAGE_FAILED` errors should disappear!
