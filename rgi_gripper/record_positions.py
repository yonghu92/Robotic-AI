#!/usr/bin/env python3
# -*-coding:utf8-*-
"""
Position Recorder & Playback for Piper Arm + RGI Gripper

How it works:
    - Motors are DISABLED on startup, so you can freely move the arm by hand
    - Move arm to a position, then press SELECT or type 'record <name>'
    - When you type 'go <name>', motors ENABLE and move to saved position
    - Type 'free' to disable motors again and continue recording

Commands:
    record <name>   : Save current position with name
    go <name>       : Move to saved position (enables motors)
    list            : Show all saved positions
    delete <name>   : Delete a position
    home            : Go to home position (0,0,0,0,0,0)
    free            : Disable motors (so you can move arm by hand)
    quit            : Exit

Gamepad:
    SELECT (btn 8)  : Quick record (auto-names position_1, position_2, etc.)
    START (btn 9)   : List all positions
    X/B             : Open/Close RGI gripper
    LT/RT           : Rotate RGI gripper
    Y/A             : Rotation step size +/-
"""

import os
import sys
import time
import json
import threading
import select
import pygame
import serial
import struct
from piper_sdk import C_PiperInterface_V2

# Configuration
POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "saved_positions.json")
RGI_SERIAL_PORT = '/dev/ttyUSB1'
RGI_BAUDRATE = 115200
STEP_SIZES = [1, 10, 90, 180, 360]


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
        except:
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


