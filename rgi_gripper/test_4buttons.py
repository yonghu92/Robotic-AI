#!/usr/bin/env python3
"""
RGI Gripper - Combined Control (Open/Close + Rotation)

Controls:
    X       : OPEN gripper (position 1000)
    B       : CLOSE gripper (position 0)
    LT/L2   : Rotate counterclockwise
    RT/R2   : Rotate clockwise
    Y       : Rotation step size UP
    A       : Rotation step size DOWN
    Start   : Exit

Registers:
    Gripper:
        0x0100 = Initialize (write 0xA5)
        0x0101 = Force (20-100%)
        0x0103 = Position (0=closed, 1000=open)
        0x0104 = Speed (1-100%)
    Rotation:
        0x0107 = Rotation Speed (0-100%)
        0x0108 = Rotation Force (0-100%)
        0x0109 = Target Angle (relative movement)
        0x0208 = Current Angle (read)
"""

import pygame
import serial
import struct
import time
import sys

SERIAL_PORT = '/dev/ttyUSB1'
BAUDRATE = 115200

# Rotation step sizes in degrees
STEP_SIZES = [1, 10, 90, 180, 360]
step_index = 0  # Start at 1 degree


def calc_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_cmd(slave_id, func, reg, value):
    if value < 0:
        value = value & 0xFFFF
    cmd = struct.pack('>BBHH', slave_id, func, reg, value)
    crc = calc_crc16(cmd)
    return cmd + struct.pack('<H', crc)


def write_reg(ser, reg, value):
    cmd = build_cmd(1, 0x06, reg, int(value))
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.02)
    return ser.read(100)


def read_reg(ser, reg):
    cmd = build_cmd(1, 0x03, reg, 1)
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.02)
    resp = ser.read(100)
    if len(resp) >= 7:
        for i in range(len(resp) - 6):
            if resp[i] == 0x01 and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                val = (resp[i+3] << 8) | resp[i+4]
                if val > 32767:
                    val -= 65536
                return val
    return None


def main():
    global step_index

    print("=" * 50)
    print("  RGI Gripper - Combined Control")
    print("=" * 50)
    print()
    print("  Gripper:")
    print("    X       = OPEN gripper")
    print("    B       = CLOSE gripper")
    print()
    print("  Rotation:")
    print("    LT/L2   = Rotate counterclockwise")
    print("    RT/R2   = Rotate clockwise")
    print("    Y       = Step size UP")
    print("    A       = Step size DOWN")
    print()
    print(f"  Step sizes: {STEP_SIZES}°")
    print("  Start = Exit")
    print("=" * 50)

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("[ERROR] No gamepad!")
        return 1

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"[OK] Gamepad: {js.get_name()}")

    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.5)
        time.sleep(0.1)
        print(f"[OK] Gripper on {SERIAL_PORT}")
    except Exception as e:
        print(f"[ERROR] {e}")
        pygame.quit()
        return 1

    # Initialize gripper
    print("[..] Initializing gripper...")
    write_reg(ser, 0x0100, 0xA5)  # Initialize
    time.sleep(1.0)  # Wait for initialization

    # Gripper settings
    gripper_speed = 50
    gripper_force = 100
    write_reg(ser, 0x0104, gripper_speed)  # Gripper speed (1-100%)
    write_reg(ser, 0x0101, gripper_force)  # Gripper force (20-100%)

    # Rotation settings
    write_reg(ser, 0x0107, 100)  # Rotation speed 100%
    write_reg(ser, 0x0108, 100)  # Rotation force 100%

    # Read initial states
    gripper_pos = read_reg(ser, 0x0103) or 0
    rotation_angle = read_reg(ser, 0x0208) or 0
    print(f"[OK] Gripper pos: {gripper_pos}, Rotation angle: {rotation_angle}°")
    print(f"[OK] Rotation step: {STEP_SIZES[step_index]}°")
    print("\nReady!\n")

    running = True
    last_update = time.time()
    y_was_pressed = False
    a_was_pressed = False

    try:
        while running:
            pygame.event.pump()

            # Process button events (X, B, Start)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:  # X - Open gripper
                        print("\n[X] OPENING gripper...")
                        write_reg(ser, 0x0103, 1000)  # Position = 1000 (fully open)

                    elif event.button == 2:  # B - Close gripper
                        print("\n[B] CLOSING gripper...")
                        write_reg(ser, 0x0103, 0)  # Position = 0 (fully closed)

                    elif event.button == 9:  # Start - Exit
                        print("\n[Exit]")
                        running = False

            # Check Y button - increase rotation step size (with debounce)
            if js.get_button(3):
                if not y_was_pressed:
                    step_index = min(len(STEP_SIZES) - 1, step_index + 1)
                    print(f"\n[Y] Rotation step: {STEP_SIZES[step_index]}°")
                    y_was_pressed = True
            else:
                y_was_pressed = False

            # Check A button - decrease rotation step size (with debounce)
            if js.get_button(1):
                if not a_was_pressed:
                    step_index = max(0, step_index - 1)
                    print(f"\n[A] Rotation step: {STEP_SIZES[step_index]}°")
                    a_was_pressed = True
            else:
                a_was_pressed = False

            # Check LT/RT for rotation (buttons 6 and 7 on Logitech)
            lt_pressed = js.get_button(6)  # L2 button
            rt_pressed = js.get_button(7)  # R2 button
            step = STEP_SIZES[step_index]

            if lt_pressed and not rt_pressed:
                # LT - rotate counterclockwise
                write_reg(ser, 0x0109, -step)

            elif rt_pressed and not lt_pressed:
                # RT - rotate clockwise
                write_reg(ser, 0x0109, step)

            # Display status
            now = time.time()
            if now - last_update >= 0.2:
                gripper_pos = read_reg(ser, 0x0103)
                rotation_angle = read_reg(ser, 0x0208)

                if gripper_pos is not None and rotation_angle is not None:
                    # Gripper status
                    g_status = "OPEN" if gripper_pos > 500 else "CLOSED" if gripper_pos < 100 else "MOVING"
                    bar = int(gripper_pos / 50)  # 0-20 scale
                    bar_str = "#" * bar + "-" * (20 - bar)

                    # Rotation status
                    rot_dir = "<<" if lt_pressed else ">>" if rt_pressed else "--"

                    print(f"\r  Grip:[{bar_str}] {gripper_pos:4d} {g_status:6s} | Rot: {rot_dir} {rotation_angle:6d}° Step:{step}°   ", end="", flush=True)

                last_update = now

            time.sleep(0.1)  # 0.1s loop time

    except KeyboardInterrupt:
        print("\n[Stopped]")

    finally:
        ser.close()
        pygame.quit()
        print("\nDone")

    return 0


if __name__ == "__main__":
    sys.exit(main())
