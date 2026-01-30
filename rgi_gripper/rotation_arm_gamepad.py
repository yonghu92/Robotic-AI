#!/usr/bin/env python3
# -*-coding:utf8-*-
"""
Combined Gamepad Control: Piper Arm + RGI Rotating Gripper

Arm Controls (Piper):
    Left Stick X        : Joint 1 (base rotation)
    Left Stick Y        : Joint 2 (arm lifting)
    Right Stick Y       : Joint 3 (elbow)
    Right Stick X       : Joint 4 (wrist yaw)
    D-Pad UP/DOWN       : Joint 5 (wrist pitch)
    D-Pad LEFT/RIGHT    : Joint 6 (wrist rotation)
    LB (button 4)       : Decrease arm speed
    RB (button 5)       : Increase arm speed
    R3 (button 9)       : Go to home position

RGI Gripper Controls:
    X (button 0)        : OPEN gripper
    B (button 2)        : CLOSE gripper
    LT/L2 (button 6)    : Rotate gripper counterclockwise
    RT/R2 (button 7)    : Rotate gripper clockwise
    Y (button 3)        : Rotation step size UP
    A (button 1)        : Rotation step size DOWN

Press Ctrl+C to stop
"""

import time
import pygame
import serial
import struct
import sys
import threading
from piper_sdk import C_PiperInterface_V2

# RGI Gripper settings
RGI_SERIAL_PORT = '/dev/ttyUSB1'
RGI_BAUDRATE = 115200
STEP_SIZES = [1, 10, 90, 180, 360, 720, 1080]


# ============ RGI Gripper Class (runs in separate thread) ============
class RGIGripper:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.thread = None

        # Commands (set by main thread, executed by RGI thread)
        self.cmd_open = False
        self.cmd_close = False
        self.cmd_rotate_ccw = False
        self.cmd_rotate_cw = False
        self.rotation_step = 1

        # Status (updated by RGI thread, read by main thread)
        self.gripper_pos = 0
        self.rotation_angle = 0
        self.lock = threading.Lock()

    def calc_crc16(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def build_cmd(self, slave_id, func, reg, value):
        if value < 0:
            value = value & 0xFFFF
        cmd = struct.pack('>BBHH', slave_id, func, reg, value)
        crc = self.calc_crc16(cmd)
        return cmd + struct.pack('<H', crc)

    def write_reg(self, reg, value):
        if not self.ser:
            return
        cmd = self.build_cmd(1, 0x06, reg, int(value))
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.005)
        self.ser.read(100)

    def read_reg(self, reg):
        if not self.ser:
            return None
        cmd = self.build_cmd(1, 0x03, reg, 1)
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.005)
        resp = self.ser.read(100)
        if len(resp) >= 7:
            for i in range(len(resp) - 6):
                if resp[i] == 0x01 and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                    val = (resp[i+3] << 8) | resp[i+4]
                    if val > 32767:
                        val -= 65536
                    return val
        return None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"[ERROR] RGI: {e}")
            return False

    def initialize(self):
        self.write_reg(0x0100, 0xA5)  # Initialize
        time.sleep(0.5)
        self.write_reg(0x0104, 100)   # Gripper speed 100%
        self.write_reg(0x0101, 100)   # Gripper force 100%
        self.write_reg(0x0107, 100)   # Rotation speed 100%
        self.write_reg(0x0108, 100)   # Rotation force 100%

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.ser:
            self.ser.close()

    def _run(self):
        """RGI control thread - runs independently from arm control"""
        last_status_read = 0

        while self.running:
            # Process commands
            with self.lock:
                cmd_open = self.cmd_open
                cmd_close = self.cmd_close
                cmd_ccw = self.cmd_rotate_ccw
                cmd_cw = self.cmd_rotate_cw
                step = self.rotation_step

            # Gripper open/close
            if cmd_open:
                self.write_reg(0x0103, 1000)
            elif cmd_close:
                self.write_reg(0x0103, 0)

            # Rotation
            if cmd_ccw and not cmd_cw:
                self.write_reg(0x0109, -step)
            elif cmd_cw and not cmd_ccw:
                self.write_reg(0x0109, step)

            # Read status less frequently (don't slow down rotation)
            now = time.time()
            if now - last_status_read >= 0.3:
                pos = self.read_reg(0x0103)
                angle = self.read_reg(0x0208)
                with self.lock:
                    if pos is not None:
                        self.gripper_pos = pos
                    if angle is not None:
                        self.rotation_angle = angle
                last_status_read = now

            time.sleep(0.02)  # RGI loop runs at 50Hz for smoother rotation

    def set_commands(self, open_grip, close_grip, rotate_ccw, rotate_cw, step):
        with self.lock:
            self.cmd_open = open_grip
            self.cmd_close = close_grip
            self.cmd_rotate_ccw = rotate_ccw
            self.cmd_rotate_cw = rotate_cw
            self.rotation_step = step

    def get_status(self):
        with self.lock:
            return self.gripper_pos, self.rotation_angle


