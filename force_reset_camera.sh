#!/bin/bash
# Force reset RealSense camera

echo "Resetting RealSense Camera..."
echo ""

# Kill any ROS processes using camera
echo "[1] Killing ROS camera processes..."
pkill -f realsense2_camera 2>/dev/null
pkill -f rs_launch 2>/dev/null
sleep 1

# Kill any Python processes using camera
echo "[2] Killing Python camera processes..."
pkill -f object_detection_pick_place 2>/dev/null
pkill -f "python.*camera" 2>/dev/null
sleep 1

# Try to reset via pyrealsense2 if available
echo "[3] Attempting camera reset via pyrealsense2..."
if python3 -c "import pyrealsense2" 2>/dev/null; then
    python3 << 'EOF'
import pyrealsense2 as rs
import time

try:
    ctx = rs.context()
    devices = ctx.query_devices()
    
    if len(devices) > 0:
        print(f"  Found {len(devices)} device(s)")
        for i, dev in enumerate(devices):
            serial = dev.get_info(rs.camera_info.serial_number)
            print(f"  Resetting device {i} (Serial: {serial})...")
            
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_device(serial)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            
            pipeline.start(config)
            time.sleep(0.5)
            pipeline.stop()
            print(f"  ✓ Device {i} reset")
    else:
        print("  No devices found")
except Exception as e:
    print(f"  Error: {e}")
EOF
else
    echo "  pyrealsense2 not available"
fi

echo ""
echo "[4] Checking for remaining processes..."
ps aux | grep -E "realsense|camera" | grep -v grep | head -3 || echo "  No camera processes found"

echo ""
echo "Reset complete! Try using the camera now."
