#!/bin/bash
# Start Intel RealSense Camera Viewer

echo "Starting RealSense Camera Viewer..."
echo ""

# Method 1: Try realsense-viewer (if installed)
if command -v realsense-viewer &> /dev/null; then
    echo "Using realsense-viewer..."
    realsense-viewer
    exit 0
fi

# Method 2: Try ROS 2 image viewer
echo "realsense-viewer not found. Using ROS 2 method..."
echo ""

# Check if ROS 2 is available
if [ -z "$ROS_DISTRO" ]; then
    source /opt/ros/jazzy/setup.bash 2>/dev/null
fi

if [ -z "$ROS_DISTRO" ]; then
    echo "ERROR: ROS 2 not found. Please install ROS 2 Jazzy first."
    exit 1
fi

echo "ROS 2 $ROS_DISTRO detected"
echo ""

# Start RealSense camera node in background
echo "[1] Starting RealSense camera driver..."
ros2 run realsense2_camera realsense2_camera_node &
CAMERA_PID=$!
sleep 3

# Check if camera started
if ! ps -p $CAMERA_PID > /dev/null; then
    echo "ERROR: Failed to start camera node"
    exit 1
fi

echo "  Camera node started (PID: $CAMERA_PID)"
echo ""

# Check available topics
echo "[2] Available camera topics:"
ros2 topic list | grep camera | head -5
echo ""

# Start image viewer
echo "[3] Starting image viewer..."
echo "  Viewing: /camera/color/image_raw"
echo "  Press Ctrl+C to stop"
echo ""

ros2 run image_view image_view --ros-args --remap /image:=/camera/color/image_raw

# Cleanup
echo ""
echo "Stopping camera node..."
kill $CAMERA_PID 2>/dev/null
echo "Done!"
