#!/usr/bin/env python3
"""
Intel RealSense Camera Test Script
Tests if the RealSense camera is working properly
"""

import sys
import subprocess

def check_usb_device():
    """Check if RealSense camera is detected via USB"""
    print("=" * 60)
    print("1. Checking USB Device Detection")
    print("=" * 60)
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True, check=True)
        if 'Intel' in result.stdout and 'RealSense' in result.stdout:
            print("✓ RealSense camera detected via USB:")
            for line in result.stdout.split('\n'):
                if 'Intel' in line and 'RealSense' in line:
                    print(f"  {line}")
            return True
        else:
            print("✗ RealSense camera NOT detected via USB")
            return False
    except Exception as e:
        print(f"✗ Error checking USB: {e}")
        return False

def test_pyrealsense2():
    """Test using pyrealsense2 library"""
    print("\n" + "=" * 60)
    print("2. Testing with pyrealsense2 library")
    print("=" * 60)
    try:
        import pyrealsense2 as rs
        print(f"✓ pyrealsense2 imported successfully (version: {rs.__version__})")
        
        # Create a pipeline
        pipeline = rs.pipeline()
        config = rs.config()
        
        # Try to detect devices
        ctx = rs.context()
        devices = ctx.query_devices()
        
        if len(devices) == 0:
            print("✗ No RealSense devices found")
            return False
        
        print(f"✓ Found {len(devices)} RealSense device(s):")
        for i, dev in enumerate(devices):
            print(f"  Device {i}: {dev.get_info(rs.camera_info.name)}")
            print(f"    Serial: {dev.get_info(rs.camera_info.serial_number)}")
            print(f"    Firmware: {dev.get_info(rs.camera_info.firmware_version)}")
        
        # Try to start streaming
        print("\n  Attempting to start color stream...")
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        try:
            pipeline.start(config)
            print("✓ Pipeline started successfully")
            
            # Try to get a frame
            print("  Waiting for frames...")
            frames = pipeline.wait_for_frames(timeout_ms=5000)
            color_frame = frames.get_color_frame()
            
            if color_frame:
                print(f"✓ Successfully received color frame!")
                print(f"    Resolution: {color_frame.get_width()}x{color_frame.get_height()}")
                pipeline.stop()
                return True
            else:
                print("✗ No color frame received")
                pipeline.stop()
                return False
                
        except Exception as e:
            print(f"✗ Error starting pipeline: {e}")
            return False
            
    except ImportError:
        print("✗ pyrealsense2 not installed")
        print("  Install with: pip install pyrealsense2")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_opencv():
    """Test using OpenCV (fallback method)"""
    print("\n" + "=" * 60)
    print("3. Testing with OpenCV (fallback)")
    print("=" * 60)
    try:
        import cv2
        print(f"✓ OpenCV imported successfully (version: {cv2.__version__})")
        
        # Try to open video capture devices
        print("\n  Checking available video devices...")
        available_cameras = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"  ✓ Camera {i}: Working (resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})")
                    available_cameras.append(i)
                cap.release()
            else:
                cap.release()
        
        if available_cameras:
            print(f"\n✓ Found {len(available_cameras)} working camera(s) at index(es): {available_cameras}")
            return True
        else:
            print("\n✗ No working cameras found via OpenCV")
            return False
            
    except ImportError:
        print("✗ OpenCV not installed")
        print("  Install with: pip install opencv-python")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_v4l2():
    """Test using v4l2 tools if available"""
    print("\n" + "=" * 60)
    print("4. Testing with v4l2 (if available)")
    print("=" * 60)
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ v4l2-ctl available")
            if 'RealSense' in result.stdout or 'Intel' in result.stdout:
                print("✓ RealSense camera found in v4l2 devices:")
                for line in result.stdout.split('\n'):
                    if 'RealSense' in line or 'Intel' in line or '/dev/video' in line:
                        print(f"  {line}")
                return True
            else:
                print("✗ RealSense camera not found in v4l2 devices")
                print("  Available devices:")
                print(result.stdout)
                return False
        else:
            print("✗ v4l2-ctl command failed")
            return False
    except FileNotFoundError:
        print("✗ v4l2-utils not installed")
        print("  Install with: sudo apt install v4l-utils")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("Intel RealSense Camera Diagnostic Test")
    print("=" * 60 + "\n")
    
    results = {}
    
    # Test 1: USB detection
    results['usb'] = check_usb_device()
    
    # Test 2: pyrealsense2
    results['pyrealsense2'] = test_pyrealsense2()
    
    # Test 3: OpenCV
    results['opencv'] = test_opencv()
    
    # Test 4: v4l2
    results['v4l2'] = test_v4l2()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if results['usb']:
        print("✓ USB Detection: PASS")
    else:
        print("✗ USB Detection: FAIL - Camera not detected at USB level")
    
    if results['pyrealsense2'] is True:
        print("✓ pyrealsense2: PASS - Camera working with RealSense SDK")
    elif results['pyrealsense2'] is False:
        print("✗ pyrealsense2: FAIL - Camera detected but not working")
    else:
        print("? pyrealsense2: NOT TESTED - Library not installed")
    
    if results['opencv'] is True:
        print("✓ OpenCV: PASS - Camera accessible via OpenCV")
    elif results['opencv'] is False:
        print("✗ OpenCV: FAIL - Camera not accessible via OpenCV")
    else:
        print("? OpenCV: NOT TESTED - Library not installed")
    
    if results['v4l2'] is True:
        print("✓ v4l2: PASS - Camera accessible via v4l2")
    elif results['v4l2'] is False:
        print("✗ v4l2: FAIL - Camera not accessible via v4l2")
    else:
        print("? v4l2: NOT TESTED - Tools not installed")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if not results['usb']:
        print("1. Check USB cable connection")
        print("2. Try a different USB port (preferably USB 3.0)")
        print("3. Check if camera works on another computer")
    elif results['usb'] and results['pyrealsense2'] is None:
        print("1. Install pyrealsense2: pip install pyrealsense2")
        print("2. Or install RealSense SDK: https://github.com/IntelRealSense/librealsense")
    elif results['usb'] and results['pyrealsense2'] is False:
        print("1. Check camera permissions: sudo usermod -a -G dialout $USER")
        print("2. Check USB power - try powered USB hub")
        print("3. Reinstall RealSense SDK")
        print("4. Check dmesg for USB errors: dmesg | tail -20")
    elif results['usb'] and results['pyrealsense2'] is True:
        print("✓ Camera is working correctly!")
    
    print()

if __name__ == "__main__":
    main()
