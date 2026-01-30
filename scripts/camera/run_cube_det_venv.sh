#!/bin/bash
# Run cube detection with correct topic remapping
# Works with venv or without

echo "=========================================="
echo "Running Cube Detection Node"
echo "=========================================="

# Source ROS 2
source /opt/ros/jazzy/setup.bash 2>/dev/null || {
    echo "ERROR: ROS 2 Jazzy not found"
    exit 1
}

# Source workspace
if [ -f ~/ros2_ws/install/setup.bash ]; then
    source ~/ros2_ws/install/setup.bash
    echo "✓ Workspace sourced"
else
    echo "⚠ Workspace not built. Building now..."
    cd ~/ros2_ws
    colcon build --packages-select cubeAndLineDet
    source install/setup.bash
fi

# Check if camera is running
echo ""
echo "Checking camera topics..."
if ros2 topic list 2>/dev/null | grep -q "camera.*color.*image"; then
    echo "✓ Camera topics found"
    ros2 topic list | grep -E "(color|depth)" | head -5
else
    echo "⚠ No camera topics found!"
    echo "  Start camera first:"
    echo "  ros2 launch realsense2_camera rs_launch.py"
    exit 1
fi

echo ""
echo "=========================================="
echo "Starting cube detection..."
echo "=========================================="
echo ""
echo "Topic remapping:"
echo "  image: /camera/camera/color/image_raw"
echo "  camera_info: /camera/camera/color/camera_info"
echo "  depth: /camera/camera/depth/image_rect_raw"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with topic remapping
ros2 run cubeAndLineDet cube_det \
    --ros-args \
    -p image_topic_name:=/camera/camera/color/image_raw \
    -p camera_info_topic_name:=/camera/camera/color/camera_info \
    -p depth_topic_name:=/camera/camera/depth/image_rect_raw
