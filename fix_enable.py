#!/usr/bin/env python3
"""
Fixed EnablePiper function that properly waits for enable to take effect
"""
import time
from piper_sdk import C_PiperInterface_V2

def EnablePiperWithWait(piper, max_attempts=50, wait_between_attempts=0.05):
    """
    Enable the arm and wait for it to actually become enabled.
    
    Returns True if enabled, False otherwise.
    """
    for attempt in range(max_attempts):
        # Send enable command
        piper.EnableArm(7)
        time.sleep(wait_between_attempts)
        
        # Check if all motors are enabled
        enable_list = piper.GetArmEnableStatus()
        if all(enable_list):
            return True
    
    return False

# Test it
if __name__ == "__main__":
    piper = C_PiperInterface_V2('can0')
    piper.ConnectPort()
    time.sleep(0.5)
    
    # Clear e-stop
    piper.EmergencyStop(0x02)
    time.sleep(0.5)
    
    print("Enabling arm with fixed function...")
    if EnablePiperWithWait(piper):
        print("✓ Arm enabled successfully!")
        enable_list = piper.GetArmEnableStatus()
        print(f"Enable status: {enable_list}")
    else:
        print("✗ Failed to enable arm")
        enable_list = piper.GetArmEnableStatus()
        print(f"Enable status: {enable_list}")
