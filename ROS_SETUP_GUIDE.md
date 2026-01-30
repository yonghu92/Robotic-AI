# ROS Setup Guide for Ubuntu 24.04

## Important Note
You're running **Ubuntu 24.04**, but the README specifies **ROS Noetic** which is designed for **Ubuntu 20.04**. 

You have a few options:

## Option 1: Install ROS Noetic on Ubuntu 24.04 (May have compatibility issues)

```bash
# Add ROS Noetic repository
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
sudo apt update

# Install ROS Noetic
sudo apt install -y ros-noetic-desktop-full

# Install catkin tools
sudo apt install -y python3-catkin-tools python3-osrf-pycommon

# Source ROS
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## Option 2: Use ROS 2 (If the code supports it)

Ubuntu 24.04 supports ROS 2 Jazzy:

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -
sudo sh -c 'echo "deb [arch=$(dpkg --print-architecture)] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" > /etc/apt/sources.list.d/ros2-latest.list'
sudo apt update
sudo apt install -y ros-jazzy-desktop
```

**Note:** The handpose_det package appears to be written for ROS 1, so this may require code modifications.

## Option 3: Create Catkin Workspace Manually (After installing ROS)

Once ROS is installed, create your workspace:

```bash
# Create workspace
mkdir -p ~/piper_ws/src
cd ~/piper_ws/src

# Initialize workspace
catkin_init_workspace

# Copy packages
cd ~/Documents/Realsense/librealsense/Agilex-College/piper/
cp -r handpose_det ~/piper_ws/src/
cp -r piper_kinematics ~/piper_ws/src/  # if needed

# Install dependencies
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

# Build
cd ~/piper_ws
source /opt/ros/noetic/setup.bash
catkin_make

# Source workspace
source devel/setup.bash
```

## Quick Setup Script

I've created a setup script for you. First install ROS, then run:

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI
./setup_ros_workspace.sh
```
