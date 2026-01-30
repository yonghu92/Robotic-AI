#!/usr/bin/env python3
# -*-coding:utf8-*-
"""
Play Trajectory + Gamepad Adjustment

This script:
1. Plays back a recorded trajectory from CSV
2. After reaching position, asks if you want gamepad control
3. Allows fine adjustments with the gamepad + RGI gripper control

Based on: playTrajectory_new_en.py + rotation_arm_gamepad.py
"""

import os
import time
import csv
import json
import pygame
import serial
import struct
import threading
from piper_sdk import *

# ============ Configuration ============
CSV_PATH = os.path.join(os.path.dirname(__file__), "../piper/recordAndPlayTraj/trajectory.csv")
POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "saved_positions.json")
RGI_SERIAL_PORT = '/dev/ttyUSB1'
RGI_BAUDRATE = 115200
STEP_SIZES = [1, 10, 90, 180, 360, 720, 1080]

# Playback settings
MOVE_SPD_RATE = 50  # Motion speed percentage
TIMEOUT = 5.0


# ============ RGI Gripper Class ============
class RGIGripper:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.thread = None
        self.cmd_open = False
        self.cmd_close = False
        self.cmd_rotate_ccw = False
        self.cmd_rotate_cw = False
        self.rotation_step = 1
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
            print(f"[WARN] RGI: {e}")
            return False

    def initialize(self):
        self.write_reg(0x0100, 0xA5)
        time.sleep(0.5)
        self.write_reg(0x0104, 100)
        self.write_reg(0x0101, 100)
        self.write_reg(0x0107, 100)
        self.write_reg(0x0108, 100)

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
        last_status = 0
        while self.running:
            with self.lock:
                cmd_open = self.cmd_open
                cmd_close = self.cmd_close
                cmd_ccw = self.cmd_rotate_ccw
                cmd_cw = self.cmd_rotate_cw
                step = self.rotation_step

            if cmd_open:
                self.write_reg(0x0103, 1000)
            elif cmd_close:
                self.write_reg(0x0103, 0)

            if cmd_ccw and not cmd_cw:
                self.write_reg(0x0109, -step)
            elif cmd_cw and not cmd_ccw:
                self.write_reg(0x0109, step)

            now = time.time()
            if now - last_status >= 0.3:
                pos = self.read_reg(0x0103)
                angle = self.read_reg(0x0208)
                with self.lock:
                    if pos is not None:
                        self.gripper_pos = pos
                    if angle is not None:
                        self.rotation_angle = angle
                last_status = now

            time.sleep(0.02)

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

    def close_gripper(self):
        """Close gripper (thread-safe)"""
        with self.lock:
            if self.ser:
                cmd = self.build_cmd(1, 0x06, 0x0103, 0)
                self.ser.reset_input_buffer()
                self.ser.write(cmd)
                time.sleep(0.02)
                try:
                    self.ser.read(100)
                except:
                    pass

    def open_gripper(self):
        """Open gripper (thread-safe)"""
        with self.lock:
            if self.ser:
                cmd = self.build_cmd(1, 0x06, 0x0103, 1000)
                self.ser.reset_input_buffer()
                self.ser.write(cmd)
                time.sleep(0.02)
                try:
                    self.ser.read(100)
                except:
                    pass

    def rotate(self, degrees):
        """Rotate gripper by specified degrees (thread-safe)"""
        with self.lock:
            if self.ser:
                value = int(degrees)
                if value < 0:
                    value = value & 0xFFFF
                cmd = self.build_cmd(1, 0x06, 0x0109, value)
                self.ser.reset_input_buffer()
                self.ser.write(cmd)
                time.sleep(0.02)
                try:
                    self.ser.read(100)
                except:
                    pass


# ============ Arm Functions ============
def stop_arm(piper):
    """Stop and reset arm - required when exiting teach mode"""
    piper.EmergencyStop(0x01)
    time.sleep(1.0)
    piper.EmergencyStop(0x02)
    time.sleep(1.0)


