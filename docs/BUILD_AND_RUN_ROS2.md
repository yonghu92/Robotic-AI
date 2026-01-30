# How to Build and Run Cube/Line Detection in ROS 2

## Prerequisites

1. **Install missing Python package** (if not already installed):
```bash
sudo apt install -y python3-catkin-pkg
```

2. **Deactivate virtual environment** (if active):
```bash
deactivate
```

## Step-by-Step Instructions

### 1. Create ROS 2 Workspace (if not exists)

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
```

### 2. Copy Package to Workspace

```bash
cp -r ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet ~/ros2_ws/src/
```

### 3. Fix Package.xml (if needed)

The package.xml should have `<name>` not `<n>`. Fix it:
```bash
sed -i 's/<n>/<name>/g; s/<\/n>/<\/name>/g' ~/ros2_ws/src/cubeAndLineDet/package.xml
```

### 4. Source ROS 2

```bash
source /opt/ros/jazzy/setup.bash
```

### 5. Install Dependencies

```bash
# Install ROS 2 packages
sudo apt install -y \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-visualization-msgs \
    ros-jazzy-pcl-conversions

# Install system dependencies
sudo apt install -y \
    libopencv-dev \
    libpcl-dev \
    libeigen3-dev
```

### 6. Build the Package

```bash
cd ~/ros2_ws
colcon build --packages-select cubeAndLineDet
```

If you get Python/venv errors, make sure to:
- Deactivate any virtual environment: `deactivate`
- Use system Python: `unset PYTHONPATH` (temporarily)

### 7. Source the Workspace

```bash
source ~/ros2_ws/install/setup.bash
```

### 8. Run the Nodes

**For cube detection:**
```bash
ros2 run cubeAndLineDet cube_det
```

**For line detection:**
```bash
ros2 run cubeAndLineDet line_det
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'catkin_pkg'"

**Solution:**
```bash
# Install the package
sudo apt install -y python3-catkin-pkg

# Or install via pip (if using system Python)
pip3 install catkin_pkg
```

### Issue: Virtual environment interfering

**Solution:**
```bash
# Deactivate venv
deactivate

# Or unset PYTHONPATH temporarily
unset PYTHONPATH
colcon build --packages-select cubeAndLineDet
```

### Issue: Camera topics not found

**Solution:**
Make sure your RealSense camera driver is running:
```bash
# For RealSense (ROS 2)
ros2 launch realsense2_camera rs_launch.py
```

Then check available topics:
```bash
ros2 topic list
```

You should see topics like:
- `/camera/color/image_raw`
- `/camera/depth/image_raw`
- `/camera/color/camera_info`

### Issue: Package not found after build

**Solution:**
```bash
# Make sure you source both ROS 2 and your workspace
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Verify package is found
ros2 pkg list | grep cubeAndLineDet
```

## Quick Start Script

Create a file `build_and_run.sh`:

```bash
#!/bin/bash
# Build and run cube/line detection

# Deactivate venv if active
deactivate 2>/dev/null

# Source ROS 2
source /opt/ros/jazzy/setup.bash

# Build
cd ~/ros2_ws
colcon build --packages-select cubeAndLineDet

# Source workspace
source install/setup.bash

# Run (choose one)
# ros2 run cubeAndLineDet cube_det
# ros2 run cubeAndLineDet line_det
```

Make it executable:
```bash
chmod +x build_and_run.sh
./build_and_run.sh
```
