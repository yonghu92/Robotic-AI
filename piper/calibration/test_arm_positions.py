#!/usr/bin/env python3
"""
Simple Arm Position Test - Using Joint Control (like gamepad)

This tests if the arm can move to known joint positions.
Uses the same reliable method as the gamepad controller.

Press 1-4 to move to test positions, h for home, q to quit
"""

import time
import sys

sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')

from piper_sdk import C_PiperInterface_V2


def main():
    print("=" * 60)
    print("  SIMPLE ARM POSITION TEST (Joint Control)")
    print("=" * 60)

    # Connect to arm (use V2 interface like gamepad)
    print("\nConnecting to arm...")
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()
    time.sleep(0.5)

    # Check status
    status = piper.GetArmStatus()
    print(f"Control mode: {status.arm_status.ctrl_mode}")
    print(f"Arm status: {status.arm_status.arm_status}")

    # Clear emergency stop if needed
    if status.arm_status.arm_status == 1:
        print("Arm in EMERGENCY_STOP - clearing...")
        piper.EmergencyStop(0x02)
        time.sleep(1.0)

    # Step 1: Set CAN control mode (must do this repeatedly!)
    print("\nSetting CAN control mode...")
    for i in range(50):
        piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
        time.sleep(0.1)
        if piper.GetArmStatus().arm_status.ctrl_mode == 1:
            print("CAN mode activated!")
            break

    # Step 2: Enable all motors
    print("Enabling motors...")
    for i in range(100):
        piper.EnableArm(7)
        time.sleep(0.1)
        enable_status = piper.GetArmEnableStatus()
        if all(enable_status):
            print(f"All motors enabled!")
            break
        if i % 20 == 0:
            print(f"  Enabling... {enable_status}")

    # Define 4 test joint positions (in degrees * 1000 = millidegrees)
    # These are safe positions within the arm's range
    # Format: [J1, J2, J3, J4, J5, J6]

    test_positions = {
        '1': {'name': 'Position 1 (Front-Left)',  'joints': [30000, -20000, 20000, 0, 45000, 0]},      # J1=30°, J2=-20°, etc
        '2': {'name': 'Position 2 (Front-Right)', 'joints': [-30000, -20000, 20000, 0, 45000, 0]},     # J1=-30°
        '3': {'name': 'Position 3 (Back-Right)',  'joints': [-30000, -40000, 40000, 0, 45000, 0]},     # J2=-40°, J3=40°
        '4': {'name': 'Position 4 (Back-Left)',   'joints': [30000, -40000, 40000, 0, 45000, 0]},
    }

    home_joints = [0, 0, 0, 0, 0, 0]
    current_joints = list(home_joints)

    print("\n" + "=" * 60)
    print("Test positions (joint angles in degrees):")
    for key, pos in test_positions.items():
        joints_deg = [j/1000 for j in pos['joints']]
        print(f"  {key}: {pos['name']}")
        print(f"     J1={joints_deg[0]:.0f}° J2={joints_deg[1]:.0f}° J3={joints_deg[2]:.0f}° J4={joints_deg[3]:.0f}° J5={joints_deg[4]:.0f}° J6={joints_deg[5]:.0f}°")
    print("=" * 60)
    print("\nControls:")
    print("  1-4 = Move to test position")
    print("  h   = Go home (all joints to 0)")
    print("  g   = Open gripper")
    print("  c   = Close gripper")
    print("  q   = Quit")
    print("=" * 60)

    def move_to_joints(target_joints, speed=30):
        """Move to target joint position (sends commands continuously like gamepad)"""
        print(f"Moving to: {[j/1000 for j in target_joints]} degrees...")

        for i in range(200):  # Send commands for ~4 seconds
            # Keep sending mode control
            piper.MotionCtrl_2(0x01, 0x01, speed, 0x00)

            # Send joint command
            piper.JointCtrl(*target_joints)

            time.sleep(0.02)

            # Check if close to target every 50 iterations
            if i % 50 == 0 and i > 0:
                joints = piper.GetArmJointMsgs().joint_state
                current = [
                    joints.joint_1,
                    joints.joint_2,
                    joints.joint_3,
                    joints.joint_4,
                    joints.joint_5,
                    joints.joint_6,
                ]
                # Check if within 2 degrees of target
                if all(abs(current[j] - target_joints[j]) < 2000 for j in range(6)):
                    print("Position reached!")
                    return True

        print("Movement complete (timeout)")
        return True

    def control_gripper(opening):
        """Control gripper: 0=closed, 70000=fully open"""
        print(f"Gripper: {'OPEN' if opening > 30000 else 'CLOSED'}")
        for _ in range(20):
            piper.GripperCtrl(opening, 500, 0x01, 0)
            time.sleep(0.02)

    # Start at home
    print("\nMoving to home position...")
    move_to_joints(home_joints)

    try:
        while True:
            key = input("\nCommand (1-4, h, g, c, q): ").strip().lower()

            if key == 'q':
                print("Quitting (arm stays enabled)...")
                break
            elif key == 'h':
                move_to_joints(home_joints)
            elif key == 'g':
                control_gripper(70000)  # Open
            elif key == 'c':
                control_gripper(5000)   # Close
            elif key in test_positions:
                pos = test_positions[key]
                print(f"\n>>> Moving to {pos['name']}")
                move_to_joints(pos['joints'])
            else:
                print("Unknown command. Use 1-4, h, g, c, or q")

    except KeyboardInterrupt:
        print("\nInterrupted")

    print("\nDone! Arm stays enabled.")


if __name__ == "__main__":
    main()