def enable_arm(piper):
    """Enable arm for CAN control"""
    print("[..] Enabling arm...")
    enable_timeout = time.time() + 10.0
    while not piper.EnablePiper():
        if time.time() > enable_timeout:
            print("[ERROR] Failed to enable arm")
            return False
        time.sleep(0.1)
    piper.ModeCtrl(0x01, 0x01, MOVE_SPD_RATE, 0x00)
    print("[OK] Arm enabled")
    return True


def get_joints_milli(piper):
    """Get joint positions in milli-degrees"""
    js = piper.GetArmJointMsgs().joint_state
    return [js.joint_1, js.joint_2, js.joint_3, js.joint_4, js.joint_5, js.joint_6]


def get_joints_radians(piper):
    """Get joint positions in radians"""
    js = piper.GetArmJointMsgs().joint_state
    return [getattr(js, f"joint_{i+1}") / 1e3 * 0.0174533 for i in range(6)]


# ============ Saved Positions Functions ============
def load_positions():
    """Load saved positions from JSON file"""
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_positions(positions):
    """Save positions to JSON file"""
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)
    print(f"[OK] Positions saved to {POSITIONS_FILE}")


def record_trajectory(piper, rgi, name):
    """Record a new trajectory using teach mode"""
    import select
    import sys

    # Go home first
    if rgi:
        print("\n[..] Opening gripper...")
        rgi.open_gripper()
        time.sleep(0.5)

    print("[..] Moving to home position first...")
    home_milli = [0, 0, 0, 0, 0, 0]
    for _ in range(150):
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*home_milli)
        time.sleep(0.02)
        current = get_joints_milli(piper)
        if all(abs(c) < 1000 for c in current):
            break
    print("[OK] At home position!")

    # Wait for teach mode
    print("\n" + "=" * 50)
    print("  RECORDING TRAJECTORY: " + name)
    print("=" * 50)
    print("Press the TEACH button on the controller to enter teach mode...")

    timeout = 30.0
    over_time = time.time() + timeout
    while piper.GetArmStatus().arm_status.ctrl_mode != 2:
        if time.time() > over_time:
            print("[ERROR] Teach mode timeout. Make sure to press the TEACH button.")
            return None
        time.sleep(0.01)

    print("[OK] Teach mode detected!")
    print("\nMove the arm through the desired trajectory...")
    input("Press ENTER to START recording: ")

    # Record trajectory
    trajectory = []
    last_pos = get_joints_radians(piper)
    last_time = time.time()
    start_time = last_time
    point_count = 0

    print("\n[RECORDING] Move the arm now! Press ENTER to STOP recording...")

    # Set stdin to non-blocking
    import tty
    import termios
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin.fileno())

        while True:
            # Check if Enter was pressed (non-blocking)
            if select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
                break

            current_pos = get_joints_radians(piper)
            # Record only when position changes
            if current_pos != last_pos:
                wait_time = time.time() - last_time
                trajectory.append([wait_time] + list(current_pos))
                point_count += 1
                last_pos = current_pos
                last_time = time.time()

            elapsed = time.time() - start_time
            print(f"\r[RECORDING] Points: {point_count} | Time: {elapsed:.1f}s | Press ENTER to stop  ", end="")
            time.sleep(0.01)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    print(f"\n\n[OK] Recording complete! Captured {len(trajectory)} points.")

    if len(trajectory) == 0:
        print("[WARN] No movement detected - trajectory is empty!")
        return None

    print("\nPress the TEACH button again to exit teach mode (15s timeout)...")
    exit_timeout = 15.0
    over_time = time.time() + exit_timeout
    while piper.GetArmStatus().arm_status.ctrl_mode == 2:
        if time.time() > over_time:
            print("[WARN] Timeout waiting for teach mode exit - continuing anyway")
            break
        time.sleep(0.01)

    # Re-enable arm for CAN control
    print("[..] Re-enabling arm...")
    stop_arm(piper)

    over_time = time.time() + 5.0
    while piper.GetArmStatus().arm_status.ctrl_mode != 1:
        if time.time() > over_time:
            print("[ERROR] CAN mode switch failed")
            return None
        piper.ModeCtrl(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        time.sleep(0.01)

    enable_arm(piper)

    # Go back to home position
    print("[..] Moving back to home position...")
    home_milli = [0, 0, 0, 0, 0, 0]
    for _ in range(150):
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*home_milli)
        time.sleep(0.02)
        current = get_joints_milli(piper)
        if all(abs(c) < 1000 for c in current):
            break
    print("[OK] Back at home position!")

    return trajectory