# ============ Main Program ============
def main():
    print("=" * 60)
    print("  Combined Control: Piper Arm + RGI Rotating Gripper")
    print("=" * 60)

    # Initialize pygame and joystick
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("[ERROR] No joystick found!")
        return 1

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"[OK] Gamepad: {joystick.get_name()}")

    # Connect and start RGI Gripper (in separate thread)
    rgi = RGIGripper(RGI_SERIAL_PORT, RGI_BAUDRATE)
    if not rgi.connect():
        pygame.quit()
        return 1
    print(f"[OK] RGI Gripper on {RGI_SERIAL_PORT}")

    print("[..] Initializing RGI Gripper...")
    rgi.initialize()
    rgi.start()  # Start RGI thread
    print("[OK] RGI Gripper running in background thread")

    # Initialize and connect to Piper arm
    print("[..] Connecting to Piper arm...")
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()
    time.sleep(0.5)

    # Check current status
    status = piper.GetArmStatus()
    print(f"[OK] Arm control mode: {status.arm_status.ctrl_mode}")

    # Clear emergency stop if needed
    if status.arm_status.arm_status == 1:
        response = input("\nArm is in EMERGENCY_STOP. Clear it? (y/n): ").strip().lower()
        if response == 'y':
            piper.EmergencyStop(0x02)
            time.sleep(1.0)
            print("[OK] Emergency stop cleared!")
        else:
            rgi.stop()
            pygame.quit()
            return 1

    # Set to CAN control mode
    print("[..] Setting CAN control mode...")
    for i in range(50):
        piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
        time.sleep(0.1)
        if piper.GetArmStatus().arm_status.ctrl_mode == 1:
            print("[OK] CAN mode activated!")
            break

    # Enable all motors
    print("[..] Enabling motors...")
    for i in range(100):
        piper.EnableArm(7)
        time.sleep(0.1)
        enable_status = piper.GetArmEnableStatus()
        if all(enable_status):
            print(f"[OK] All motors enabled!")
            break
        if i % 10 == 0:
            print(f"[..] Enabling... attempt {i+1}")
    else:
        print(f"[ERROR] Not all motors enabled")
        rgi.stop()
        pygame.quit()
        return 1

    # Move to home position
    print("\n[!!] Moving to home position...")
    print("[!!] WARNING: Arm will move!")
    input("Press Enter to continue...")

    home_joints = [0, 0, 0, 0, 0, 0]
    for i in range(500):
        piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
        piper.JointCtrl(*home_joints)
        time.sleep(0.02)
        joints = piper.GetArmJointMsgs().joint_state
        current = [joints.joint_1/1000, joints.joint_2/1000, joints.joint_3/1000,
                   joints.joint_4/1000, joints.joint_5/1000, joints.joint_6/1000]
        if i % 50 == 0:
            print(f"[..] Position: {[round(j, 1) for j in current]}°")
        if all(abs(c) < 5 for c in current):
            print("[OK] Arm at home position!")
            break

    # Re-enable arm
    for i in range(50):
        if piper.EnablePiper():
            break
        time.sleep(0.02)
    piper.ModeCtrl(0x01, 0x01, 30, 0x00)
    time.sleep(0.2)

    # Get current joint positions
    joints = piper.GetArmJointMsgs()
    j1 = joints.joint_state.joint_1
    j2 = joints.joint_state.joint_2
    j3 = joints.joint_state.joint_3
    j4 = joints.joint_state.joint_4
    j5 = joints.joint_state.joint_5
    j6 = joints.joint_state.joint_6

    # Print controls
    print("\n" + "=" * 60)
    print("  ARM: Sticks + D-Pad | LB/RB = Speed | R3 = Home")
    print("  RGI: X=Open B=Close | LT/RT = Rotate | Y/A = Step")
    print(f"  Steps: {STEP_SIZES}°")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")

    # Control parameters (same as original)
    SPEED = 500  # Same as original
    DEADZONE = 0.1
    STICK_SCALE = 2.0

    speed_multiplier = 1.0
    step_index = 2  # Start at 90 degrees

    last_lb = False
    last_rb = False
    last_r3 = False
    last_y = False
    last_a = False

    # Main control loop - ARM ONLY (RGI runs in separate thread)
    try:
        while True:
            pygame.event.pump()

            # === D-Pad ===
            if joystick.get_numhats() > 0:
                hat = joystick.get_hat(0)
                dpad_x, dpad_y = hat[0], hat[1]
            else:
                dpad_x, dpad_y = 0, 0

            # === Left Stick ===
            stick_x = joystick.get_axis(0) if joystick.get_numaxes() >= 1 else 0
            stick_y = joystick.get_axis(1) if joystick.get_numaxes() >= 2 else 0
            if abs(stick_x) < DEADZONE: stick_x = 0
            if abs(stick_y) < DEADZONE: stick_y = 0

            # === Right Stick ===
            right_x = joystick.get_axis(2) if joystick.get_numaxes() >= 3 else 0
            right_y = -joystick.get_axis(3) if joystick.get_numaxes() >= 4 else 0
            if abs(right_x) < DEADZONE: right_x = 0
            if abs(right_y) < DEADZONE: right_y = 0

            # === Arm Speed (LB/RB) ===
            lb = joystick.get_button(4)
            rb = joystick.get_button(5)
            if lb and not last_lb:
                speed_multiplier = max(0.25, speed_multiplier - 0.25)
            if rb and not last_rb:
                speed_multiplier = min(1.0, speed_multiplier + 0.25)
            last_lb, last_rb = lb, rb

            # === Update Joints ===
            if stick_x: j1 += int(stick_x * SPEED * STICK_SCALE * speed_multiplier)
            if stick_y: j2 -= int(stick_y * SPEED * STICK_SCALE * speed_multiplier)
            if right_y: j3 += int(right_y * SPEED * STICK_SCALE * speed_multiplier)
            if right_x: j4 += int(right_x * SPEED * STICK_SCALE * speed_multiplier)
            if dpad_y:  j5 += int(dpad_y * SPEED * speed_multiplier)
            if dpad_x:  j6 += int(dpad_x * SPEED * speed_multiplier)

            # === Home (R3) ===
            r3 = joystick.get_button(9)
            if r3 and not last_r3:
                j1, j2, j3, j4, j5, j6 = 0, 0, 0, 0, 0, 0
            last_r3 = r3

            # === RGI Step Size (Y/A) ===
            y_btn = joystick.get_button(3)
            a_btn = joystick.get_button(1)
            if y_btn and not last_y:
                step_index = min(len(STEP_SIZES) - 1, step_index + 1)
            if a_btn and not last_a:
                step_index = max(0, step_index - 1)
            last_y, last_a = y_btn, a_btn

            # === Send RGI Commands (non-blocking, just set flags) ===
            x_btn = joystick.get_button(0)  # Open
            b_btn = joystick.get_button(2)  # Close
            lt_btn = joystick.get_button(6)  # Rotate CCW
            rt_btn = joystick.get_button(7)  # Rotate CW
            rgi.set_commands(x_btn, b_btn, lt_btn, rt_btn, STEP_SIZES[step_index])

            # === Send Arm Commands ===
            piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            piper.JointCtrl(j1, j2, j3, j4, j5, j6)

            # === Display ===
            grip_pos, rot_angle = rgi.get_status()
            g_str = "OPEN" if grip_pos > 500 else "CLOSED" if grip_pos < 100 else "---"
            r_dir = "<<" if lt_btn else ">>" if rt_btn else "--"

            print(f"\rJ1:{j1/1000:+5.1f} J2:{j2/1000:+5.1f} J3:{j3/1000:+5.1f} J4:{j4/1000:+5.1f} J5:{j5/1000:+5.1f} J6:{j6/1000:+5.1f} | "
                  f"G:{g_str:6s} R:{r_dir}{rot_angle:5d}° S:{STEP_SIZES[step_index]}° | Spd:{int(speed_multiplier*100)}%  ", end="")

            time.sleep(0.02)  # 50Hz - same as original

    except KeyboardInterrupt:
        print("\n\n[STOPPED]")

    # Cleanup
    rgi.stop()

    response = input("\nEmergency stop? (y/n): ").strip().lower()
    if response == 'y':
        piper.EmergencyStop(0x01)
        print("[OK] Emergency stop activated!")

    pygame.quit()
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
