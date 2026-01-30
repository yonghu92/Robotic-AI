#!/usr/bin/env python3
"""
Continuous Arm Control Test - Works exactly like gamepad

Runs in a continuous loop sending commands.
Press keys while it's running (non-blocking input).
"""

import time
import sys
import select
import tty
import termios

sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')

from piper_sdk import C_PiperInterface_V2


def get_key_nonblocking():
    """Get key press without blocking"""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


def main():
    print("=" * 60)
    print("  CONTINUOUS ARM CONTROL TEST")
    print("=" * 60)

    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Set terminal to raw mode for non-blocking input
        tty.setcbreak(sys.stdin.fileno())

        # Connect to arm
        print("\nConnecting to arm...")
        piper = C_PiperInterface_V2("can0")
        piper.ConnectPort()
        time.sleep(0.5)

        # Check and clear emergency stop
        status = piper.GetArmStatus()
        print(f"Arm status: {status.arm_status.arm_status}")
        if status.arm_status.arm_status == 1:
            print("Clearing emergency stop...")
            piper.EmergencyStop(0x02)
            time.sleep(1.0)

        # Initialize CAN mode
        print("Setting CAN mode...")
        for i in range(50):
            piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            time.sleep(0.1)
            if piper.GetArmStatus().arm_status.ctrl_mode == 1:
                print("CAN mode OK!")
                break

        # Enable motors
        print("Enabling motors...")
        for i in range(100):
            piper.EnableArm(7)
            time.sleep(0.1)
            if all(piper.GetArmEnableStatus()):
                print("Motors enabled!")
                break

        # Current target position (start at 0)
        target = [0, 0, 0, 0, 0, 0]
        gripper = 35000  # Half open

        # Test positions
        positions = {
            '1': [20000, -15000, 15000, 0, 30000, 0],   # Small movements
            '2': [-20000, -15000, 15000, 0, 30000, 0],
            '3': [-20000, -30000, 30000, 0, 30000, 0],
            '4': [20000, -30000, 30000, 0, 30000, 0],
            'h': [0, 0, 0, 0, 0, 0],  # Home
        }

        print("\n" + "=" * 60)
        print("CONTROLS (press while running):")
        print("  1-4 = Test positions")
        print("  h   = Home position")
        print("  g   = Open gripper")
        print("  c   = Close gripper")
        print("  q   = Quit")
        print("=" * 60)
        print("\nRunning... (commands sent continuously)")

        running = True
        loop_count = 0

        while running:
            # Check for key press (non-blocking)
            key = get_key_nonblocking()

            if key:
                if key == 'q':
                    print("\nQuitting...")
                    running = False
                elif key == 'g':
                    gripper = 70000
                    print("\n>>> GRIPPER OPEN")
                elif key == 'c':
                    gripper = 5000
                    print("\n>>> GRIPPER CLOSE")
                elif key in positions:
                    target = positions[key]
                    name = "HOME" if key == 'h' else f"Position {key}"
                    print(f"\n>>> Moving to {name}: {[t/1000 for t in target]} deg")

            # CONTINUOUSLY send commands (this is the key!)
            piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            piper.JointCtrl(*target)
            piper.GripperCtrl(gripper, 500, 0x01, 0)

            # Print status every 2 seconds
            if loop_count % 100 == 0:
                joints = piper.GetArmJointMsgs().joint_state
                current = [joints.joint_1, joints.joint_2, joints.joint_3,
                          joints.joint_4, joints.joint_5, joints.joint_6]
                current_deg = [c/1000 for c in current]
                target_deg = [t/1000 for t in target]
                print(f"\rCurrent: [{current_deg[0]:6.1f}, {current_deg[1]:6.1f}, {current_deg[2]:6.1f}, {current_deg[3]:6.1f}, {current_deg[4]:6.1f}, {current_deg[5]:6.1f}] Target: [{target_deg[0]:6.1f}, {target_deg[1]:6.1f}, {target_deg[2]:6.1f}, {target_deg[3]:6.1f}, {target_deg[4]:6.1f}, {target_deg[5]:6.1f}]", end="", flush=True)

            loop_count += 1
            time.sleep(0.02)  # 50Hz loop like gamepad

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\nDone! Arm stays enabled.")


if __name__ == "__main__":
    main()