# ============ Position Manager ============
class PositionManager:
    def __init__(self, filename):
        self.filename = filename
        self.positions = {}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.positions = json.load(f)
                print(f"[OK] Loaded {len(self.positions)} positions from file")
            except Exception as e:
                print(f"[WARN] Could not load positions: {e}")
                self.positions = {}

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Could not save: {e}")

    def record(self, name, joints_deg, gripper_pos=None, gripper_rotation=None):
        self.positions[name] = {
            "joints_deg": joints_deg,
            "gripper_pos": gripper_pos,
            "gripper_rotation": gripper_rotation,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        print(f"\n*** RECORDED '{name}': {[round(j, 1) for j in joints_deg]}° ***")
        self.save()

    def get(self, name):
        return self.positions.get(name)

    def delete(self, name):
        if name in self.positions:
            del self.positions[name]
            print(f"[OK] Deleted '{name}'")
            self.save()
        else:
            print(f"[ERROR] '{name}' not found")

    def list_all(self):
        if not self.positions:
            print("\n[INFO] No positions saved yet.")
            return
        print(f"\n{'='*60}")
        print(f"  SAVED POSITIONS ({len(self.positions)})")
        print(f"{'='*60}")
        for name, data in self.positions.items():
            joints = data.get("joints_deg", [0]*6)
            print(f"  {name:20s} : {[round(j, 1) for j in joints]}°")
        print(f"{'='*60}\n")


# ============ Main ============
def main():
    print("=" * 60)
    print("  POSITION RECORDER & PLAYBACK")
    print("=" * 60)

    # Initialize pygame for gamepad
    pygame.init()
    pygame.joystick.init()

    joystick = None
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"[OK] Gamepad: {joystick.get_name()}")
    else:
        print("[WARN] No gamepad - keyboard only")

    # Connect RGI Gripper
    rgi = RGIGripper(RGI_SERIAL_PORT, RGI_BAUDRATE)
    if rgi.connect():
        print(f"[OK] RGI Gripper connected")
        rgi.initialize()
        rgi.start()
    else:
        print("[WARN] RGI Gripper not connected")
        rgi = None

    # Connect Piper Arm
    print("[..] Connecting to Piper arm...")
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()
    time.sleep(0.1)
    print("[OK] Piper arm connected")

    # Check and clear emergency stop if needed
    status = piper.GetArmStatus()
    if status.arm_status.arm_status == 1:
        print("[WARN] Arm in emergency stop - clearing...")
        piper.EmergencyStop(0x02)
        time.sleep(1.0)
        print("[OK] Emergency stop cleared")

    # Position manager
    pos_mgr = PositionManager(POSITIONS_FILE)

    # Helper functions
    def get_joints_deg():
        js = piper.GetArmJointMsgs().joint_state
        return [js.joint_1/1000, js.joint_2/1000, js.joint_3/1000,
                js.joint_4/1000, js.joint_5/1000, js.joint_6/1000]

    def enable_motors():
        """Enable motors for moving to position"""
        print("[..] Enabling motors...")
        # Set CAN control mode
        for _ in range(30):
            piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            time.sleep(0.1)
            if piper.GetArmStatus().arm_status.ctrl_mode == 1:
                break
        # Enable arm
        for _ in range(30):
            piper.EnableArm(7)
            time.sleep(0.1)
            if all(piper.GetArmEnableStatus()):
                break
        piper.EnablePiper()
        piper.ModeCtrl(0x01, 0x01, 30, 0x00)
        time.sleep(0.2)
        print("[OK] Motors enabled")

    def disable_motors():
        """Disable motors so arm can be moved by hand"""
        print("[..] Disabling motors (you can now move arm by hand)...")
        piper.DisableArm(7)
        time.sleep(0.3)
        print("[OK] Motors disabled - move arm freely!")

    def move_to_position(target_deg):
        """Move arm to target position"""
        target_milli = [int(j * 1000) for j in target_deg]
        print(f"[..] Moving to: {[round(j, 1) for j in target_deg]}°")
        for i in range(300):  # 6 seconds max
            piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            piper.JointCtrl(*target_milli)
            time.sleep(0.02)
            current = get_joints_deg()
            errors = [abs(c - t) for c, t in zip(current, target_deg)]
            if all(e < 1.0 for e in errors):
                print("[OK] Reached position!")
                return True
        print("[WARN] May not have reached target exactly")
        return False

    # Start with motors disabled so user can move arm
    disable_motors()

    # Instructions
    print("\n" + "=" * 60)
    print("  READY TO RECORD")
    print("=" * 60)
    print("  Motors are DISABLED - you can move the arm by hand!")
    print()
    print("  Commands:")
    print("    record <name>  - Save current position")
    print("    go <name>      - Move to position (enables motors)")
    print("    list           - Show all positions")
    print("    delete <name>  - Delete position")
    print("    home           - Go to home (0,0,0,0,0,0)")
    print("    free           - Disable motors again")
    print("    quit           - Exit")
    print()
    print("  Gamepad: SELECT=record, START=list")
    print("=" * 60 + "\n")

    # Control state
    motors_enabled = False
    step_index = 2
    last_select = False
    last_start = False
    last_y = False
    last_a = False
    record_counter = len(pos_mgr.positions) + 1

    try:
        while True:
            pygame.event.pump()

            # Check keyboard input (non-blocking)
            if select.select([sys.stdin], [], [], 0)[0]:
                cmd_line = sys.stdin.readline().strip()
                parts = cmd_line.split(maxsplit=1)
                cmd = parts[0].lower() if parts else ""
                arg = parts[1] if len(parts) > 1 else ""

                if cmd in ("quit", "exit", "q"):
                    break

                elif cmd == "record" and arg:
                    joints = get_joints_deg()
                    grip_pos, grip_rot = rgi.get_status() if rgi else (None, None)
                    pos_mgr.record(arg, joints, grip_pos, grip_rot)

                elif cmd == "go" and arg:
                    pos = pos_mgr.get(arg)
                    if pos:
                        if not motors_enabled:
                            enable_motors()
                            motors_enabled = True
                        move_to_position(pos["joints_deg"])
                    else:
                        print(f"[ERROR] Position '{arg}' not found")

                elif cmd == "list":
                    pos_mgr.list_all()

                elif cmd == "delete" and arg:
                    pos_mgr.delete(arg)

                elif cmd == "home":
                    if not motors_enabled:
                        enable_motors()
                        motors_enabled = True
                    move_to_position([0, 0, 0, 0, 0, 0])

                elif cmd == "free":
                    disable_motors()
                    motors_enabled = False

                elif cmd:
                    print(f"[?] Unknown command: {cmd}")

            # Gamepad controls
            if joystick:
                # SELECT = Quick record
                select_btn = joystick.get_button(8)
                if select_btn and not last_select:
                    name = f"position_{record_counter}"
                    joints = get_joints_deg()
                    grip_pos, grip_rot = rgi.get_status() if rgi else (None, None)
                    pos_mgr.record(name, joints, grip_pos, grip_rot)
                    record_counter += 1
                last_select = select_btn

                # START = List
                start_btn = joystick.get_button(9)
                if start_btn and not last_start:
                    pos_mgr.list_all()
                last_start = start_btn

                # RGI controls
                if rgi:
                    y_btn = joystick.get_button(3)
                    a_btn = joystick.get_button(1)
                    if y_btn and not last_y:
                        step_index = min(len(STEP_SIZES) - 1, step_index + 1)
                        print(f"\n[Y] Step: {STEP_SIZES[step_index]}°")
                    if a_btn and not last_a:
                        step_index = max(0, step_index - 1)
                        print(f"\n[A] Step: {STEP_SIZES[step_index]}°")
                    last_y, last_a = y_btn, a_btn

                    x_btn = joystick.get_button(0)
                    b_btn = joystick.get_button(2)
                    lt_btn = joystick.get_button(6)
                    rt_btn = joystick.get_button(7)
                    rgi.set_commands(x_btn, b_btn, lt_btn, rt_btn, STEP_SIZES[step_index])

            # Display status
            joints = get_joints_deg()
            grip_pos, grip_rot = rgi.get_status() if rgi else (0, 0)
            mode_str = "MOTORS ON" if motors_enabled else "FREE MOVE"

            print(f"\r[{mode_str:9s}] J1:{joints[0]:+6.1f} J2:{joints[1]:+6.1f} J3:{joints[2]:+6.1f} "
                  f"J4:{joints[3]:+6.1f} J5:{joints[4]:+6.1f} J6:{joints[5]:+6.1f} | "
                  f"Saved:{len(pos_mgr.positions)}  ", end="", flush=True)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n[STOPPED]")

    # Cleanup
    if rgi:
        rgi.stop()
    pos_mgr.save()
    pygame.quit()
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
