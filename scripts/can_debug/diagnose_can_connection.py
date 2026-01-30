#!/usr/bin/env python3
"""
Comprehensive CAN Connection Diagnostic Tool
Helps troubleshoot why the arm is not responding on CAN bus
"""
import subprocess
import sys
import time
import os

def run_command(cmd, shell=True):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_can_interface_exists():
    """Check if CAN interface exists"""
    print_section("Step 1: Check CAN Interface Exists")
    
    success, output, error = run_command("ip link show type can")
    if not success:
        print("❌ ERROR: Cannot check CAN interfaces")
        print(f"   Error: {error}")
        return False, None
    
    if "can" not in output.lower():
        print("❌ No CAN interfaces found!")
        print("   Make sure your USB-to-CAN adapter is plugged in")
        return False, None
    
    # Extract CAN interface names
    interfaces = []
    for line in output.split('\n'):
        if 'can' in line.lower() and ':' in line:
            parts = line.split(':')
            if len(parts) >= 2:
                iface = parts[1].strip().split()[0]
                interfaces.append(iface)
    
    if not interfaces:
        print("❌ No CAN interfaces detected")
        return False, None
    
    print(f"✓ Found CAN interface(s): {', '.join(interfaces)}")
    return True, interfaces

def check_can_interface_status(iface="can0"):
    """Check if CAN interface is UP and configured"""
    print_section(f"Step 2: Check CAN Interface Status ({iface})")
    
    # Check if interface exists
    success, output, error = run_command(f"ip link show {iface}")
    if not success:
        print(f"❌ Interface {iface} does not exist!")
        print(f"   Error: {error}")
        return False
    
    # Check if UP
    if "UP" in output:
        print(f"✓ Interface {iface} is UP")
    else:
        print(f"❌ Interface {iface} is DOWN")
        print("   Need to activate it!")
        return False
    
    # Check bitrate
    success, output, error = run_command(f"ip -details link show {iface}")
    if "bitrate 1000000" in output:
        print(f"✓ Bitrate is correctly set to 1,000,000 bps")
    else:
        print(f"⚠ Bitrate may not be set correctly")
        print(f"   Output: {output[:200]}")
    
    # Check statistics
    success, output, error = run_command(f"ip -s link show {iface}")
    if success:
        print(f"\nInterface Statistics:")
        print(output)
    
    return True

def test_can_receive(iface="can0", timeout=3):
    """Test if we can receive CAN messages"""
    print_section(f"Step 3: Test CAN Receive ({iface})")
    
    print(f"Listening for CAN messages on {iface} for {timeout} seconds...")
    print("   (Make sure arm controller is powered on)")
    
    success, output, error = run_command(f"timeout {timeout} candump {iface} 2>&1 | head -20")
    
    if "can0" in error.lower() or "no such device" in error.lower():
        print(f"❌ Cannot access {iface}")
        print(f"   Error: {error}")
        return False
    
    if output.strip():
        print(f"✓ Received CAN messages!")
        print(f"   Sample messages:")
        for line in output.strip().split('\n')[:5]:
            print(f"   {line}")
        return True
    else:
        print(f"❌ No CAN messages received")
        print(f"   This means the arm controller is not responding")
        return False

def test_can_send(iface="can0"):
    """Test if we can send CAN messages"""
    print_section(f"Step 4: Test CAN Send ({iface})")
    
    # Try to send a test message
    # Using cansend with a simple test ID
    test_id = "123"
    test_data = "00.00.00.00"
    
    print(f"Sending test message to {iface}...")
    success, output, error = run_command(f"cansend {iface} {test_id}#{test_data} 2>&1")
    
    if "No buffer space available" in error or "No buffer space available" in output:
        print(f"❌ Send failed: No buffer space available")
        print(f"   This means no device is acknowledging CAN messages")
        print(f"   → Arm controller is likely not powered or not connected")
        return False
    elif "Invalid" in error or "invalid" in error.lower():
        print(f"⚠ Send command had issues (this is OK for test)")
        return True
    elif success:
        print(f"✓ CAN send appears to work")
        return True
    else:
        print(f"⚠ Send test result unclear")
        print(f"   Output: {output}")
        print(f"   Error: {error}")
        return True  # Don't fail on this

