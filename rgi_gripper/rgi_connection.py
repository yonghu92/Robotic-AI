"""
RGI Series Gripper Connection Script
Connects to RGI device and tests communication
Adapted for Linux (uses /dev/ttyUSB0 instead of COM6)
"""

import serial
import serial.tools.list_ports
import time
import sys

class RGIConnection:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, timeout=1):
        """
        Initialize RGI connection

        Args:
            port: Serial port (default /dev/ttyUSB0 for Linux)
            baudrate: Communication baud rate (RGI uses 115200)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None

    def connect(self):
        """Establish connection to RGI device"""
        try:
            print(f"Attempting to connect to {self.port} at {self.baudrate} baud...")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )

            if self.serial_conn.is_open:
                print(f"[OK] Successfully connected to {self.port}")
                time.sleep(0.1)  # Wait for connection to stabilize
                return True
            else:
                print(f"[ERROR] Failed to open {self.port}")
                return False

        except serial.SerialException as e:
            print(f"[ERROR] Serial connection error: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return False

    def disconnect(self):
        """Close connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"[OK] Disconnected from {self.port}")

    def send_command(self, command):
        """
        Send command to RGI device

        Args:
            command: Command bytes or string to send
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("[ERROR] Not connected to device")
            return None

        try:
            if isinstance(command, str):
                command = command.encode('utf-8')

            self.serial_conn.write(command)
            print(f"[SEND] {command.hex()}")
            return True
        except Exception as e:
            print(f"[ERROR] Error sending command: {e}")
            return False

    def read_response(self, bytes_to_read=64):
        """
        Read response from RGI device

        Args:
            bytes_to_read: Number of bytes to read
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("[ERROR] Not connected to device")
            return None

        try:
            if self.serial_conn.in_waiting > 0:
                response = self.serial_conn.read(bytes_to_read)
                print(f"[RECV] {response.hex()}")
                return response
            else:
                print("[INFO] No data available")
                return None
        except Exception as e:
            print(f"[ERROR] Error reading response: {e}")
            return None

    def send_and_receive(self, command, wait_time=0.1, bytes_to_read=64):
        """
        Send command and wait for response

        Args:
            command: Command to send
            wait_time: Time to wait before reading response
            bytes_to_read: Number of bytes to read
        """
        if self.send_command(command):
            time.sleep(wait_time)
            return self.read_response(bytes_to_read)
        return None

    def test_connection(self):
        """Test basic connection by checking if device responds"""
        print("\n=== Testing RGI Connection ===")

        # Common test commands (adjust based on actual protocol)
        test_commands = [
            b'\x01\x03\x00\x00\x00\x01',  # Modbus read holding register example
            b'?',  # Simple query
            b'STATUS',  # Status query
        ]

        for cmd in test_commands:
            print(f"\nTesting command: {cmd.hex()}")
            response = self.send_and_receive(cmd, wait_time=0.2)
            if response:
                print(f"[OK] Device responded: {response.hex()}")
                return True
            time.sleep(0.1)

        print("[WARNING] No response from device (may be normal if device doesn't respond to test commands)")
        return False

    def get_device_info(self):
        """Attempt to retrieve device information"""
        print("\n=== Retrieving Device Information ===")

        # Try common information queries
        info_commands = [
            b'*IDN?',  # SCPI-style identification
            b'VERSION',  # Version query
            b'\x01\x03\x00\x00\x00\x01',  # Modbus device ID
        ]

        for cmd in info_commands:
            response = self.send_and_receive(cmd, wait_time=0.2)
            if response:
                print(f"Device info: {response.hex()}")
                return response

        return None


def list_available_ports():
    """List all available serial ports"""
    print("\n=== Available Serial Ports ===")
    ports = serial.tools.list_ports.comports()
    if ports:
        for port in ports:
            print(f"  {port.device}: {port.description}")
    else:
        print("  No serial ports found")
    return [port.device for port in ports]


def main():
    """Main function to test RGI connection"""
    print("RGI Series Gripper Connection Test (Linux)")
    print("=" * 50)

    # List available ports
    available_ports = list_available_ports()

    # Default port for Linux
    port = '/dev/ttyUSB0'

    # Check if port exists
    if port not in available_ports:
        print(f"\n[WARNING] {port} not found in available ports")
        if available_ports:
            port = available_ports[0]
            print(f"[INFO] Using {port} instead")

    # RGI uses 115200 baud
    baud_rates = [115200, 9600, 19200, 38400]

    rgi = None
    connected = False

    for baud in baud_rates:
        print(f"\n--- Trying {port} at {baud} baud ---")
        rgi = RGIConnection(port=port, baudrate=baud)

        if rgi.connect():
            connected = True
            print(f"[OK] Connected at {baud} baud")

            # Test connection
            rgi.test_connection()

            # Try to get device info
            rgi.get_device_info()

            break
        else:
            print(f"[ERROR] Failed at {baud} baud")

    if not connected:
        print(f"\n[ERROR] Could not establish connection to {port}")
        print("\nTroubleshooting tips:")
        print("1. Verify the device is connected (check dmesg | tail)")
        print("2. Check permissions: sudo usermod -a -G dialout $USER")
        print("3. Verify the correct baud rate in the manual")
        print("4. Ensure proper cable connection")
        return 1

    # Keep connection open for manual testing
    print("\n" + "=" * 50)
    print("Connection established. Press Ctrl+C to disconnect.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nDisconnecting...")
        rgi.disconnect()
        return 0


if __name__ == "__main__":
    sys.exit(main())
