# Quick Setup Guide - Fix catkin_make Issue

## Problem
- `catkin_make` command not found
- `your_ws` is a placeholder, not a real directory

## Solution

### Step 1: Install ROS Noetic

Since you're on Ubuntu 24.04, you need to install ROS Noetic manually:

```bash
# Add ROS repository
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'

# Add GPG key
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# Update package list
sudo apt update

# Install ROS Noetic
sudo apt install -y ros-noetic-desktop-full

# Install catkin tools
sudo apt install -y python3-catkin-tools python3-osrf-pycommon

# Source ROS (add to bashrc)
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### Step 2: Create Your Catkin Workspace

Replace `your_ws` with an actual workspace name:

```bash
# Create workspace directory
mkdir -p ~/piper_ws/src
cd ~/piper_ws/src

# Initialize catkin workspace
catkin_init_workspace

# Go back to workspace root
cd ~/piper_ws
```

### Step 3: Install Required ROS Packages

```bash
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
```

### Step 4: Copy Packages to Workspace

```bash
# Navigate to where you cloned Agilex-College
cd ~/Documents/Realsense/librealsense/Agilex-College/piper/

# Copy handpose_det package
cp -r handpose_det ~/piper_ws/src/

# Copy piper_kinematics if needed
cp -r piper_kinematics ~/piper_ws/src/
```

### Step 5: Build the Workspace

```bash
# Make sure ROS is sourced
source /opt/ros/noetic/setup.bash

# Navigate to workspace
cd ~/piper_ws

# Build
catkin_make

# Source the workspace
source devel/setup.bash
```

### Step 6: Verify Installation

```bash
# Check if packages are found
rospack find handpose_det

# Should output: /home/robotics_urop/piper_ws/src/handpose_det
```

## All-in-One Commands

Copy and paste this entire block:

```bash
# Install ROS Noetic
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
sudo apt update
sudo apt install -y ros-noetic-desktop-full python3-catkin-tools python3-osrf-pycommon
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc

# Create workspace
mkdir -p ~/piper_ws/src
cd ~/piper_ws/src
catkin_init_workspace

# Install dependencies
sudo apt install -y ros-noetic-sensor-msgs ros-noetic-image-transport ros-noetic-cv-bridge ros-noetic-vision-msgs ros-noetic-image-geometry ros-noetic-pcl-conversions ros-noetic-pcl-ros ros-noetic-message-filters ros-noetic-visualization-msgs ros-noetic-geometry-msgs

# Copy packages
cd ~/Documents/Realsense/librealsense/Agilex-College/piper/
cp -r handpose_det ~/piper_ws/src/
cp -r piper_kinematics ~/piper_ws/src/ 2>/dev/null || echo "piper_kinematics not found, skipping"

# Build
cd ~/piper_ws
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash

echo "✓ Setup complete! Workspace is at ~/piper_ws"
```
