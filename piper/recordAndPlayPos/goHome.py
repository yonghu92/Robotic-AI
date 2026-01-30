#!/usr/bin/env python3
# -*-coding:utf8-*-
# Go to home position
import time
from piper_sdk import C_PiperInterface_V2

if __name__ == "__main__":
    print("=== Piper Arm Go Home Script ===")

    # Initialize and connect
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()
    time.sleep(0.5)

    # Check current status
    status = piper.GetArmStatus()
    print(f"Current control mode: {status.arm_status.ctrl_mode}")
    print(f"Arm status: {status.arm_status.arm_status}")

    # Clear emergency stop if arm is in that state
    if status.arm_status.arm_status == 1:  # EMERGENCY_STOP
        response = input("\nArm is in EMERGENCY_STOP state. Clear it? (y/n): ").strip().lower()
        if response == 'y':
            piper.EmergencyStop(0x02)  # Clear emergency stop
            time.sleep(1.0)
            print("Emergency stop cleared!")
        else:
            print("Cannot proceed with emergency stop active. Exiting.")
            exit(1)

    # Step 1: Set to CAN control mode
    print("\nStep 1: Setting CAN control mode...")
    for i in range(50):
        piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
        time.sleep(0.1)
        if piper.GetArmStatus().arm_status.ctrl_mode == 1:
            print("CAN mode activated!")
            break
    else:
        print("WARNING: Could not switch to CAN mode, continuing anyway...")

    # Step 2: Enable all motors
    print("Step 2: Enabling motors...")
    for i in range(100):
        piper.EnableArm(7)  # Enable all 7 motors (6 joints + gripper)
        time.sleep(0.1)
        enable_status = piper.GetArmEnableStatus()
        if all(enable_status):
            print(f"All motors enabled: {enable_status}")
            break
        if i % 10 == 0:
            print(f"Enabling... attempt {i+1}, status: {enable_status}")
    else:
        print(f"WARNING: Not all motors enabled: {enable_status}")
        print("The arm may need to be manually moved to a safe position first.")
        print("Try manually moving the arm closer to an upright position.")
        exit(1)

    # Step 3: Move to home position (all joints to 0)
    print("\nStep 3: Moving to home position...")
    print("WARNING: Arm will move! Make sure the area is clear.")
    input("Press Enter to continue or Ctrl+C to cancel...")

    home_joints = [0, 0, 0, 0, 0, 0]  # All joints at 0 degrees

    for i in range(500):
        piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
        piper.JointCtrl(*home_joints)
        time.sleep(0.02)

        # Check if we're close to home
        joints = piper.GetArmJointMsgs().joint_state
        current = [
            joints.joint_1 / 1000,
            joints.joint_2 / 1000,
            joints.joint_3 / 1000,
            joints.joint_4 / 1000,
            joints.joint_5 / 1000,
            joints.joint_6 / 1000,
        ]

        if i % 50 == 0:
            print(f"Current position: {[round(j, 1) for j in current]} deg")

        # Check if close enough to home (within 5 degrees)
        if all(abs(c) < 5 for c in current):
            print("\n=== Arm is at home position! ===")
            break
    else:
        print("\nTimeout - arm may not have reached home position")
        joints = piper.GetArmJointMsgs().joint_state
        print(f"Final position: joint1={joints.joint_1/1000:.1f}, joint2={joints.joint_2/1000:.1f}, "
              f"joint3={joints.joint_3/1000:.1f}, joint4={joints.joint_4/1000:.1f}, "
              f"joint5={joints.joint_5/1000:.1f}, joint6={joints.joint_6/1000:.1f}")

    # Optional: Emergency stop
    response = input("\nActivate emergency stop? (y/n): ").strip().lower()
    if response == 'y':
        piper.EmergencyStop(0x01)  # Trigger emergency stop
        print("Emergency stop activated!")
    else:
        print("Emergency stop skipped.")

    print("\nDone!")
