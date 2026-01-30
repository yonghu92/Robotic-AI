# How to Run Cube and Line Detection

## ✅ Package is Built and Ready!

The package has been successfully built in `~/ros2_ws`.

## Quick Start

### Option 1: Use the Run Script

```bash
cd ~/ros2_ws
./run_cube_detection.sh
```

Then choose:
- **1** for cube detection
- **2** for line detection

### Option 2: Run Directly

**Step 1: Open a terminal and source everything:**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
source ~/Documents/Robotic\ AI/Robotic-AI/venv/bin/activate
```

**Step 2: Start your RealSense camera (in a separate terminal):**
```bash
ros2 launch realsense2_camera rs_launch.py
```

**Step 3: Run the detection (in another terminal):**

For **cube detection**:
```bash
ros2 run cubeAndLineDet cube_det
```

For **line detection**:
```bash
ros2 run cubeAndLineDet line_det
```

## What You'll See

When you run the detection:
- **Two OpenCV windows** will open:
  - `origin_image` - The original camera feed
  - `hsv_image` - The processed image with detection

- **To use cube detection:**
  1. Click on a colored object in the `origin_image` window
  2. The HSV sliders will adjust automatically
  3. The detected cube will be highlighted in green
  4. 3D coordinates will be published to ROS topics

- **To use line detection:**
  1. Click on a colored line in the `origin_image` window
  2. The system will detect and track the line
  3. 3D point cloud of the line will be published

- **Press ESC** to exit

## Troubleshooting

**If you get "package not found":**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

**If camera topics not found:**
- Make sure RealSense camera driver is running
- Check topics: `ros2 topic list | grep camera`

**If windows don't open:**
- Make sure you have X11 forwarding enabled if using SSH
- Check display: `echo $DISPLAY`

## All-in-One Command

To run everything in one go (after camera is started):

```bash
source /opt/ros/jazzy/setup.bash && \
source ~/ros2_ws/install/setup.bash && \
source ~/Documents/Robotic\ AI/Robotic-AI/venv/bin/activate && \
ros2 run cubeAndLineDet cube_det
```
