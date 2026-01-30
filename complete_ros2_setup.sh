#!/bin/bash
# Complete ROS 2 Setup Script
# Completes todos: Install RealSense, dependencies, build workspace, run cube_det

set -e

echo "=========================================="
echo "ROS 2 Setup - Completing Todos"
echo "=========================================="

# Source ROS 2
source /opt/ros/jazzy/setup.bash 2>/dev/null || {
    echo "ERROR: ROS 2 Jazzy not found. Please install it first."
    exit 1
}

echo "✓ ROS 2 Jazzy sourced"

# TODO 2: Install RealSense ROS2 wrapper
echo ""
echo "=========================================="
echo "TODO 2: Installing RealSense ROS2 wrapper"
echo "=========================================="

if ros2 pkg list | grep -q realsense2_camera; then
    echo "✓ RealSense ROS2 wrapper already installed"
else
    echo "Installing RealSense ROS2 wrapper..."
    sudo apt update
    sudo apt install -y ros-jazzy-realsense2-camera
    
    if ros2 pkg list | grep -q realsense2_camera; then
        echo "✓ RealSense ROS2 wrapper installed successfully"
    else
        echo "⚠ RealSense ROS2 wrapper installation may have failed"
        echo "  You may need to build from source:"
        echo "  https://github.com/IntelRealSense/realsense-ros"
    fi
fi

# TODO 3: Install missing ROS2 dependencies
echo ""
echo "=========================================="
echo "TODO 3: Installing missing ROS2 dependencies"
echo "=========================================="

echo "Installing ROS 2 packages..."
sudo apt install -y \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-visualization-msgs \
    ros-jazzy-pcl-conversions \
    ros-jazzy-sensor-msgs \
    ros-jazzy-geometry-msgs \
    ros-jazzy-std-msgs \
    ros-jazzy-rclcpp \
    ros-jazzy-image-geometry

echo "Installing system dependencies..."
sudo apt install -y \
    libopencv-dev \
    libpcl-dev \
    libeigen3-dev \
    python3-catkin-pkg

echo "✓ Dependencies installed"

# Check if workspace exists
if [ ! -d ~/ros2_ws ]; then
    echo ""
    echo "Creating ROS 2 workspace..."
    mkdir -p ~/ros2_ws/src
fi

# Check if package is in workspace
if [ ! -d ~/ros2_ws/src/cubeAndLineDet ]; then
    echo ""
    echo "Copying cubeAndLineDet package to workspace..."
    if [ -d ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet ]; then
        cp -r ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet ~/ros2_ws/src/
        echo "✓ Package copied"
    else
        echo "ERROR: cubeAndLineDet package not found!"
        exit 1
    fi
fi

# TODO 4: Build ROS2 workspace
echo ""
echo "=========================================="
echo "TODO 4: Building ROS2 workspace"
echo "=========================================="

cd ~/ros2_ws

# Deactivate venv if active
deactivate 2>/dev/null || true

# Unset PYTHONPATH to avoid conflicts
unset PYTHONPATH

# Source ROS 2 again
source /opt/ros/jazzy/setup.bash

echo "Building cubeAndLineDet package..."
colcon build --packages-select cubeAndLineDet

if [ $? -eq 0 ]; then
    echo "✓ Build successful!"
else
    echo "⚠ Build failed. Check errors above."
    exit 1
fi

# Source the workspace
source ~/ros2_ws/install/setup.bash

# Verify package is available
if ros2 pkg list | grep -q cubeAndLineDet; then
    echo "✓ Package registered in ROS 2"
else
    echo "⚠ Package not found in ROS 2 package list"
fi

# TODO 5: Instructions for running cube_det
echo ""
echo "=========================================="
echo "TODO 5: Running cube_det node"
echo "=========================================="
echo ""
echo "To run the cube detection node:"
echo ""
echo "Terminal 1 - Start RealSense camera:"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  source ~/ros2_ws/install/setup.bash"
echo "  ros2 launch realsense2_camera rs_launch.py"
echo ""
echo "Terminal 2 - Run cube detection:"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  source ~/ros2_ws/install/setup.bash"
echo "  ros2 run cubeAndLineDet cube_det"
echo ""
echo "Or use the quick start script:"
echo "  bash ~/ros2_ws/run_cube_detection.sh"
echo ""

echo "=========================================="
echo "✓ All setup tasks completed!"
echo "=========================================="
