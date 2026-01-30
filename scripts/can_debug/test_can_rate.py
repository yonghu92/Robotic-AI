#!/usr/bin/env python3
"""
Test CAN send rate and check for timing issues
"""
import time
from piper_sdk import C_PiperInterface_V2
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_can_rate():
    print("=== CAN Rate Test ===\n")
    
    piper = C_PiperInterface_V2('can0')
    piper.ConnectPort()
    time.sleep(0.5)
    
    # Clear e-stop
    piper.EmergencyStop(0x02)
    time.sleep(0.5)
    
    # Enable arm
    print("Enabling arm...")
    for i in range(100):
        if piper.EnablePiper():
            print("✓ Arm enabled!")
            break
        time.sleep(0.02)
    else:
        print("✗ Failed to enable arm")
        return
    
    # Set mode
    piper.ModeCtrl(0x01, 0x01, 50, 0x00)
    time.sleep(0.3)
    
    # Get current joints
    joints = piper.GetArmJointMsgs()
    j1 = joints.joint_state.joint_1
    j2 = joints.joint_state.joint_2
    j3 = joints.joint_state.joint_3
    j4 = joints.joint_state.joint_4
    j5 = joints.joint_state.joint_5
    j6 = joints.joint_state.joint_6
    
    print(f"\nSending JointCtrl commands at different rates...")
    print("Testing 50Hz (0.02s delay)...")
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    for i in range(100):
        try:
            piper.JointCtrl(j1, j2, j3, j4, j5, j6)
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Exception at iteration {i}: {e}")
        time.sleep(0.02)
    
    elapsed = time.time() - start_time
    print(f"\nResults:")
    print(f"  Success: {success_count}/100")
    print(f"  Failed: {fail_count}/100")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Rate: {100/elapsed:.1f} Hz")
    
    print("\nTesting 10Hz (0.1s delay)...")
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    for i in range(100):
        try:
            piper.JointCtrl(j1, j2, j3, j4, j5, j6)
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Exception at iteration {i}: {e}")
        time.sleep(0.1)
    
    elapsed = time.time() - start_time
    print(f"\nResults:")
    print(f"  Success: {success_count}/100")
    print(f"  Failed: {fail_count}/100")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Rate: {100/elapsed:.1f} Hz")

if __name__ == "__main__":
    test_can_rate()
