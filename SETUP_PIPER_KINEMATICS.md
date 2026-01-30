# Setting Up Piper Kinematics (ROS1 Package)

## Problem
You're trying to run a **ROS1 (Noetic)** package, but you only have **ROS2 (Jazzy)** installed.

## Important Note

**You might not need this ROS package!** 

Your `pick_and_place.py` script uses the **piper_sdk** directly and doesn't need ROS. The `piper_kinematics` ROS package is only needed if you want to:
- Use RViz for visualization
- Integrate with other ROS nodes
- Use ROS-based planning/control

---

## Option 1: Install ROS1 Noetic (Recommended if you need ROS)

**Note:** ROS1 Noetic is designed for Ubuntu 20.04, but can work on Ubuntu 24.04 with some compatibility issues.

### Step 1: Install ROS1 Noetic

```bash
# Add ROS repository
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'

# Add GPG key
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# Update
sudo apt update

# Install ROS Noetic
sudo apt install -y ros-noetic-desktop-full

# Install catkin tools
sudo apt install -y python3-catkin-tools python3-osrf-pycommon python3-catkin-pkg

# Install dependencies for piper_kinematics
sudo apt install -y \
    ros-noetic-sensor-msgs \
    ros-noetic-geometry-msgs \
    ros-noetic-visualization-msgs \
    ros-noetic-tf \
    ros-noetic-eigen-conversions \
    libeigen3-dev
```

### Step 2: Source ROS1

```bash
# Add to ~/.bashrc (or source manually)
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Create Catkin Workspace

```bash
# Create workspace
mkdir -p ~/piper_kinematics_ws/src
cd ~/piper_kinematics_ws/src

# Initialize workspace
catkin_init_workspace

# Copy package
cp -r ~/Documents/Robotic\ AI/Robotic-AI/piper/piper_kinematics ~/piper_kinematics_ws/src/

# Go back to workspace root
cd ~/piper_kinematics_ws
```

### Step 4: Build the Package

```bash
# Make sure ROS1 is sourced (NOT ROS2!)
source /opt/ros/noetic/setup.bash

# Build
catkin_make

# Source the workspace
source devel/setup.bash
```

### Step 5: Run the Package

```bash
# Make sure you're NOT in venv and ROS1 is sourced
deactivate  # if venv is active
source /opt/ros/noetic/setup.bash
source ~/piper_kinematics_ws/devel/setup.bash

# Run the interactive marker script
rosrun piper_kinematics interactive_pose_marker.py

# Or use the launch file
roslaunch piper_kinematics piper_ik.launch
```

---

## Option 2: Use Your Existing pick_and_place.py (No ROS Needed!)

**This is the easier option** - you already have a working solution!

Your `pick_and_place.py` script:
- ✅ Uses piper_sdk directly (no ROS needed)
- ✅ Has object detection
- ✅ Has pick and place logic
- ✅ Works in simulation mode

Just fix the CAN connection and you're good to go!

```bash
# Just run your existing script
python3 pick_and_place.py
```

---

## Option 3: Convert to ROS2 (Advanced)

If you really need ROS but want to use ROS2, you'd need to convert the package:
- Change `rospy` → `rclpy`
- Change `catkin` → `colcon`
- Update message types
- Update launch files

This is a lot of work and probably not worth it unless you specifically need ROS2 integration.

---

## Quick Fix for Your Current Error

If you just want to test the kinematics without ROS, you can't - this package is **designed for ROS**. 

But you can use the **pick_and_place.py** script instead, which doesn't need ROS!

---

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'rospy'"

**Cause:** Running ROS1 package without ROS1 environment

**Solution:**
1. Install ROS1 Noetic (see Option 1)
2. OR use `pick_and_place.py` instead (Option 2)

### Error: "catkin_make: command not found"

**Solution:**
```bash
sudo apt install -y python3-catkin-tools python3-osrf-pycommon
```

### Error: Virtual environment interfering

**Solution:**
```bash
# Deactivate venv before running ROS
deactivate

# Then source ROS
source /opt/ros/noetic/setup.bash
source ~/piper_kinematics_ws/devel/setup.bash
```

### ROS1 and ROS2 Conflict

If you have both ROS1 and ROS2 installed:
- Make sure to source the correct one
- ROS1: `source /opt/ros/noetic/setup.bash`
- ROS2: `source /opt/ros/jazzy/setup.bash`
- Don't source both at the same time!

---

## Recommendation

**For your use case (pick and place), I recommend Option 2** - just use `pick_and_place.py` which doesn't need ROS at all!

The ROS kinematics package is mainly useful for:
- RViz visualization
- ROS-based motion planning
- Integration with other ROS nodes

If you don't need those features, stick with the SDK-based approach.
