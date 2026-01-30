#!/bin/bash
# Launch RealSense with IR error workaround

source /opt/ros/jazzy/setup.bash 2>/dev/null || {
    echo "ERROR: ROS 2 not found"
    exit 1
}

echo "Launching RealSense camera with IR workaround..."
echo ""
echo "Options:"
echo "  1. Disable IR stream (recommended if IR fails)"
echo "  2. Use color + depth only"
echo "  3. Standard launch (may have IR error)"
echo ""

read -p "Choose option [1-3] (default: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        echo "Launching without IR stream..."
        ros2 launch realsense2_camera rs_launch.py \
            enable_infra1:=false \
            enable_infra2:=false \
            enable_gyro:=false \
            enable_accel:=false
        ;;
    2)
        echo "Launching with color and depth only..."
        ros2 launch realsense2_camera rs_launch.py \
            enable_infra1:=false \
            enable_infra2:=false \
            enable_gyro:=false \
            enable_accel:=false \
            enable_color:=true \
            enable_depth:=true
        ;;
    3)
        echo "Launching standard configuration..."
        ros2 launch realsense2_camera rs_launch.py
        ;;
    *)
        echo "Invalid choice, using option 1"
        ros2 launch realsense2_camera rs_launch.py \
            enable_infra1:=false \
            enable_infra2:=false
        ;;
esac
