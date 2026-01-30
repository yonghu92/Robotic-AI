# Test Depth Camera - Jupyter Notebook Guide

## Quick Start

1. **Start the camera** (in a terminal):
   ```bash
   source /opt/ros/jazzy/setup.bash
   ros2 launch realsense2_camera rs_launch.py
   ```

2. **Open the notebook**:
   ```bash
   cd ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet
   jupyter notebook test_depth_view.ipynb
   ```

3. **Run the cells** in order (Shift+Enter)

## What the Notebook Does

The notebook contains several test cells:

### Cell 1: Imports
- Imports all required libraries (rclpy, OpenCV, matplotlib, etc.)

### Cell 2: Initialize ROS 2
- Initializes ROS 2 connection

### Cell 3: DepthViewer Class
- Creates a ROS 2 node that subscribes to depth and color topics
- Converts ROS messages to OpenCV images
- Provides visualization functions

### Cell 4: Test Depth Reception
- Waits up to 10 seconds for depth data
- Shows if depth data is being received

### Cell 5: Display Depth Image
- Shows 3 views:
  - Raw depth image (grayscale)
  - Colorized depth (JET colormap - blue=far, red=close)
  - Depth distribution histogram
- Prints depth statistics

### Cell 6: Side-by-Side View
- Shows color image, depth visualization, and overlay together

## Troubleshooting

**If depth data is not received:**
1. Check camera is running: `ros2 node list | grep camera`
2. Check topics: `ros2 topic list | grep depth`
3. Verify topic name matches: `/camera/camera/depth/image_rect_raw`

**If you get import errors:**
```bash
pip install rclpy opencv-python numpy matplotlib
```

**If ROS 2 is not found:**
Make sure ROS 2 is sourced in your environment or add to notebook:
```python
import os
os.system('source /opt/ros/jazzy/setup.bash')
```

## Expected Output

When working correctly, you should see:
- ✓ Depth image received! Shape: (480, 640)
- Three images displayed: raw depth, colorized depth, and histogram
- Depth statistics printed

This confirms the depth camera is working and can be visualized!
