#!/usr/bin/env python3
"""
Debug script to test RGI gripper communication
"""
import serial
import struct
import time

SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 115200

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

def write_reg(ser, reg, value, name=""):
    cmd = build_cmd(1, 0x06, reg, int(value))
    print(f"  SEND [{name}]: {cmd.hex()}")
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.1)
    resp = ser.read(100)
    print(f"  RECV: {resp.hex() if resp else '(no response)'}")
    return resp

def read_reg(ser, reg, name=""):
    cmd = build_cmd(1, 0x03, reg, 1)
    print(f"  SEND [{name}]: {cmd.hex()}")
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.1)
    resp = ser.read(100)
    print(f"  RECV: {resp.hex() if resp else '(no response)'}")

    if len(resp) >= 7:
        for i in range(len(resp) - 6):
            if resp[i] == 0x01 and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                val = (resp[i+3] << 8) | resp[i+4]
                if val > 32767:
                    val -= 65536
                print(f"  VALUE: {val}")
                return val
    return None

def main():
    print("=" * 50)
    print("  RGI Gripper Debug Test")
    print("=" * 50)

    # Try different baud rates
    baud_rates = [115200, 9600, 19200, 38400, 57600]

    ser = None
    for baud in baud_rates:
        print(f"\n[*] Trying {SERIAL_PORT} at {baud} baud...")
        try:
            ser = serial.Serial(SERIAL_PORT, baud, timeout=1)
            time.sleep(0.2)
            print(f"[OK] Port opened at {baud} baud")

            # Test read current angle
            print(f"\n[1] Reading current angle (reg 0x0208)...")
            angle = read_reg(ser, 0x0208, "read angle")

            if angle is not None:
                print(f"\n[SUCCESS] Got response at {baud} baud! Angle = {angle}")
                break
            else:
                print(f"[--] No valid response at {baud}")
                ser.close()
                ser = None

        except Exception as e:
            print(f"[ERROR] {e}")
            if ser:
                ser.close()
                ser = None

    if not ser:
        print("\n[ERROR] Could not communicate with gripper at any baud rate")
        print("\nCheck:")
        print("  1. Is the gripper powered on?")
        print("  2. Is USB cable connected properly?")
        print("  3. Is there another program using the port?")
        return 1

    print("\n" + "=" * 50)
    print("Testing gripper commands...")
    print("=" * 50)

    # Initialize
    print("\n[2] Initialize (write 0xA5 to reg 0x0100)...")
    write_reg(ser, 0x0100, 0xA5, "init")
    time.sleep(0.5)

    # Set speed
    print("\n[3] Set speed to 50% (reg 0x0107)...")
    write_reg(ser, 0x0107, 50, "speed")

    # Set force
    print("\n[4] Set force to 100% (reg 0x0108)...")
    write_reg(ser, 0x0108, 100, "force")

    # Read angle again
    print("\n[5] Read current angle...")
    angle = read_reg(ser, 0x0208, "angle")

    # Try to rotate
    print("\n[6] Command rotation to +1000 degrees (reg 0x0109)...")
    write_reg(ser, 0x0109, 1000, "rotate")

    print("\n[7] Waiting 3 seconds and checking angle...")
    for i in range(6):
        time.sleep(0.5)
        angle = read_reg(ser, 0x0208, f"angle check {i+1}")
        status = read_reg(ser, 0x020B, "status")
        print(f"     Angle: {angle}, Status: {status}")

    # Stop
    print("\n[8] Stop rotation (write 0 to reg 0x0109)...")
    write_reg(ser, 0x0109, 0, "stop")

    ser.close()
    print("\n[OK] Test complete")
    return 0

if __name__ == "__main__":
    exit(main())
