#!/bin/bash
# Start both camera and cube detection together

echo "=========================================="
echo "Starting RealSense Camera + Cube Detection"
echo "=========================================="

# Source ROS 2
source /opt/ros/jazzy/setup.bash 2>/dev/null || {
    echo "ERROR: ROS 2 Jazzy not found"
    exit 1
}

# Check if camera is already running
if ros2 node list 2>/dev/null | grep -q "camera"; then
    echo "⚠ Camera node already running"
    read -p "Kill existing camera node? [y/N]: " kill_cam
    if [ "$kill_cam" = "y" ] || [ "$kill_cam" = "Y" ]; then
        pkill -f realsense2_camera
        sleep 2
    else
        echo "Using existing camera node"
    fi
fi

# Start camera in background
echo ""
echo "Starting RealSense camera..."
ros2 launch realsense2_camera rs_launch.py \
    enable_infra1:=false \
    enable_infra2:=false \
    enable_gyro:=false \
    enable_accel:=false > /tmp/realsense_camera.log 2>&1 &
CAMERA_PID=$!

echo "Camera PID: $CAMERA_PID"
echo "Waiting for camera to initialize..."

# Wait for camera topics
for i in {1..30}; do
    if ros2 topic list 2>/dev/null | grep -q "camera.*color.*image_raw"; then
        echo "✓ Camera topics available!"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Check if camera started successfully
if ! ros2 topic list 2>/dev/null | grep -q "camera.*color.*image_raw"; then
    echo "ERROR: Camera failed to start!"
    echo "Check logs: tail -f /tmp/realsense_camera.log"
    kill $CAMERA_PID 2>/dev/null
    exit 1
fi

# Source workspace
if [ -f ~/ros2_ws/install/setup.bash ]; then
    source ~/ros2_ws/install/setup.bash
else
    echo "ERROR: Workspace not built!"
    exit 1
fi

# Start cube detection
echo ""
echo "Starting cube detection..."
echo ""
echo "You should see two OpenCV windows:"
echo "  - origin_image: Camera feed with detected cubes"
echo "  - hsv_image: HSV tuning interface"
echo ""
echo "Press Ctrl+C to stop both"
echo ""

# Trap Ctrl+C to kill both processes
trap "echo ''; echo 'Stopping...'; kill $CAMERA_PID 2>/dev/null; pkill -f cube_det; exit" INT

# Run cube detection in foreground
ros2 run cubeAndLineDet cube_det \
    --ros-args \
    -p image_topic_name:=/camera/camera/color/image_raw \
    -p camera_info_topic_name:=/camera/camera/color/camera_info \
    -p depth_topic_name:=/camera/camera/depth/image_rect_raw

# Cleanup on exit
kill $CAMERA_PID 2>/dev/null
pkill -f cube_det 2>/dev/null