def list_positions(positions):
    """Display all saved trajectories"""
    if not positions:
        print("\n[INFO] No saved trajectories yet.")
        return

    print("\n" + "=" * 50)
    print("  SAVED TRAJECTORIES")
    print("=" * 50)
    for i, (name, data) in enumerate(positions.items(), 1):
        trajectory = data.get('trajectory', [])
        recorded_at = data.get('recorded_at', 'unknown')
        print(f"  {i}. {name}")
        print(f"     Points: {len(trajectory)} | Recorded: {recorded_at}")
    print("=" * 50)


def move_to_position(piper, target_rad, timeout=10.0):
    """Move arm to target position (in radians)"""
    # Convert radians to milli-degrees
    target_milli = [round(r / 0.0174533 * 1000) for r in target_rad]

    print(f"[..] Moving to position...")
    start = time.time()

    while time.time() - start < timeout:
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*target_milli)
        time.sleep(0.02)

        current = get_joints_milli(piper)
        errors = [abs(c - t) for c, t in zip(current, target_milli)]

        if all(e < 1000 for e in errors):  # Within 1 degree
            print("[OK] Reached position!")
            return True

    print("[WARN] Timeout - may not have reached exact position")
    return False


def gamepad_control_loop(piper, rgi, joystick):
    """Run gamepad control loop for fine adjustments"""
    print("\n" + "=" * 60)
    print("  GAMEPAD CONTROL MODE")
    print("=" * 60)
    print("  Left Stick: Joint 1-2 | Right Stick: Joint 3-4")
    print("  D-Pad: Joint 5-6 | LB/RB: Speed | R3: Home")
    print("  X: Open gripper | B: Close gripper")
    print("  LT/RT: Rotate gripper | Y/A: Rotation step")
    print("  START: Exit gamepad mode")
    print("=" * 60 + "\n")

    # Get current joint positions
    joints = get_joints_milli(piper)
    j1, j2, j3, j4, j5, j6 = joints

    # Control parameters
    SPEED = 500
    DEADZONE = 0.1
    STICK_SCALE = 2.0
    speed_multiplier = 1.0
    step_index = 2

    last_lb = last_rb = last_r3 = last_y = last_a = last_start = False

    while True:
        pygame.event.pump()

        # Check START to exit
        start_btn = joystick.get_button(9)
        if start_btn and not last_start:
            print("\n[OK] Exiting gamepad mode")
            break
        last_start = start_btn

        # D-Pad
        if joystick.get_numhats() > 0:
            hat = joystick.get_hat(0)
            dpad_x, dpad_y = hat[0], hat[1]
        else:
            dpad_x, dpad_y = 0, 0

        # Left Stick
        stick_x = joystick.get_axis(0) if joystick.get_numaxes() >= 1 else 0
        stick_y = joystick.get_axis(1) if joystick.get_numaxes() >= 2 else 0
        if abs(stick_x) < DEADZONE: stick_x = 0
        if abs(stick_y) < DEADZONE: stick_y = 0

        # Right Stick
        right_x = joystick.get_axis(2) if joystick.get_numaxes() >= 3 else 0
        right_y = -joystick.get_axis(3) if joystick.get_numaxes() >= 4 else 0
        if abs(right_x) < DEADZONE: right_x = 0
        if abs(right_y) < DEADZONE: right_y = 0

        # Speed control (LB/RB)
        lb = joystick.get_button(4)
        rb = joystick.get_button(5)
        if lb and not last_lb:
            speed_multiplier = max(0.25, speed_multiplier - 0.25)
        if rb and not last_rb:
            speed_multiplier = min(1.0, speed_multiplier + 0.25)
        last_lb, last_rb = lb, rb

        # Update joints
        if stick_x: j1 += int(stick_x * SPEED * STICK_SCALE * speed_multiplier)
        if stick_y: j2 -= int(stick_y * SPEED * STICK_SCALE * speed_multiplier)
        if right_y: j3 += int(right_y * SPEED * STICK_SCALE * speed_multiplier)
        if right_x: j4 += int(right_x * SPEED * STICK_SCALE * speed_multiplier)
        if dpad_y:  j5 += int(dpad_y * SPEED * speed_multiplier)
        if dpad_x:  j6 += int(dpad_x * SPEED * speed_multiplier)

        # Home (R3)
        r3 = joystick.get_button(10) if joystick.get_numbuttons() > 10 else False
        if not r3:
            r3 = joystick.get_button(9)  # Some controllers use button 9
        # Actually R3 is usually button 11 on some, let's try a different approach
        # Skip home for now to avoid confusion

        # RGI step size (Y/A)
        if rgi:
            y_btn = joystick.get_button(3)
            a_btn = joystick.get_button(1)
            if y_btn and not last_y:
                step_index = min(len(STEP_SIZES) - 1, step_index + 1)
            if a_btn and not last_a:
                step_index = max(0, step_index - 1)
            last_y, last_a = y_btn, a_btn

            # RGI commands
            x_btn = joystick.get_button(0)
            b_btn = joystick.get_button(2)
            lt_btn = joystick.get_button(6)
            rt_btn = joystick.get_button(7)
            rgi.set_commands(x_btn, b_btn, lt_btn, rt_btn, STEP_SIZES[step_index])

        # Send arm commands
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(j1, j2, j3, j4, j5, j6)

        # Display
        grip_pos, rot_angle = rgi.get_status() if rgi else (0, 0)
        print(f"\rJ1:{j1/1000:+5.1f} J2:{j2/1000:+5.1f} J3:{j3/1000:+5.1f} "
              f"J4:{j4/1000:+5.1f} J5:{j5/1000:+5.1f} J6:{j6/1000:+5.1f} | "
              f"Spd:{int(speed_multiplier*100)}% | Press START to exit  ", end="")

        time.sleep(0.02)


