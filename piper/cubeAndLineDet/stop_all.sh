#!/bin/bash
# Stop all camera and detection processes

echo "=========================================="
echo "Stopping Camera and Detection Processes"
echo "=========================================="

# Find and kill cube_det processes
CUBE_PIDS=$(pgrep -f "cube_det" || echo "")
if [ -n "$CUBE_PIDS" ]; then
    echo "Stopping cube_det processes..."
    echo "$CUBE_PIDS" | xargs kill -9 2>/dev/null
    echo "✓ Stopped cube_det"
else
    echo "✓ No cube_det processes running"
fi

# Find and kill line_det processes
LINE_PIDS=$(pgrep -f "line_det" || echo "")
if [ -n "$LINE_PIDS" ]; then
    echo "Stopping line_det processes..."
    echo "$LINE_PIDS" | xargs kill -9 2>/dev/null
    echo "✓ Stopped line_det"
else
    echo "✓ No line_det processes running"
fi

# Find and kill camera processes
CAMERA_PIDS=$(pgrep -f "realsense2_camera" || echo "")
if [ -n "$CAMERA_PIDS" ]; then
    echo "Stopping camera processes..."
    echo "$CAMERA_PIDS" | xargs kill -9 2>/dev/null
    sleep 2
    echo "✓ Stopped camera"
else
    echo "✓ No camera processes running"
fi

# Kill any remaining ros2 launch processes
LAUNCH_PIDS=$(pgrep -f "ros2 launch" || echo "")
if [ -n "$LAUNCH_PIDS" ]; then
    echo "Stopping ros2 launch processes..."
    echo "$LAUNCH_PIDS" | xargs kill -9 2>/dev/null
    echo "✓ Stopped ros2 launch"
fi

echo ""
echo "=========================================="
echo "All processes stopped!"
echo "=========================================="
echo ""
echo "You can now start fresh:"
echo "  1. Start camera: bash start_camera.sh"
echo "  2. Start detection: bash check_and_run.sh"
