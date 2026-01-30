# Quick Start: Cube Detection with RealSense

## ✅ Status: Working!

The cube detection node is now running with your RealSense camera.

## How to Use

### Option 1: Use the Script (Easiest)

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI
bash run_cube_det_venv.sh
```

### Option 2: Manual Run

**Terminal 1: Start Camera** (if not already running)
```bash
source /opt/ros/jazzy/setup.bash
ros2 launch realsense2_camera rs_launch.py
```

**Terminal 2: Run Cube Detection**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 run cubeAndLineDet cube_det \
    --ros-args \
    -p image_topic_name:=/camera/camera/color/image_raw \
    -p camera_info_topic_name:=/camera/camera/color/camera_info \
    -p depth_topic_name:=/camera/camera/depth/image_rect_raw
```

## What You'll See

1. **Two OpenCV Windows:**
   - `origin_image`: Original camera feed with detected cubes
   - `hsv_image`: HSV color space for tuning detection

2. **Interactive Controls:**
   - Click on objects in `origin_image` to auto-tune HSV values
   - Use trackbars in `hsv_image` to manually adjust:
     - `hmin/hmax`: Hue range
     - `smin/smax`: Saturation range
     - `vmin/vmax`: Value (brightness) range

3. **Published Topics:**
   - `/cube_coordinates`: MarkerArray with detected cube positions

## Verify It's Working

```bash
# Check node is running
ros2 node list | grep cube

# Check topics
ros2 topic list | grep cube

# View cube coordinates
ros2 topic echo /cube_coordinates
```

## Troubleshooting

### No images showing?
- Check camera is running: `ros2 topic list | grep camera`
- Verify topics: `ros2 topic echo /camera/camera/color/image_raw --once`

### Wrong topic names?
- Check actual topics: `ros2 topic list`
- Update the topic parameters in the command

### Node crashes?
- Make sure camera is running first
- Check ROS 2 is sourced: `echo $ROS_DISTRO` (should show "jazzy")

## Stop the Node

Press `Ctrl+C` in the terminal running the node, or:

```bash
pkill -f cube_det
```
