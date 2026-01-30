# How to Run Cube and Line Detection

## 🚀 Quick Start (Easiest Way)

**If you're not sure what's running, use this interactive script:**

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet
bash check_and_run.sh
```

This script will:
- ✅ Check if ROS 2 is set up
- ✅ Check if the package is built
- ✅ Check if camera is running
- ✅ Let you choose what to start (cube detection, line detection, or camera)

**Or if you just want to start detection directly:**

```bash
# In one terminal - start camera (if not running):
source /opt/ros/jazzy/setup.bash
ros2 launch realsense2_camera rs_launch.py

# In another terminal - start detection:
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run cubeAndLineDet cube_det    # for cubes
# OR
ros2 run cubeAndLineDet line_det    # for lines
```

---

## ⚠️ Important Note

The README.md shows ROS 1 commands (`roslaunch`, `rosrun`), but this package is built for **ROS 2**. Use the commands below instead.

## Prerequisites

### 1. Build the Package (First Time Only)

If you haven't built the package yet:

```bash
# Create workspace (if needed)
mkdir -p ~/ros2_ws/src

# Copy package to workspace (if not already there)
cp -r ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet ~/ros2_ws/src/

# Source ROS 2
source /opt/ros/jazzy/setup.bash

# Install dependencies (if needed)
sudo apt install -y \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-visualization-msgs \
    ros-jazzy-pcl-conversions \
    libopencv-dev \
    libpcl-dev \
    libeigen3-dev

# Build the package
cd ~/ros2_ws
colcon build --packages-select cubeAndLineDet

# Source the workspace
source ~/ros2_ws/install/setup.bash
```

### 2. Install Camera Driver

For **RealSense D435**:
```bash
sudo apt install -y ros-jazzy-realsense2-camera
```

For **Orbbec Petrel** (Astra):
```bash
# Install from source or use appropriate ROS 2 driver
# Check: https://github.com/orbbec/ros_astra_camera
```

## Running the Code

### Option 1: Quick Start Script (Easiest)

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI
bash start_camera_and_cube_det.sh
```

This script will:
- Start the RealSense camera automatically
- Wait for camera to initialize
- Launch cube detection
- Handle cleanup on exit

### Option 2: Manual Run (Two Terminals)

#### Terminal 1: Start Camera Driver

**For RealSense D435:**
```bash
source /opt/ros/jazzy/setup.bash
ros2 launch realsense2_camera rs_launch.py
```

**For Orbbec Petrel (if ROS 2 driver available):**
```bash
source /opt/ros/jazzy/setup.bash
ros2 launch astra_camera dabai_dc1.launch.py
```

#### Terminal 2: Run Detection Node

**For Cube Detection:**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Default topics (adjust if your camera uses different topics)
ros2 run cubeAndLineDet cube_det
```

**For Line Detection:**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 run cubeAndLineDet line_det
```

**If your camera topics are different**, specify them explicitly:
```bash
ros2 run cubeAndLineDet cube_det \
    --ros-args \
    -p image_topic_name:=/camera/camera/color/image_raw \
    -p camera_info_topic_name:=/camera/camera/color/camera_info \
    -p depth_topic_name:=/camera/camera/depth/image_rect_raw
```

## How to Use

### Cube Detection (`cube_det`)

1. **Three OpenCV windows** will appear:
   - `origin_img`: Original camera feed
   - `hsv_image`: HSV color space visualization
   - `depth_image`: Depth visualization

2. **Click on colored objects** in the `origin_img` window to:
   - Automatically detect the color
   - Adjust HSV thresholds
   - Calculate 3D coordinates

3. **The detected cube** will be highlighted with a bounding box

4. **3D coordinates** are published to ROS 2 topics:
   - `/cube_coordinates`: MarkerArray with cube positions

### Line Detection (`line_det`)

1. **Three OpenCV windows** will appear:
   - `origin_img`: Original camera feed
   - `hsv_image`: HSV color space visualization  
   - `depth_image`: Depth visualization

2. **Click on colored lines** in the `origin_img` window to:
   - Detect the line color
   - Extract 3D point cloud of the line
   - Visualize the detected line

3. **3D point cloud** is published for visualization

## Verify It's Working

```bash
# Check nodes are running
ros2 node list | grep -E "(cube|line)"

# Check topics
ros2 topic list | grep -E "(cube|line|camera)"

# View cube coordinates (in another terminal)
ros2 topic echo /cube_coordinates
```

## Troubleshooting

### Package Not Found
```bash
# Make sure workspace is sourced
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Verify package exists
ros2 pkg list | grep cubeAndLineDet
```

### Camera Topics Not Found
```bash
# Check available topics
ros2 topic list | grep camera

# Common RealSense topics:
# /camera/camera/color/image_raw
# /camera/camera/depth/image_rect_raw
# /camera/camera/color/camera_info
```

### No Images Showing
- Make sure camera driver is running in Terminal 1
- Check camera is connected: `lsusb | grep -i "intel\|orbbec"`
- Verify topics exist: `ros2 topic echo /camera/camera/color/image_raw --once`

### Build Errors
```bash
# Deactivate virtual environment if active
deactivate

# Clean and rebuild
cd ~/ros2_ws
rm -rf build install log
colcon build --packages-select cubeAndLineDet
```

## Stop the Nodes

Press `Ctrl+C` in the terminal, or:

```bash
# Stop cube detection
pkill -f cube_det

# Stop line detection  
pkill -f line_det

# Stop camera
pkill -f realsense2_camera
```

## Additional Resources

- See `BUILD_AND_RUN_ROS2.md` in the project root for detailed build instructions
- See `QUICK_START_CUBE_DET.md` for more examples
- Check `HOW_TO_RUN.md` in the project root for alternative methods