# ============ Helper Function ============
def go_home(piper, rgi):
    """Move arm to home position with gripper open"""
    if rgi:
        print("\n[..] Opening gripper...")
        rgi.open_gripper()
        time.sleep(0.5)
    print("[..] Moving to home position...")
    home_milli = [0, 0, 0, 0, 0, 0]
    for _ in range(150):
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*home_milli)
        time.sleep(0.02)
        current = get_joints_milli(piper)
        if all(abs(c) < 1000 for c in current):
            break
    print("[OK] At home position!")


def play_trajectory(piper, trajectory):
    """Play a recorded trajectory"""
    print(f"\n[..] Playing trajectory ({len(trajectory)} points)...")

    for i, pos in enumerate(trajectory):
        wait_time = pos[0]
        target_joints = pos[1:7]

        print(f"\r[{i+1}/{len(trajectory)}] Moving... wait={wait_time:.2f}s  ", end="")

        joints_milli = [round(r / 0.0174533 * 1000) for r in target_joints]
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*joints_milli)

        if i < len(trajectory) - 1:
            time.sleep(wait_time)
        else:
            time.sleep(0.5)

    print("\n[OK] Trajectory complete!")


def position_actions_menu(rgi):
    """Position actions menu for gripper control"""
    if not rgi:
        return

    while True:
        print("\n" + "=" * 40)
        print("  POSITION ACTIONS")
        print("=" * 40)
        print("  r  - Rotate gripper")
        print("  c  - Close gripper")
        print("  o  - Open gripper")
        print("  d  - Done (continue to next options)")
        print("=" * 40)

        action = input("\nAction: ").strip().lower()

        if action == 'r':
            try:
                degrees = input("Enter rotation degrees (e.g., 360): ").strip()
                degrees = int(degrees)
            except:
                degrees = 360
                print(f"[WARN] Invalid input, using {degrees}°")

            direction = input("Direction - clockwise (cw) or counter-clockwise (ccw)? ").strip().lower()
            if direction == 'ccw':
                degrees = -degrees

            dir_str = "CCW" if degrees < 0 else "CW"
            print(f"[..] Performing {abs(degrees)}° rotation ({dir_str})...")
            rgi.rotate(degrees)
            time.sleep(max(1.0, abs(degrees) / 180.0))
            print("[OK] Rotation complete!")

        elif action == 'c':
            print("[..] Closing gripper...")
            rgi.close_gripper()
            time.sleep(0.5)
            print("[OK] Gripper closed!")

        elif action == 'o':
            print("[..] Opening gripper...")
            rgi.open_gripper()
            time.sleep(0.5)
            print("[OK] Gripper opened!")

        elif action == 'd':
            break

        else:
            print("[?] Unknown action")


