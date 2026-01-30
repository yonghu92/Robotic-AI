#!/usr/bin/env python3
"""
Debug script to test CAN send functionality and capture actual exceptions
"""
import sys
import traceback
from piper_sdk import C_PiperInterface_V2

def test_can_send():
    print("=== CAN Send Debug Test ===\n")
    
    # Initialize the interface
    print("1. Initializing CAN interface...")
    try:
        piper = C_PiperInterface_V2('can0')
        print("   ✓ CAN interface created")
    except Exception as e:
        print(f"   ✗ Failed to create CAN interface: {e}")
        traceback.print_exc()
        return
    
    # Connect port
    print("\n2. Connecting to port...")
    try:
        piper.ConnectPort()
        print("   ✓ Port connected")
    except Exception as e:
        print(f"   ✗ Failed to connect port: {e}")
        traceback.print_exc()
        return
    
    # Check CAN bus state
    print("\n3. Checking CAN bus state...")
    try:
        bus_state = piper._C_PiperInterface_V2__arm_can.is_can_bus_ok()
        print(f"   Bus state: {bus_state}")
        print(f"   Bus state value: {bus_state.value}")
        print(f"   Expected ACTIVE: {piper._C_PiperInterface_V2__arm_can.CAN_STATUS.BUS_STATE_ACTIVE.value}")
    except Exception as e:
        print(f"   ✗ Failed to check bus state: {e}")
        traceback.print_exc()
    
    # Try to send a simple message directly
    print("\n4. Testing direct CAN send...")
    try:
        arm_can = piper._C_PiperInterface_V2__arm_can
        result = arm_can.SendCanMessage(0x151, [0x01, 0x01, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00])
        print(f"   Send result: {result}")
        print(f"   Send result value: {result.value}")
        print(f"   Expected SUCCESS: {arm_can.CAN_STATUS.SEND_MESSAGE_SUCCESS.value}")
        if result == arm_can.CAN_STATUS.SEND_MESSAGE_SUCCESS:
            print("   ✓ Send successful!")
        else:
            print("   ✗ Send failed!")
    except Exception as e:
        print(f"   ✗ Exception during send: {e}")
        traceback.print_exc()
    
    # Try to send using the python-can library directly
    print("\n5. Testing python-can library directly...")
    try:
        import can
        bus = can.interface.Bus(channel='can0', bustype='socketcan')
        msg = can.Message(
            arbitration_id=0x151,
            data=[0x01, 0x01, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00],
            is_extended_id=False
        )
        bus.send(msg)
        print("   ✓ Direct python-can send successful!")
        bus.shutdown()
    except Exception as e:
        print(f"   ✗ Direct python-can send failed: {e}")
        traceback.print_exc()
    
    # Try EnablePiper to see what happens
    print("\n6. Testing EnablePiper...")
    try:
        result = piper.EnablePiper()
        print(f"   EnablePiper result: {result}")
    except Exception as e:
        print(f"   ✗ EnablePiper exception: {e}")
        traceback.print_exc()
    
    # Try JointCtrl
    print("\n7. Testing JointCtrl...")
    try:
        joints = piper.GetArmJointMsgs()
        j1 = joints.joint_state.joint_1
        j2 = joints.joint_state.joint_2
        j3 = joints.joint_state.joint_3
        j4 = joints.joint_state.joint_4
        j5 = joints.joint_state.joint_5
        j6 = joints.joint_state.joint_6
        print(f"   Current joints: J1={j1}, J2={j2}, J3={j3}, J4={j4}, J5={j5}, J6={j6}")
        
        # Try sending joint control
        piper.JointCtrl(j1, j2, j3, j4, j5, j6)
        print("   ✓ JointCtrl called (check logs for errors)")
    except Exception as e:
        print(f"   ✗ JointCtrl exception: {e}")
        traceback.print_exc()
    
    print("\n=== Debug Test Complete ===")

if __name__ == "__main__":
    test_can_send()
