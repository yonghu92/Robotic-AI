# How to Complete ROS 2 Setup Todos

## Current Status
- ☒ Check available ROS2 topics for camera (DONE)
- ☐ Install RealSense ROS2 wrapper
- ☐ Install missing ROS2 dependencies (needs sudo)
- ☐ Build ROS2 workspace
- ☐ Run cube_det node

## Quick Solution: Run the Setup Script

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI
bash complete_ros2_setup.sh
```

This script will automatically complete todos 2-4. Then follow the instructions for todo 5.

---

## Manual Step-by-Step Guide

### TODO 2: Install RealSense ROS2 Wrapper

**Option A: Install via apt (Easiest)**
```bash
sudo apt update
sudo apt install -y ros-jazzy-realsense2-camera
```

**Option B: Build from source (if apt doesn't work)**
```bash
cd ~/ros2_ws/src
# If you already cloned it, skip this:
# git clone https://github.com/IntelRealSense/realsense-ros.git -b ros2-development

cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select realsense2_camera
source install/setup.bash
```

### TODO 3: Install Missing ROS2 Dependencies

```bash
# ROS 2 packages
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

# System dependencies
sudo apt install -y \
    libopencv-dev \
    libpcl-dev \
    libeigen3-dev \
    python3-catkin-pkg
```

### TODO 4: Build ROS2 Workspace

```bash
cd ~/ros2_ws

# Deactivate any virtual environment
deactivate 2>/dev/null || true

# Source ROS 2
source /opt/ros/jazzy/setup.bash

# Build the package
colcon build --packages-select cubeAndLineDet

# If you also need to build RealSense:
# colcon build --packages-select realsense2_camera

# Source the workspace
source install/setup.bash

# Verify it worked
ros2 pkg list | grep cubeAndLineDet
```

### TODO 5: Run cube_det Node

**Step 1: Start RealSense Camera (Terminal 1)**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# If RealSense is installed via apt:
ros2 launch realsense2_camera rs_launch.py

# OR if built from source:
ros2 run realsense2_camera realsense2_camera_node
```

**Step 2: Run Cube Detection (Terminal 2)**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run cubeAndLineDet cube_det
```

**Step 3: Verify Topics**
```bash
# In a third terminal, check topics:
ros2 topic list
# You should see:
# - /camera/color/image_raw
# - /camera/depth/image_raw
# - /cube_markers (from cube_det)
```

---

## Troubleshooting

### Issue: "Package 'realsense2_camera' not found"
**Solution:** Build from source (see TODO 2, Option B)

### Issue: Build fails with Python errors
**Solution:**
```bash
deactivate  # Exit virtual environment
unset PYTHONPATH
colcon build --packages-select cubeAndLineDet
```

### Issue: "No topics available"
**Solution:** Make sure RealSense camera is:
1. Connected via USB
2. Not busy (run: `bash force_reset_camera.sh`)
3. Driver is running (Terminal 1)

### Issue: Camera topics have different names
**Solution:** Check actual topic names:
```bash
ros2 topic list
```
Then update the topic names in `cube_det.cpp` if needed.

---

## Quick Test Script

Create `~/ros2_ws/test_setup.sh`:
```bash
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

echo "Checking ROS 2 setup..."
echo "Packages:"
ros2 pkg list | grep -E "(cubeAndLineDet|realsense)"

echo ""
echo "Topics:"
ros2 topic list | head -10

echo ""
echo "To run cube detection:"
echo "  Terminal 1: ros2 launch realsense2_camera rs_launch.py"
echo "  Terminal 2: ros2 run cubeAndLineDet cube_det"
```

Make it executable:
```bash
chmod +x ~/ros2_ws/test_setup.sh
~/ros2_ws/test_setup.sh
```
