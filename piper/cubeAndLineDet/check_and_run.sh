#!/bin/bash
# Simple script to check what's running and start cube/line detection

echo "=========================================="
echo "Checking Current Status..."
echo "=========================================="

# Source ROS 2
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
    echo "✓ ROS 2 Jazzy sourced"
else
    echo "✗ ROS 2 Jazzy not found at /opt/ros/jazzy/"
    echo "  Please install ROS 2 or check your installation"
    exit 1
fi

# Source workspace
if [ -f ~/ros2_ws/install/setup.bash ]; then
    source ~/ros2_ws/install/setup.bash
    echo "✓ ROS 2 workspace sourced"
else
    echo "✗ Workspace not found at ~/ros2_ws/"
    echo "  The package may need to be built first"
    exit 1
fi

# Check if package is available
if ros2 pkg list 2>/dev/null | grep -q cubeAndLineDet; then
    echo "✓ cubeAndLineDet package found"
else
    echo "✗ cubeAndLineDet package not found"
    echo "  Run: cd ~/ros2_ws && colcon build --packages-select cubeAndLineDet"
    exit 1
fi

echo ""
echo "=========================================="
echo "Checking Running Nodes..."
echo "=========================================="

# Check for camera nodes
CAMERA_NODES=$(ros2 node list 2>/dev/null | grep -iE "camera|realsense|astra" || echo "")
if [ -n "$CAMERA_NODES" ]; then
    echo "✓ Camera nodes running:"
    echo "$CAMERA_NODES" | sed 's/^/  /'
else
    echo "⚠ No camera nodes detected"
fi

# Check for detection nodes
DETECTION_NODES=$(ros2 node list 2>/dev/null | grep -iE "cube|line" || echo "")
if [ -n "$DETECTION_NODES" ]; then
    echo "✓ Detection nodes running:"
    echo "$DETECTION_NODES" | sed 's/^/  /'
else
    echo "⚠ No detection nodes running"
fi

echo ""
echo "=========================================="
echo "Checking Camera Topics..."
echo "=========================================="

# Check for camera topics
CAMERA_TOPICS=$(ros2 topic list 2>/dev/null | grep -iE "camera.*(color|depth|image)" | head -5 || echo "")
if [ -n "$CAMERA_TOPICS" ]; then
    echo "✓ Camera topics available:"
    echo "$CAMERA_TOPICS" | sed 's/^/  /'
    CAMERA_RUNNING=true
else
    echo "⚠ No camera topics found"
    echo "  You may need to start the camera driver first"
    CAMERA_RUNNING=false
fi

echo ""
echo "=========================================="
echo "What would you like to do?"
echo "=========================================="
echo ""
echo "1) Start cube detection (cube_det)"
echo "2) Start line detection (line_det)"
echo "3) Start RealSense camera (if not running)"
echo "4) Check status only (exit)"
echo "5) View all available topics"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Starting cube detection..."
        echo "Press Ctrl+C to stop"
        echo ""
        if [ "$CAMERA_RUNNING" = false ]; then
            echo "⚠ Warning: Camera may not be running!"
            echo "  Start camera in another terminal:"
            echo "    ros2 launch realsense2_camera rs_launch.py"
            echo ""
            read -p "Continue anyway? [y/N]: " continue_anyway
            if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
                exit 0
            fi
        fi
        ros2 run cubeAndLineDet cube_det
        ;;
    2)
        echo ""
        echo "Starting line detection..."
        echo "Press Ctrl+C to stop"
        echo ""
        if [ "$CAMERA_RUNNING" = false ]; then
            echo "⚠ Warning: Camera may not be running!"
            echo "  Start camera in another terminal:"
            echo "    ros2 launch realsense2_camera rs_launch.py"
            echo ""
            read -p "Continue anyway? [y/N]: " continue_anyway
            if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
                exit 0
            fi
        fi
        ros2 run cubeAndLineDet line_det
        ;;
    3)
        echo ""
        echo "Starting RealSense camera..."
        echo "This will run in the background"
        echo "Press Ctrl+C to stop"
        echo ""
        ros2 launch realsense2_camera rs_launch.py
        ;;
    4)
        echo ""
        echo "Status check complete. Exiting."
        exit 0
        ;;
    5)
        echo ""
        echo "All available topics:"
        ros2 topic list 2>/dev/null | head -30
        echo ""
        echo "(Showing first 30 topics. Use 'ros2 topic list' for full list)"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac
