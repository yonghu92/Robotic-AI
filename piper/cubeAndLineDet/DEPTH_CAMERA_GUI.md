# Depth Camera GUI Viewer Setup

There are multiple ways to view the depth camera GUI. Choose the one that works best for you.

## Option 1: RealSense Viewer (Official Intel Tool) - Easiest

The official RealSense viewer provides the best GUI with all camera controls.

### Start RealSense Viewer:

```bash
realsense-viewer
```

**Features:**
- Full camera control (resolution, FPS, filters)
- Real-time depth visualization
- Color and depth streams side-by-side
- Point cloud visualization
- Camera settings and calibration
- Record/playback functionality

**Note:** This tool connects directly to the camera hardware, so make sure no other programs are using the camera.

---

## Option 2: Custom Python GUI (Recommended for ROS 2)

A custom GUI that works with ROS 2 topics - perfect if you're already using ROS 2.

### Quick Start:

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet
bash start_depth_gui.sh
```

### Manual Start:

**Terminal 1 - Start Camera:**
```bash
source /opt/ros/jazzy/setup.bash
ros2 launch realsense2_camera rs_launch.py
```

**Terminal 2 - Start GUI:**
```bash
cd ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet
source /opt/ros/jazzy/setup.bash
python3 depth_camera_gui.py
```

**Features:**
- Side-by-side color and depth visualization
- Adjustable depth range (min/max sliders)
- Multiple colormap options (JET, HOT, COOL, RAINBOW, etc.)
- Real-time depth statistics
- Works with ROS 2 topics
- Can run alongside cube detection

---

## Option 3: Simple OpenCV Viewer (Lightweight)

The simplest option - just shows depth in OpenCV windows.

### Start:

```bash
cd ~/Documents/Robotic\ AI/Robotic-AI/piper/cubeAndLineDet
source /opt/ros/jazzy/setup.bash
python3 test_depth_view.py
```

**Features:**
- Lightweight and fast
- Shows color, depth, and overlay
- Press 'q' to quit

---

## Option 4: Use Cube Detection (Already Has Depth Window)

The cube detection already shows depth! Just make sure the depth window is visible.

```bash
# Terminal 1
source /opt/ros/jazzy/setup.bash
ros2 launch realsense2_camera rs_launch.py

# Terminal 2
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run cubeAndLineDet cube_det
```

You should see three windows including `depth_image` showing the depth visualization.

---

## Troubleshooting

### GUI doesn't open?
- Make sure you have X11/display forwarding if using SSH
- Check: `echo $DISPLAY` (should show a display)

### Camera busy?
- Stop other camera processes: `pkill -f realsense`
- Or use RealSense viewer which handles this automatically

### No depth data?
- Check camera is running: `ros2 node list | grep camera`
- Check topics: `ros2 topic list | grep depth`
- Verify topic name matches your camera setup

---

## Recommended Setup

**For best experience:**
1. Use **RealSense Viewer** (`realsense-viewer`) for camera setup and testing
2. Use **Custom Python GUI** for ROS 2 integration and development
3. Use **Cube Detection** for actual object detection tasks

All three can show the depth camera GUI - choose based on your needs!