def check_arm_power_and_connection():
    """Check physical connection hints"""
    print_section("Step 5: Physical Connection Checklist")
    
    print("Please verify the following:")
    print("  [ ] Arm controller box is powered on (check for power LED)")
    print("  [ ] CAN cable is firmly connected to arm controller")
    print("  [ ] CAN cable is firmly connected to USB-to-CAN adapter")
    print("  [ ] USB-to-CAN adapter is plugged into computer")
    print("  [ ] Arm controller has status LEDs showing it's ready")
    print("  [ ] No error lights on the arm controller")
    print("\n  Common issues:")
    print("  • Controller needs separate power supply (not just USB)")
    print("  • CAN cable might need termination resistor")
    print("  • Wrong CAN port on controller (some have multiple ports)")

def suggest_solutions(iface="can0"):
    """Suggest solutions based on findings"""
    print_section("Recommended Solutions")
    
    print("1. ACTIVATE CAN INTERFACE:")
    print(f"   cd piper_sdk/piper_sdk")
    print(f"   bash can_activate.sh {iface} 1000000")
    print()
    
    print("2. IF MULTIPLE CAN DEVICES:")
    print(f"   bash find_all_can_port.sh")
    print(f"   # Then use the USB port address:")
    print(f"   bash can_activate.sh {iface} 1000000 \"USB_PORT_ADDRESS\"")
    print()
    
    print("3. RESET CAN INTERFACE:")
    print(f"   sudo ip link set {iface} down")
    print(f"   sudo ip link set {iface} type can bitrate 1000000")
    print(f"   sudo ip link set {iface} up")
    print()
    
    print("4. TEST WITH CANTOOLS:")
    print(f"   # In one terminal, listen:")
    print(f"   candump {iface}")
    print(f"   # In another terminal, send test:")
    print(f"   cansend {iface} 123#00.00.00.00")
    print()
    
    print("5. CHECK ARM CONTROLLER:")
    print("   • Power cycle the arm controller")
    print("   • Check controller documentation for CAN setup")
    print("   • Verify CAN baud rate matches (should be 1,000,000)")

def main():
    print("\n" + "=" * 60)
    print("  CAN CONNECTION DIAGNOSTIC TOOL")
    print("  For Piper Robotic Arm")
    print("=" * 60)
    
    # Step 1: Check if CAN interface exists
    exists, interfaces = check_can_interface_exists()
    if not exists:
        print("\n❌ CANNOT PROCEED: No CAN interfaces found")
        print("\nPlease:")
        print("  1. Plug in your USB-to-CAN adapter")
        print("  2. Run: bash piper_sdk/piper_sdk/find_all_can_port.sh")
        return 1
    
    # Use first interface or can0
    iface = "can0"
    if interfaces and "can0" not in interfaces:
        iface = interfaces[0]
        print(f"\n⚠ Note: Using interface {iface} (can0 not found)")
    
    # Step 2: Check interface status
    if not check_can_interface_status(iface):
        print(f"\n⚠ Interface {iface} needs to be activated")
        suggest_solutions(iface)
        return 1
    
    # Step 3: Test receive
    can_receive = test_can_receive(iface)
    
    # Step 4: Test send
    can_send = test_can_send(iface)
    
    # Step 5: Physical checklist
    check_arm_power_and_connection()
    
    # Summary
    print_section("DIAGNOSIS SUMMARY")
    
    if can_receive:
        print("✓ CAN communication is WORKING")
        print("  The arm is responding on the CAN bus")
        print("  Your pick_and_place script should work!")
    elif can_send:
        print("⚠ CAN interface works but arm is not responding")
        print("  → Check arm controller power and connection")
    else:
        print("❌ CAN communication is NOT working")
        print("  → Check physical connections and power")
    
    suggest_solutions(iface)
    
    return 0 if can_receive else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
