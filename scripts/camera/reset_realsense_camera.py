#!/usr/bin/env python3
"""
Reset RealSense Camera - Connect and Disconnect to Free It
"""

import sys
import time

print("=" * 60)
print("RealSense Camera Reset Tool")
print("=" * 60)

# Try pyrealsense2 first
try:
    import pyrealsense2 as rs
    print("\n[1] Using pyrealsense2 to reset camera...")
    
    ctx = rs.context()
    devices = ctx.query_devices()
    
    if len(devices) == 0:
        print("  No RealSense devices found")
    else:
        print(f"  Found {len(devices)} device(s):")
        for i, dev in enumerate(devices):
            name = dev.get_info(rs.camera_info.name)
            serial = dev.get_info(rs.camera_info.serial_number)
            print(f"    Device {i}: {name} (Serial: {serial})")
            
            # Try to create and destroy pipeline to reset
            try:
                pipeline = rs.pipeline()
                config = rs.config()
                config.enable_device(serial)
                config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
                
                print(f"    Connecting to device {i}...")
                pipeline.start(config)
                time.sleep(0.5)  # Brief connection
                
                print(f"    Disconnecting from device {i}...")
                pipeline.stop()
                print(f"    ✓ Device {i} reset successfully")
                
            except Exception as e:
                print(f"    ⚠ Error resetting device {i}: {e}")
    
    print("\n[2] Camera reset complete via pyrealsense2")
    
except ImportError:
    print("\n[1] pyrealsense2 not available, trying OpenCV method...")
    
    import cv2
    
    # Try to open and close camera via OpenCV
    print("  Attempting to reset via OpenCV...")
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"  Found camera at index {i}, connecting...")
                ret, frame = cap.read()
                if ret:
                    print(f"  Camera {i} is accessible")
                print(f"  Disconnecting camera {i}...")
                cap.release()
                print(f"  ✓ Camera {i} released")
        except Exception as e:
            print(f"  Error with camera {i}: {e}")
    
    print("\n[2] Camera reset complete via OpenCV")

# Additional cleanup - kill any stuck processes
print("\n[3] Checking for processes that might be using the camera...")
import subprocess

try:
    # Check for video devices
    result = subprocess.run(['lsof', '/dev/video*'], 
                           capture_output=True, text=True, timeout=2)
    if result.returncode == 0 and result.stdout:
        print("  Processes using video devices:")
        print(result.stdout)
    else:
        print("  No processes found using /dev/video*")
except:
    print("  Could not check video device usage")

print("\n" + "=" * 60)
print("Reset Complete!")
print("=" * 60)
print("\nYou can now try using the camera again.")
print("If it's still busy, you may need to:")
print("  1. Unplug and replug the USB cable")
print("  2. Restart any applications using the camera")
print("  3. Reboot the system if needed")
