#!/bin/bash
# Complete ROS Noetic installation and workspace setup script
# Run this script with: bash install_ros_and_setup.sh

set -e

echo "=========================================="
echo "ROS Noetic Installation & Workspace Setup"
echo "=========================================="
echo ""

# Step 1: Add ROS repository
echo "[1/8] Adding ROS repository..."
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'

# Step 2: Add GPG key
echo "[2/8] Adding ROS GPG key..."
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# Step 3: Update package list
echo "[3/8] Updating package list..."
sudo apt update

# Step 4: Install ROS Noetic
echo "[4/8] Installing ROS Noetic Desktop Full (this may take a while)..."
sudo apt install -y ros-noetic-desktop-full

# Step 5: Install catkin tools
echo "[5/8] Installing catkin tools..."
sudo apt install -y python3-catkin-tools python3-osrf-pycommon

# Step 6: Install required ROS packages
echo "[6/8] Installing required ROS packages..."
sudo apt install -y \
    ros-noetic-sensor-msgs \
    ros-noetic-image-transport \
    ros-noetic-cv-bridge \
    ros-noetic-vision-msgs \
    ros-noetic-image-geometry \
    ros-noetic-pcl-conversions \
    ros-noetic-pcl-ros \
    ros-noetic-message-filters \
    ros-noetic-visualization-msgs \
    ros-noetic-geometry-msgs

# Step 7: Source ROS in bashrc
echo "[7/8] Adding ROS to ~/.bashrc..."
if ! grep -q "source /opt/ros/noetic/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
    echo "✓ Added ROS source to ~/.bashrc"
else
    echo "✓ ROS already in ~/.bashrc"
fi

# Source ROS for current session
source /opt/ros/noetic/setup.bash

# Step 8: Create and setup workspace
echo "[8/8] Creating catkin workspace..."
mkdir -p ~/piper_ws/src
cd ~/piper_ws/src

if [ ! -f "CMakeLists.txt" ]; then
    catkin_init_workspace
    echo "✓ Workspace initialized"
else
    echo "✓ Workspace already initialized"
fi

# Copy packages
echo ""
echo "Copying packages to workspace..."

# Try multiple possible locations for handpose_det
HANDPOSE_SRC1="$HOME/Documents/Realsense/librealsense/Agilex-College/piper/handpose_det"
HANDPOSE_SRC2="$HOME/Documents/Robotic AI/Robotic-AI/piper/handpose_det"

if [ -d "$HANDPOSE_SRC1" ]; then
    cp -r "$HANDPOSE_SRC1" ~/piper_ws/src/
    echo "✓ handpose_det copied from $HANDPOSE_SRC1"
elif [ -d "$HANDPOSE_SRC2" ]; then
    cp -r "$HANDPOSE_SRC2" ~/piper_ws/src/
    echo "✓ handpose_det copied from $HANDPOSE_SRC2"
else
    echo "⚠ handpose_det not found in expected locations"
    echo "  Please copy it manually: cp -r <path>/handpose_det ~/piper_ws/src/"
fi

# Try multiple possible locations for piper_kinematics
KINEMATICS_SRC1="$HOME/Documents/Realsense/librealsense/Agilex-College/piper/piper_kinematics"
KINEMATICS_SRC2="$HOME/Documents/Robotic AI/Robotic-AI/piper/piper_kinematics"

if [ -d "$KINEMATICS_SRC1" ]; then
    cp -r "$KINEMATICS_SRC1" ~/piper_ws/src/
    echo "✓ piper_kinematics copied from $KINEMATICS_SRC1"
elif [ -d "$KINEMATICS_SRC2" ]; then
    cp -r "$KINEMATICS_SRC2" ~/piper_ws/src/
    echo "✓ piper_kinematics copied from $KINEMATICS_SRC2"
fi

# Build workspace
echo ""
echo "Building workspace..."
cd ~/piper_ws
source /opt/ros/noetic/setup.bash
catkin_make

# Add workspace to bashrc
if ! grep -q "source ~/piper_ws/devel/setup.bash" ~/.bashrc; then
    echo "source ~/piper_ws/devel/setup.bash" >> ~/.bashrc
    echo "✓ Added workspace to ~/.bashrc"
fi

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Workspace location: ~/piper_ws"
echo ""
echo "To use the workspace in a new terminal:"
echo "  source ~/piper_ws/devel/setup.bash"
echo ""
echo "Or just open a new terminal (already added to ~/.bashrc)"
echo ""
