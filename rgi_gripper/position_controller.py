#!/usr/bin/env python3
# -*-coding:utf8-*-
"""
Position Controller - Play Trajectories + Named Positions + Gamepad Adjustment

Features:
1. Play recorded trajectories from CSV
2. Save/load named positions (e.g., "home", "pick", "place")
3. Gamepad control for fine adjustments
4. RGI gripper support

Commands:
    play        - Play the recorded trajectory
    save <name> - Save current arm position with a name
    go <name>   - Move to a saved position
    list        - List all saved positions
    delete <name> - Delete a saved position
    gamepad     - Enter gamepad control mode
    quit        - Exit
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
MOVE_SPD_RATE = 50
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


# ============ Position Storage ============
def load_positions():
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_positions(positions):
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)


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


def get_joints_deg(piper):
    """Get joint positions in degrees"""
    milli = get_joints_milli(piper)
    return [m / 1000.0 for m in milli]


def move_to_joints_deg(piper, target_deg, timeout=10.0):
    """Move arm to target position (in degrees)"""
    target_milli = [int(d * 1000) for d in target_deg]

    print(f"[..] Moving to: {[round(d, 1) for d in target_deg]}°")
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


def play_trajectory(piper, track):
    """Play entire trajectory"""
    print(f"\n[..] Playing trajectory ({len(track)} points)")

    for i, pos in enumerate(track):
        wait_time = pos[0]
        target_rad = pos[1:7]  # 6 joint values in radians

        # Convert radians to milli-degrees
        joints_milli = [round(r / 0.0174533 * 1000) for r in target_rad]

        print(f"  [{i+1}/{len(track)}] wait={wait_time:.2f}s")

        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*joints_milli)

        if i < len(track) - 1:
            time.sleep(wait_time)
        else:
            time.sleep(0.5)

    print("[OK] Trajectory complete!")


def gamepad_control_loop(piper, rgi, joystick):
    """Run gamepad control loop for fine adjustments"""
    print("\n" + "=" * 60)
    print("  GAMEPAD CONTROL MODE")
    print("=" * 60)
    print("  Left Stick: Joint 1-2 | Right Stick: Joint 3-4")
    print("  D-Pad: Joint 5-6 | LB/RB: Speed")
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

    last_lb = last_rb = last_y = last_a = last_start = False

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
        print(f"\rJ1:{j1/1000:+5.1f} J2:{j2/1000:+5.1f} J3:{j3/1000:+5.1f} "
              f"J4:{j4/1000:+5.1f} J5:{j5/1000:+5.1f} J6:{j6/1000:+5.1f} | "
              f"Spd:{int(speed_multiplier*100)}% | START=exit  ", end="")

        time.sleep(0.02)

    # Return final position
    return [j1/1000, j2/1000, j3/1000, j4/1000, j5/1000, j6/1000]


# ============ Main ============
if __name__ == "__main__":
    print("=" * 60)
    print("  POSITION CONTROLLER")
    print("=" * 60)

    # Load trajectory if exists
    track = None
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, 'r') as f:
                track = list(csv.reader(f))
                track = [[float(j) for j in i] for i in track]
            print(f"[OK] Loaded trajectory: {len(track)} points")
        except:
            print("[WARN] Could not load trajectory")

    # Load saved positions
    positions = load_positions()
    print(f"[OK] Loaded {len(positions)} saved positions")

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

    # Ensure arm is in CAN mode
    print("[..] Ensuring CAN control mode...")
    if piper.GetArmStatus().arm_status.ctrl_mode != 1:
        print("[..] Stopping arm (exiting teach mode)...")
        stop_arm(piper)

    over_time = time.time() + TIMEOUT
    while piper.GetArmStatus().arm_status.ctrl_mode != 1:
        if time.time() > over_time:
            print("[ERROR] CAN mode switch failed")
            exit(1)
        piper.ModeCtrl(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        time.sleep(0.01)

    enable_arm(piper)

    # Go home first
    print("\n[..] Moving to home position first...")
    move_to_joints_deg(piper, [0, 0, 0, 0, 0, 0])

    # Print help
    print("\n" + "=" * 60)
    print("  COMMANDS")
    print("=" * 60)
    print("  play          - Play recorded trajectory")
    print("  save <name>   - Save current position")
    print("  go <name>     - Go to saved position")
    print("  list          - List saved positions")
    print("  delete <name> - Delete a position")
    print("  gamepad / g   - Enter gamepad control")
    print("  home          - Go to home position (0,0,0,0,0,0)")
    print("  quit / q      - Exit")
    print("=" * 60 + "\n")

    # Main command loop
    try:
        while True:
            # Show current position
            current = get_joints_deg(piper)
            print(f"Current: [{current[0]:+.1f}, {current[1]:+.1f}, {current[2]:+.1f}, "
                  f"{current[3]:+.1f}, {current[4]:+.1f}, {current[5]:+.1f}]°")

            cmd = input("\n> ").strip()
            if not cmd:
                continue

            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if action in ('quit', 'q'):
                break

            elif action == 'play':
                if track:
                    play_trajectory(piper, track)

                    # Ask about rotation
                    if rgi:
                        choice = input("\nDo you want to proceed with rotation? (y/n): ").strip().lower()
                        if choice == 'y':
                            print("[..] Closing gripper...")
                            rgi.write_reg(0x0103, 0)  # Close gripper
                            time.sleep(1.0)

                            print("[..] Performing 360° rotation...")
                            rgi.write_reg(0x0109, 360)  # Rotate 360 degrees
                            time.sleep(2.0)  # Wait for rotation to complete
                            print("[OK] Rotation complete!")

                    # Ask about gamepad
                    choice = input("\nEnter gamepad mode for adjustments? (y/n): ").strip().lower()
                    if choice == 'y' and joystick:
                        gamepad_control_loop(piper, rgi, joystick)
                else:
                    print("[ERROR] No trajectory loaded")

            elif action == 'save' and arg:
                current = get_joints_deg(piper)
                grip_pos, grip_angle = rgi.get_status() if rgi else (None, None)
                positions[arg] = {
                    "joints": current,
                    "gripper_pos": grip_pos,
                    "gripper_rotation": grip_angle,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_positions(positions)
                print(f"[OK] Saved '{arg}': {[round(j,1) for j in current]}°")

            elif action == 'go' and arg:
                if arg in positions:
                    target = positions[arg]["joints"]
                    move_to_joints_deg(piper, target)
                    # Ask about gamepad
                    choice = input("\nEnter gamepad mode for adjustments? (y/n): ").strip().lower()
                    if choice == 'y' and joystick:
                        final_pos = gamepad_control_loop(piper, rgi, joystick)
                        # Ask to update saved position
                        update = input(f"\nUpdate '{arg}' with new position? (y/n): ").strip().lower()
                        if update == 'y':
                            grip_pos, grip_angle = rgi.get_status() if rgi else (None, None)
                            positions[arg] = {
                                "joints": final_pos,
                                "gripper_pos": grip_pos,
                                "gripper_rotation": grip_angle,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            save_positions(positions)
                            print(f"[OK] Updated '{arg}'")
                else:
                    print(f"[ERROR] Position '{arg}' not found")
                    print(f"  Available: {list(positions.keys())}")

            elif action == 'list':
                if positions:
                    print("\nSaved positions:")
                    for name, data in positions.items():
                        j = data["joints"]
                        print(f"  {name}: [{j[0]:+.1f}, {j[1]:+.1f}, {j[2]:+.1f}, "
                              f"{j[3]:+.1f}, {j[4]:+.1f}, {j[5]:+.1f}]°")
                else:
                    print("No saved positions")

            elif action == 'delete' and arg:
                if arg in positions:
                    del positions[arg]
                    save_positions(positions)
                    print(f"[OK] Deleted '{arg}'")
                else:
                    print(f"[ERROR] Position '{arg}' not found")

            elif action in ('gamepad', 'g'):
                if joystick:
                    gamepad_control_loop(piper, rgi, joystick)
                else:
                    print("[ERROR] No gamepad connected")

            elif action == 'home':
                move_to_joints_deg(piper, [0, 0, 0, 0, 0, 0])

            else:
                print(f"[?] Unknown command: {cmd}")

    except KeyboardInterrupt:
        print("\n\n[STOPPED]")

    # Cleanup
    if rgi:
        rgi.stop()
    pygame.quit()
    print("Done!")
