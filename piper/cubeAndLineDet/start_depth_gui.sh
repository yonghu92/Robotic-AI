#!/bin/bash
# Start Depth Camera GUI Viewer

echo "=========================================="
echo "Starting Depth Camera GUI Viewer"
echo "=========================================="

# Check if camera is running
if ! ros2 node list 2>/dev/null | grep -q "camera"; then
    echo "⚠ Camera not detected!"
    echo "  Starting camera in background..."
    source /opt/ros/jazzy/setup.bash
    ros2 launch realsense2_camera rs_launch.py > /tmp/camera.log 2>&1 &
    CAMERA_PID=$!
    echo "  Camera PID: $CAMERA_PID"
    echo "  Waiting for camera to initialize..."
    sleep 5
fi

# Check if topics exist
if ! ros2 topic list 2>/dev/null | grep -q "camera.*depth"; then
    echo "⚠ Depth topics not found!"
    echo "  Make sure camera is running: ros2 launch realsense2_camera rs_launch.py"
    exit 1
fi

echo "✓ Camera topics found"
echo ""
echo "Starting GUI..."
echo ""

# Activate venv if exists and run GUI
cd ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet

if [ -f ~/Documents/Robotic\ AI/Robotic-AI/venv/bin/activate ]; then
    source ~/Documents/Robotic\ AI/Robotic-AI/venv/bin/activate
fi

source /opt/ros/jazzy/setup.bash

# Install tkinter if needed (usually comes with Python)
python3 -c "import tkinter" 2>/dev/null || {
    echo "⚠ tkinter not found. Installing..."
    sudo apt install -y python3-tk
}

python3 depth_camera_gui.py
