#!/usr/bin/env python3
"""
Auto Move Test - Fixed version matching gamepad exactly
"""

import time
import sys

sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')

from piper_sdk import C_PiperInterface_V2

print("=" * 60)
print("  AUTO MOVE TEST (Fixed)")
print("=" * 60)

# Connect
piper = C_PiperInterface_V2("can0")
piper.ConnectPort()
time.sleep(0.5)

# Clear emergency stop if needed
status = piper.GetArmStatus()
if status.arm_status.arm_status == 1:
    print("Clearing emergency stop...")
    piper.EmergencyStop(0x02)
    time.sleep(1.0)

# Step 1: Set CAN mode
print("\n1. Setting CAN mode...")
for i in range(50):
    piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
    time.sleep(0.1)
    if piper.GetArmStatus().arm_status.ctrl_mode == 1:
        print("   CAN mode OK!")
        break

# Step 2: Enable motors with EnableArm
print("2. Enabling motors (EnableArm)...")
for i in range(100):
    piper.EnableArm(7)
    time.sleep(0.1)
    if all(piper.GetArmEnableStatus()):
        print("   Motors enabled!")
        break

# Step 3: Enable with EnablePiper (REQUIRED for JointCtrl!)
print("3. Enabling arm (EnablePiper)...")
for i in range(50):
    if piper.EnablePiper():
        print("   EnablePiper OK!")
        break
    time.sleep(0.02)

# Step 4: Set mode control
print("4. Setting joint control mode...")
piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
time.sleep(0.2)

# Get CURRENT joint positions (start from where the arm actually is!)
joints = piper.GetArmJointMsgs().joint_state
current_j1 = joints.joint_1
current_j2 = joints.joint_2
current_j3 = joints.joint_3
current_j4 = joints.joint_4
current_j5 = joints.joint_5
current_j6 = joints.joint_6

print(f"\nCurrent position: J1={current_j1/1000:.1f} J2={current_j2/1000:.1f} J3={current_j3/1000:.1f} J4={current_j4/1000:.1f} J5={current_j5/1000:.1f} J6={current_j6/1000:.1f}")

# Positions relative to home
positions = [
    ("Home",     [0, 0, 0, 0, 0, 0]),
    ("J1 +20",   [20000, 0, 0, 0, 0, 0]),
    ("J1 -20",   [-20000, 0, 0, 0, 0, 0]),
    ("Home",     [0, 0, 0, 0, 0, 0]),
]

print("\n" + "=" * 60)
print("Will move through positions. Press Ctrl+C to abort.")
print("=" * 60)
time.sleep(2)

try:
    for pos_name, target in positions:
        print(f"\n>>> Moving to {pos_name}: {[t/1000 for t in target]} deg")

        # Move for 4 seconds
        for i in range(200):
            # Keep calling EnablePiper and mode control (like gamepad does)
            if i % 25 == 0:
                piper.EnablePiper()

            piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            piper.JointCtrl(*target)
            time.sleep(0.02)

            # Print progress
            if i % 50 == 0:
                joints = piper.GetArmJointMsgs().joint_state
                print(f"    J1={joints.joint_1/1000:6.1f} J2={joints.joint_2/1000:6.1f} J3={joints.joint_3/1000:6.1f}")

        print(f"    Done!")
        time.sleep(0.3)

    print("\n" + "=" * 60)
    print("TEST COMPLETE!")
    print("=" * 60)

except KeyboardInterrupt:
    print("\nAborted!")

print("Arm stays enabled.")
