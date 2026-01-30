"""
RGI Gripper Gamepad Control
Control the rotating gripper with a gamepad controller

Controls:
    Left Stick Y-axis  : Rotate gripper (up=clockwise, down=counter-clockwise)
    Right Trigger (R2) : Increase speed
    Left Trigger (L2)  : Decrease speed
    A/Cross Button     : Stop rotation
    B/Circle Button    : Reset to 0 degrees
    Start Button       : Exit

Speed is controlled by how far you push the joystick.
"""

import pygame
import serial
import struct
import time
import sys
import threading

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 115200
DEADZONE = 0.15  # Joystick deadzone


class RGIGripper:
    """RGI Gripper controller"""

    REG_INIT = 0x0100
    REG_SPEED = 0x0107
    REG_FORCE = 0x0108
    REG_TARGET = 0x0109
    REG_ANGLE = 0x0208
    REG_STATUS = 0x020B

    def __init__(self, port=SERIAL_PORT, baudrate=BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.current_angle = 0
        self.target_angle = 0
        self.speed = 30  # Default speed
        self.force = 50  # Default force
        self.connected = False

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
            return None
        cmd = self.build_cmd(1, 0x06, reg, int(value))
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.02)
        return self.ser.read(100)

    def read_reg(self, reg):
        if not self.ser:
            return None
        cmd = self.build_cmd(1, 0x03, reg, 1)
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.02)
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
            print(f"Connecting to gripper on {self.port}...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.5)
            time.sleep(0.1)
            self.connected = True
            print("[OK] Gripper connected")
            return True
        except Exception as e:
            print(f"[ERROR] Cannot connect to gripper: {e}")
            return False

    def disconnect(self):
        if self.ser:
            self.stop()
            self.ser.close()
            self.connected = False
            print("[OK] Gripper disconnected")

    def initialize(self):
        print("Initializing gripper...")
        self.write_reg(self.REG_INIT, 0xA5)
        time.sleep(0.3)
        self.set_speed(self.speed)
        self.set_force(self.force)
        self.current_angle = self.get_angle() or 0
        self.target_angle = self.current_angle
        print(f"[OK] Initialized at angle: {self.current_angle}")

    def set_speed(self, speed):
        self.speed = max(1, min(100, int(speed)))
        self.write_reg(self.REG_SPEED, self.speed)

    def set_force(self, force):
        self.force = max(1, min(100, int(force)))
        self.write_reg(self.REG_FORCE, self.force)

    def get_angle(self):
        angle = self.read_reg(self.REG_ANGLE)
        if angle is not None:
            self.current_angle = angle
        return self.current_angle

    def rotate(self, degrees):
        self.target_angle += int(degrees)
        self.write_reg(self.REG_TARGET, self.target_angle)

    def rotate_to(self, target):
        self.target_angle = int(target)
        self.write_reg(self.REG_TARGET, self.target_angle)

    def stop(self):
        self.target_angle = self.current_angle
        self.write_reg(self.REG_TARGET, 0)


def main():
    print("=" * 60)
    print("  RGI Gripper - Gamepad Control")
    print("=" * 60)
    print()
    print("Controls:")
    print("  Left Stick Y    : Rotate (up=CW, down=CCW)")
    print("  Right Stick X   : Fine rotation control")
    print("  R2/L2 Triggers  : Adjust speed (+/-)")
    print("  A / Cross       : Stop rotation")
    print("  B / Circle      : Reset to 0 degrees")
    print("  X / Square      : Decrease force")
    print("  Y / Triangle    : Increase force")
    print("  Start           : Exit")
    print("=" * 60)

    # Initialize pygame for gamepad
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("[ERROR] No gamepad detected!")
        print("Please connect a gamepad and try again.")
        return 1

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"[OK] Gamepad: {joystick.get_name()}")

    # Connect to gripper
    gripper = RGIGripper()
    if not gripper.connect():
        pygame.quit()
        return 1

    gripper.initialize()

    # Control loop
    print("\n[READY] Use gamepad to control gripper. Press Start to exit.\n")

    running = True
    last_update = time.time()
    rotation_rate = 0  # Degrees per update

    try:
        while running:
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Button press events
                elif event.type == pygame.JOYBUTTONDOWN:
                    # A/Cross (button 0) - Stop
                    if event.button == 0:
                        gripper.stop()
                        rotation_rate = 0
                        print("[STOP] Rotation stopped")

                    # B/Circle (button 1) - Reset to 0
                    elif event.button == 1:
                        gripper.rotate_to(0)
                        print("[RESET] Moving to 0 degrees")

                    # X/Square (button 2) - Decrease force
                    elif event.button == 2:
                        gripper.set_force(gripper.force - 10)
                        print(f"[FORCE] {gripper.force}%")

                    # Y/Triangle (button 3) - Increase force
                    elif event.button == 3:
                        gripper.set_force(gripper.force + 10)
                        print(f"[FORCE] {gripper.force}%")

                    # Start (button 7) - Exit
                    elif event.button == 7:
                        running = False

            # Read joystick axes
            left_y = -joystick.get_axis(1)   # Invert so up is positive
            right_x = joystick.get_axis(3)

            # Read triggers (axes 4 and 5 on many controllers)
            try:
                l2 = (joystick.get_axis(4) + 1) / 2  # Normalize to 0-1
                r2 = (joystick.get_axis(5) + 1) / 2
            except:
                l2 = 0
                r2 = 0

            # Apply deadzone
            if abs(left_y) < DEADZONE:
                left_y = 0
            if abs(right_x) < DEADZONE:
                right_x = 0

            # Adjust speed with triggers
            if r2 > 0.5:
                gripper.set_speed(gripper.speed + 1)
            if l2 > 0.5:
                gripper.set_speed(gripper.speed - 1)

            # Calculate rotation rate based on joystick
            # Left stick for main rotation, right stick for fine control
            rotation_rate = left_y * 50 + right_x * 10  # Degrees per update

            # Update gripper
            now = time.time()
            if now - last_update >= 0.05:  # 20 Hz update rate
                if abs(rotation_rate) > 0.5:
                    gripper.rotate(rotation_rate)

                # Read current angle periodically
                angle = gripper.get_angle()

                # Display status
                direction = "CW " if rotation_rate > 0 else "CCW" if rotation_rate < 0 else "---"
                print(f"\r[{direction}] Angle: {angle:6d} deg | "
                      f"Target: {gripper.target_angle:6d} deg | "
                      f"Speed: {gripper.speed:3d}% | "
                      f"Force: {gripper.force:3d}%   ", end="")

                last_update = now

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED]")

    finally:
        print("\nShutting down...")
        gripper.disconnect()
        pygame.quit()

    print("[OK] Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