# ============ Main ============
if __name__ == "__main__":
    print("=" * 60)
    print("  PLAY TRAJECTORY + POSITION CONTROLLER")
    print("=" * 60)

    # Load saved trajectories
    saved_positions = load_positions()
    print(f"[OK] Loaded {len(saved_positions)} saved trajectories")

    # Load trajectory (optional - may not exist)
    track = None
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r') as f:
            track = list(csv.reader(f))
            if track:
                track = [[float(j) for j in i] for i in track]
                print(f"[OK] Loaded trajectory with {len(track)} points")
            else:
                track = None
    else:
        print("[INFO] No default trajectory file found")

    # Initialize pygame and joystick
    pygame.init()
    pygame.joystick.init()

    joystick = None
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"[OK] Gamepad: {joystick.get_name()}")
    else:
        print("[WARN] No gamepad found")

    # Connect RGI gripper
    rgi = RGIGripper(RGI_SERIAL_PORT, RGI_BAUDRATE)
    if rgi.connect():
        print("[OK] RGI Gripper connected")
        rgi.initialize()
        rgi.start()
    else:
        rgi = None

    # Connect to arm
    print("[..] Connecting to Piper arm...")
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()
    time.sleep(0.1)
    print("[OK] Piper arm connected")

    # Ensure arm is in CAN mode (exit teach mode if needed)
    print("\n[..] Ensuring CAN control mode...")
    current_mode = piper.GetArmStatus().arm_status.ctrl_mode
    print(f"[INFO] Current control mode: {current_mode}")

    if current_mode != 1:
        print("[..] Stopping arm (exiting teach mode)...")
        stop_arm(piper)
        time.sleep(0.5)

    # Try multiple times to switch to CAN mode
    for attempt in range(3):
        print(f"[..] Attempt {attempt + 1} to switch to CAN mode...")
        over_time = time.time() + 10.0  # 10 second timeout per attempt

        while piper.GetArmStatus().arm_status.ctrl_mode != 1:
            if time.time() > over_time:
                break
            piper.ModeCtrl(0x01, 0x01, MOVE_SPD_RATE, 0x00)
            time.sleep(0.05)

        if piper.GetArmStatus().arm_status.ctrl_mode == 1:
            print("[OK] CAN mode active")
            break
        else:
            print(f"[WARN] Attempt {attempt + 1} failed, retrying...")
            stop_arm(piper)
            time.sleep(1.0)
    else:
        print("[ERROR] CAN mode switch failed after 3 attempts")
        print("[TIP] Try power cycling the arm or check CAN connection")
        exit(1)

    enable_arm(piper)

    # Go home first
    go_home(piper, rgi)

    # Main menu loop
    try:
        while True:
            print("\n" + "=" * 60)
            print("  MAIN MENU")
            print("=" * 60)
            if track:
                print("  1 - Play default trajectory (from CSV)")
            print("  2 - Record new trajectory (teach mode)")
            print("  3 - List saved trajectories")
            print("  4 - Play saved trajectory")
            print("  5 - Manage trajectories (rename/delete/view)")
            print("  g - Gamepad control")
            print("  h - Go home")
            print("  q - Quit")
            print("=" * 60)

            choice = input("\nChoice: ").strip().lower()

            # ---- Play default trajectory ----
            if choice == '1' and track:
                print(f"\n" + "=" * 60)
                print(f"  PLAYING TRAJECTORY ({len(track)} points)")
                print("=" * 60)

                for i, pos in enumerate(track):
                    wait_time = pos[0]
                    target_joints = pos[1:7]

                    print(f"[{i+1}/{len(track)}] Moving... wait={wait_time:.2f}s")

                    joints_milli = [round(r / 0.0174533 * 1000) for r in target_joints]
                    piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
                    piper.JointCtrl(*joints_milli)

                    if i < len(track) - 1:
                        time.sleep(wait_time)
                    else:
                        time.sleep(0.5)

                print("\n[OK] Trajectory complete!")
                position_actions_menu(rgi)

            # ---- Record new trajectory ----
            elif choice == '2':
                name = input("\nEnter name for this trajectory: ").strip()
                if not name:
                    print("[ERROR] Name cannot be empty")
                    continue

                if name in saved_positions:
                    overwrite = input(f"Trajectory '{name}' already exists. Overwrite? (y/n): ").strip().lower()
                    if overwrite != 'y':
                        continue

                trajectory = record_trajectory(piper, rgi, name)
                if trajectory:
                    saved_positions[name] = {
                        'trajectory': trajectory,
                        'recorded_at': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    save_positions(saved_positions)
                    print(f"\n[OK] Trajectory '{name}' saved with {len(trajectory)} points!")

            # ---- List saved trajectories ----
            elif choice == '3':
                list_positions(saved_positions)

            # ---- Play saved trajectory ----
            elif choice == '4':
                if not saved_positions:
                    print("\n[INFO] No saved trajectories. Record one first.")
                    continue

                list_positions(saved_positions)
                pos_names = list(saved_positions.keys())

                print("\nEnter trajectory number or name (or 'c' to cancel):")
                sel = input("Selection: ").strip()

                if sel.lower() == 'c':
                    continue

                # Try as number first
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(pos_names):
                        sel_name = pos_names[idx]
                    else:
                        print("[ERROR] Invalid number")
                        continue
                except ValueError:
                    # Try as name
                    if sel in saved_positions:
                        sel_name = sel
                    else:
                        print(f"[ERROR] Trajectory '{sel}' not found")
                        continue

                print(f"\n[..] Playing trajectory: {sel_name}")
                trajectory = saved_positions[sel_name]['trajectory']
                play_trajectory(piper, trajectory)
                position_actions_menu(rgi)

            # ---- Manage trajectories ----
            elif choice == '5':
                if not saved_positions:
                    print("\n[INFO] No saved trajectories to manage.")
                    continue

                while True:
                    list_positions(saved_positions)
                    pos_names = list(saved_positions.keys())

                    print("\n  MANAGE TRAJECTORIES")
                    print("  " + "-" * 30)
                    print("  d - Delete a trajectory")
                    print("  r - Rename a trajectory")
                    print("  v - View trajectory details")
                    print("  x - Re-record (replace) a trajectory")
                    print("  b - Back to main menu")

                    action = input("\nAction: ").strip().lower()

                    if action == 'b':
                        break

                    elif action == 'd':
                        # Delete
                        sel = input("Enter trajectory number or name to delete (or 'c' to cancel): ").strip()
                        if sel.lower() == 'c':
                            continue

                        try:
                            idx = int(sel) - 1
                            if 0 <= idx < len(pos_names):
                                sel_name = pos_names[idx]
                            else:
                                print("[ERROR] Invalid number")
                                continue
                        except ValueError:
                            if sel in saved_positions:
                                sel_name = sel
                            else:
                                print(f"[ERROR] Trajectory '{sel}' not found")
                                continue

                        confirm = input(f"Delete trajectory '{sel_name}'? (y/n): ").strip().lower()
                        if confirm == 'y':
                            del saved_positions[sel_name]
                            save_positions(saved_positions)
                            print(f"[OK] Trajectory '{sel_name}' deleted!")
                            if not saved_positions:
                                break

                    elif action == 'r':
                        # Rename
                        sel = input("Enter trajectory number or name to rename (or 'c' to cancel): ").strip()
                        if sel.lower() == 'c':
                            continue

                        try:
                            idx = int(sel) - 1
                            if 0 <= idx < len(pos_names):
                                sel_name = pos_names[idx]
                            else:
                                print("[ERROR] Invalid number")
                                continue
                        except ValueError:
                            if sel in saved_positions:
                                sel_name = sel
                            else:
                                print(f"[ERROR] Trajectory '{sel}' not found")
                                continue

                        new_name = input(f"Enter new name for '{sel_name}': ").strip()
                        if not new_name:
                            print("[ERROR] Name cannot be empty")
                            continue
                        if new_name in saved_positions:
                            print(f"[ERROR] Trajectory '{new_name}' already exists")
                            continue

                        saved_positions[new_name] = saved_positions.pop(sel_name)
                        save_positions(saved_positions)
                        print(f"[OK] Renamed '{sel_name}' to '{new_name}'")

                    elif action == 'v':
                        # View details
                        sel = input("Enter trajectory number or name to view (or 'c' to cancel): ").strip()
                        if sel.lower() == 'c':
                            continue

                        try:
                            idx = int(sel) - 1
                            if 0 <= idx < len(pos_names):
                                sel_name = pos_names[idx]
                            else:
                                print("[ERROR] Invalid number")
                                continue
                        except ValueError:
                            if sel in saved_positions:
                                sel_name = sel
                            else:
                                print(f"[ERROR] Trajectory '{sel}' not found")
                                continue

                        data = saved_positions[sel_name]
                        traj = data.get('trajectory', [])
                        print(f"\n" + "=" * 60)
                        print(f"  TRAJECTORY: {sel_name}")
                        print("=" * 60)
                        print(f"  Recorded: {data.get('recorded_at', 'unknown')}")
                        print(f"  Total points: {len(traj)}")
                        if traj:
                            total_time = sum(p[0] for p in traj)
                            print(f"  Total duration: {total_time:.2f}s")
                            print(f"\n  First 5 points:")
                            for i, pt in enumerate(traj[:5]):
                                joints = [f"{j:.3f}" for j in pt[1:7]]
                                print(f"    {i+1}. wait={pt[0]:.3f}s joints=[{', '.join(joints)}]")
                            if len(traj) > 5:
                                print(f"    ... and {len(traj)-5} more points")
                        print("=" * 60)
                        input("\nPress ENTER to continue...")

                    elif action == 'x':
                        # Re-record (replace)
                        sel = input("Enter trajectory number or name to replace (or 'c' to cancel): ").strip()
                        if sel.lower() == 'c':
                            continue

                        try:
                            idx = int(sel) - 1
                            if 0 <= idx < len(pos_names):
                                sel_name = pos_names[idx]
                            else:
                                print("[ERROR] Invalid number")
                                continue
                        except ValueError:
                            if sel in saved_positions:
                                sel_name = sel
                            else:
                                print(f"[ERROR] Trajectory '{sel}' not found")
                                continue

                        confirm = input(f"Re-record trajectory '{sel_name}'? This will replace it. (y/n): ").strip().lower()
                        if confirm != 'y':
                            continue

                        trajectory = record_trajectory(piper, rgi, sel_name)
                        if trajectory:
                            saved_positions[sel_name] = {
                                'trajectory': trajectory,
                                'recorded_at': time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            save_positions(saved_positions)
                            print(f"\n[OK] Trajectory '{sel_name}' replaced with {len(trajectory)} points!")

                    else:
                        print("[?] Unknown action")

            # ---- Gamepad control ----
            elif choice == 'g':
                if joystick:
                    gamepad_control_loop(piper, rgi, joystick)
                    go_home(piper, rgi)
                else:
                    print("[ERROR] No gamepad connected")

            # ---- Go home ----
            elif choice == 'h':
                go_home(piper, rgi)

            # ---- Quit ----
            elif choice == 'q':
                print("\n[..] Going home before quitting...")
                go_home(piper, rgi)
                break

            else:
                print("[?] Unknown option")

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Going home before stopping...")
        try:
            go_home(piper, rgi)
        except:
            pass

    # Cleanup
    print("[..] Shutting down...")
    if rgi:
        rgi.stop()
    pygame.quit()
    print("[OK] Done!")
