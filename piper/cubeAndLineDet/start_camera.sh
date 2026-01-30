#!/bin/bash
# Simple script to start RealSense camera

echo "Starting RealSense camera..."
echo "Press Ctrl+C to stop"
echo ""

# Deactivate venv if active (ROS 2 doesn't work well with venv)
deactivate 2>/dev/null || true

# Source ROS 2
source /opt/ros/jazzy/setup.bash

# Start camera
ros2 launch realsense2_camera rs_launch.py
