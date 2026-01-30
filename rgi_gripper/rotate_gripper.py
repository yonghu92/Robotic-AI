"""
RGI Gripper Control Script
Rotate gripper at specified speed using Modbus RTU protocol
Adapted for Linux
"""
import serial
import struct
import time
import sys

# Default serial port for Linux
DEFAULT_PORT = '/dev/ttyUSB0'
DEFAULT_BAUDRATE = 115200


def calc_crc16(data):
    """Calculate Modbus CRC16"""
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
    """Build Modbus RTU command with CRC"""
    cmd = struct.pack('>BBHH', slave_id, func, reg, value)
    crc = calc_crc16(cmd)
    return cmd + struct.pack('<H', crc)


def write_reg(ser, reg, value):
    """Write value to register"""
    if value < 0:
        value = value & 0xFFFF
    cmd = build_cmd(1, 0x06, reg, value)
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.05)
    resp = ser.read(100)
    return resp


def read_reg(ser, reg):
    """Read value from register"""
    cmd = build_cmd(1, 0x03, reg, 1)
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.05)
    resp = ser.read(100)
    if len(resp) >= 7:
        for i in range(len(resp) - 6):
            if resp[i] == 0x01 and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                val = (resp[i+3] << 8) | resp[i+4]
                if val > 32767:
                    val -= 65536
                return val
    return None


class RGIGripper:
    """RGI Gripper control class"""

    # Register addresses (from manual)
    REG_INIT = 0x0100       # Initialize gripper (write 0xA5)
    REG_SPEED = 0x0107      # Rotation speed (0-100%)
    REG_FORCE = 0x0108      # Rotation force (0-100%)
    REG_TARGET = 0x0109     # Target rotation angle (degrees)
    REG_ANGLE = 0x0208      # Current angle reading
    REG_STATUS = 0x020B     # Rotation status (1=complete, 0=moving)

    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        """Connect to gripper"""
        try:
            print(f'Connecting to {self.port} at {self.baudrate} baud...')
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(0.1)
            print('[OK] Connected')
            return True
        except Exception as e:
            print(f'[ERROR] Cannot connect: {e}')
            return False

    def disconnect(self):
        """Disconnect from gripper"""
        if self.ser:
            self.ser.close()
            print('[OK] Disconnected')

    def initialize(self):
        """Initialize gripper"""
        print('Initializing gripper...')
        write_reg(self.ser, self.REG_INIT, 0xA5)
        time.sleep(0.5)
        print('[OK] Initialized')

    def set_speed(self, speed_percent):
        """Set rotation speed (0-100%)"""
        speed = max(0, min(100, speed_percent))
        print(f'Setting speed to {speed}%...')
        write_reg(self.ser, self.REG_SPEED, speed)
        time.sleep(0.1)

    def set_force(self, force_percent):
        """Set rotation force (0-100%)"""
        force = max(0, min(100, force_percent))
        print(f'Setting force to {force}%...')
        write_reg(self.ser, self.REG_FORCE, force)
        time.sleep(0.1)

    def get_angle(self):
        """Get current angle"""
        return read_reg(self.ser, self.REG_ANGLE)

    def get_status(self):
        """Get rotation status (1=complete, 0=moving)"""
        return read_reg(self.ser, self.REG_STATUS)

    def rotate(self, degrees):
        """Rotate by specified degrees"""
        print(f'Rotating {degrees} degrees...')
        write_reg(self.ser, self.REG_TARGET, int(degrees))

    def stop(self):
        """Stop rotation"""
        print('Stopping rotation...')
        write_reg(self.ser, self.REG_TARGET, 0)
        time.sleep(0.5)


def main():
    print('='*50)
    print('RGI Gripper Control (Linux)')
    print('='*50)

    # Parse arguments
    port = DEFAULT_PORT
    duration = 60  # seconds
    speed = 20     # percent

    if len(sys.argv) > 1:
        port = sys.argv[1]
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    if len(sys.argv) > 3:
        speed = int(sys.argv[3])

    print(f'\nSettings:')
    print(f'  Port: {port}')
    print(f'  Duration: {duration} seconds')
    print(f'  Speed: {speed}%')

    # Connect
    gripper = RGIGripper(port=port)
    if not gripper.connect():
        print('\nPlease check:')
        print('1. Is the gripper connected via USB?')
        print('2. Run: ls -la /dev/ttyUSB*')
        print('3. Add user to dialout group: sudo usermod -a -G dialout $USER')
        return 1

    try:
        # Initialize
        gripper.initialize()

        # Set speed and force
        gripper.set_speed(speed)
        gripper.set_force(50)

        # Get initial angle
        init_angle = gripper.get_angle()
        print(f'Initial angle: {init_angle} degrees')

        # Start rotation
        print('\n' + '='*50)
        print(f'Starting {duration} second rotation at {speed}% speed...')
        print('Press Ctrl+C to stop')
        print('='*50)

        start_time = time.time()
        rotation_degrees = 20000  # Large rotation command
        gripper.rotate(rotation_degrees)

        # Monitor rotation
        last_angle = init_angle if init_angle else 0
        total_rotation = 0

        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            current_angle = gripper.get_angle()

            if current_angle is not None:
                # Track rotation
                if last_angle is not None:
                    diff = current_angle - last_angle
                    if diff > 20000:
                        diff -= 65536
                    elif diff < -20000:
                        diff += 65536
                    total_rotation += abs(diff)
                last_angle = current_angle

                status = gripper.get_status()
                print(f'[{elapsed:5.1f}s] Angle: {current_angle:6d} deg | Total: {total_rotation:7.0f} deg | Status: {status}')

                # If rotation completed early, send more
                if status == 1 and elapsed < duration - 5:
                    print('         Sending more rotation...')
                    gripper.rotate(15000)

            time.sleep(2)

        # Stop
        gripper.stop()

        # Summary
        final_angle = gripper.get_angle()
        elapsed = time.time() - start_time

        print('\n' + '='*50)
        print('=== Rotation Complete ===')
        print('='*50)
        print(f'Duration: {elapsed:.1f} seconds')
        print(f'Final angle: {final_angle} degrees')
        print(f'Total rotation: {total_rotation:.0f} degrees')
        if elapsed > 0:
            print(f'Average speed: {total_rotation/elapsed:.1f} deg/sec')

    except KeyboardInterrupt:
        print('\n\nInterrupted! Stopping...')
        gripper.stop()
    except Exception as e:
        print(f'[ERROR] {e}')
    finally:
        gripper.disconnect()

    return 0


if __name__ == '__main__':
    sys.exit(main())
