#!/bin/bash
# Setup script for ROS workspace and handpose_det package

set -e

echo "=========================================="
echo "ROS Workspace Setup Script"
echo "=========================================="

# Check if ROS is installed
if [ -z "$ROS_DISTRO" ]; then
    echo "ROS is not installed or not sourced."
    echo ""
    echo "Please install ROS first:"
    echo ""
    echo "For Ubuntu 20.04 (ROS Noetic):"
    echo "  sudo sh -c 'echo \"deb http://packages.ros.org/ros/ubuntu \$(lsb_release -sc) main\" > /etc/apt/sources.list.d/ros-latest.list'"
    echo "  sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654"
    echo "  sudo apt update"
    echo "  sudo apt install -y ros-noetic-desktop-full"
    echo "  echo 'source /opt/ros/noetic/setup.bash' >> ~/.bashrc"
    echo "  source ~/.bashrc"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✓ ROS $ROS_DISTRO detected"

# Check if catkin tools are installed
if ! command -v catkin_make &> /dev/null; then
    echo "Installing catkin tools..."
    sudo apt install -y python3-catkin-tools python3-osrf-pycommon
fi

echo "✓ catkin_make available"

# Determine workspace location
WORKSPACE_NAME="piper_ws"
WORKSPACE_PATH="$HOME/$WORKSPACE_NAME"

# Ask user for workspace location
echo ""
echo "Where would you like to create the catkin workspace?"
echo "1. $WORKSPACE_PATH (default)"
echo "2. Custom location"
read -p "Enter choice [1-2] (default: 1): " choice

if [ "$choice" == "2" ]; then
    read -p "Enter full path for workspace: " WORKSPACE_PATH
fi

# Create workspace structure
echo ""
echo "Creating catkin workspace at: $WORKSPACE_PATH"
mkdir -p "$WORKSPACE_PATH/src"
cd "$WORKSPACE_PATH"

# Initialize workspace
if [ ! -f "$WORKSPACE_PATH/src/CMakeLists.txt" ]; then
    catkin_init_workspace "$WORKSPACE_PATH/src"
    echo "✓ Workspace initialized"
else
    echo "✓ Workspace already initialized"
fi

# Source ROS setup
source /opt/ros/$ROS_DISTRO/setup.bash

# Install required ROS packages
echo ""
echo "Installing required ROS packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-sensor-msgs \
    ros-$ROS_DISTRO-image-transport \
    ros-$ROS_DISTRO-cv-bridge \
    ros-$ROS_DISTRO-vision-msgs \
    ros-$ROS_DISTRO-image-geometry \
    ros-$ROS_DISTRO-pcl-conversions \
    ros-$ROS_DISTRO-pcl-ros \
    ros-$ROS_DISTRO-message-filters \
    ros-$ROS_DISTRO-visualization-msgs \
    ros-$ROS_DISTRO-geometry-msgs

echo "✓ ROS packages installed"

# Copy handpose_det package
HANDPOSE_SRC="$HOME/Documents/Realsense/librealsense/Agilex-College/piper/handpose_det"
if [ -d "$HANDPOSE_SRC" ]; then
    echo ""
    echo "Copying handpose_det package..."
    cp -r "$HANDPOSE_SRC" "$WORKSPACE_PATH/src/"
    echo "✓ handpose_det copied to workspace"
elif [ -d "$HOME/Documents/Robotic AI/Robotic-AI/piper/handpose_det" ]; then
    echo ""
    echo "Copying handpose_det package from alternative location..."
    cp -r "$HOME/Documents/Robotic AI/Robotic-AI/piper/handpose_det" "$WORKSPACE_PATH/src/"
    echo "✓ handpose_det copied to workspace"
else
    echo ""
    echo "⚠ handpose_det package not found. Please clone it manually:"
    echo "  cd $WORKSPACE_PATH/src"
    echo "  git clone https://github.com/agilexrobotics/Agilex-College.git"
    echo "  cp -r Agilex-College/piper/handpose_det ."
fi

# Copy piper_kinematics if it exists
KINEMATICS_SRC="$HOME/Documents/Realsense/librealsense/Agilex-College/piper/piper_kinematics"
if [ -d "$KINEMATICS_SRC" ]; then
    echo ""
    echo "Copying piper_kinematics package..."
    cp -r "$KINEMATICS_SRC" "$WORKSPACE_PATH/src/"
    echo "✓ piper_kinematics copied to workspace"
fi

# Build workspace
echo ""
echo "Building workspace..."
cd "$WORKSPACE_PATH"
source /opt/ros/$ROS_DISTRO/setup.bash
catkin_make

echo ""
echo "=========================================="
echo "✓ Workspace setup complete!"
echo "=========================================="
echo ""
echo "To use the workspace, run:"
echo "  source $WORKSPACE_PATH/devel/setup.bash"
echo ""
echo "Or add to your ~/.bashrc:"
echo "  echo 'source $WORKSPACE_PATH/devel/setup.bash' >> ~/.bashrc"
echo ""
