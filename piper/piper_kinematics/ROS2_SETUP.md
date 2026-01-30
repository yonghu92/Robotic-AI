# ROS2 Setup Guide for piper_kinematics

## Quick Start

### 1. Install Dependencies

```bash
# Install ROS2 interactive markers
sudo apt install -y ros-jazzy-interactive-markers

# Install Eigen3
sudo apt install -y libeigen3-dev

# Install other ROS2 packages
sudo apt install -y \
    ros-jazzy-visualization-msgs \
    ros-jazzy-geometry-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf2-geometry-msgs \
    ros-jazzy-rclpy
```

### 2. Build the Package

```bash
# Source ROS2
source /opt/ros/jazzy/setup.bash

# Create workspace if needed
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# Copy the package
cp -r ~/Documents/Robotic\ AI/Robotic-AI/piper/piper_kinematics ~/ros2_ws/src/

# Fix package.xml (if needed)
sed -i 's/<n>/<name>/g; s/<\/n>/<\/name>/g' ~/ros2_ws/src/piper_kinematics/package.xml

# Build
cd ~/ros2_ws
colcon build --packages-select piper_kinematics

# Source workspace
source ~/ros2_ws/install/setup.bash
```

### 3. Run the Node

```bash
# Make sure ROS2 is sourced
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Run the interactive pose marker
ros2 run piper_kinematics interactive_pose_marker.py

# Or use the launch file
ros2 launch piper_kinematics piper_ik.launch.py
```

## Testing

### Check Topics

```bash
# List topics
ros2 topic list

# Echo target pose
ros2 topic echo /target_pose

# Check TF
ros2 run tf2_ros tf2_echo base_link target_pose
```

## Troubleshooting

### Error: "No module named 'interactive_markers'"

**Solution:**
```bash
sudo apt install -y ros-jazzy-interactive-markers
```

If the package doesn't exist for Jazzy, you may need to:
1. Build from source: https://github.com/ros2/interactive_markers
2. Or use an alternative approach

### Error: "Package not found"

**Solution:**
```bash
# Make sure you sourced the workspace
source ~/ros2_ws/install/setup.bash

# Check if package is built
ros2 pkg list | grep piper_kinematics
```

### Error: "Executable not found"

**Solution:**
```bash
# Rebuild the package
cd ~/ros2_ws
colcon build --packages-select piper_kinematics
source ~/ros2_ws/install/setup.bash
```

## What's Working

✅ Python script converted to ROS2  
✅ Package structure updated  
✅ Launch file converted  

## What's Not Working Yet

⚠️ C++ nodes need ROS2 conversion  
⚠️ piper_msgs dependency needs conversion  
⚠️ Interactive markers may need verification in ROS2 Jazzy  

## Next Steps

1. Test the Python node
2. Convert C++ nodes if needed
3. Convert piper_msgs if needed
4. Test with RViz2
