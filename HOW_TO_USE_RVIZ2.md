# How to Use RViz2 with Interactive Markers

## What is RViz2?

RViz2 is the **visualization tool** for ROS2. It's like a 3D viewer where you can:
- See your robot model
- See sensor data (cameras, point clouds, etc.)
- **Interact with markers** (drag, rotate, move objects)
- Visualize topics and transforms

## Opening RViz2

### Basic Command:
```bash
rviz2
```

### With ROS2 Environment:
```bash
# Make sure ROS2 is sourced
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Open RViz2
rviz2
```

## Setting Up RViz2 for Interactive Markers

### Step 1: Open RViz2
```bash
rviz2
```

### Step 2: Add Interactive Markers Display

1. Click **"Add"** button (bottom left)
2. Select **"InteractiveMarkers"** from the list
3. Click **"OK"**

### Step 3: Configure the Display

In the InteractiveMarkers display settings:
- **Update Topic**: Should auto-detect `/interactive_marker/update`
- **Description Topic**: Should auto-detect `/interactive_marker/feedback`

### Step 4: Set Fixed Frame

1. In the left panel, find **"Global Options"**
2. Set **"Fixed Frame"** to `base_link` (or whatever frame your marker uses)

### Step 5: Interact with the Marker

Once the marker appears:
- **Drag the arrows** to move along X, Y, or Z axis
- **Drag the circles** to rotate around X, Y, or Z axis
- The marker should move in real-time
- Your node will publish updates to `/target_pose` topic

## Troubleshooting

### Marker Not Appearing?

1. **Check if node is running:**
   ```bash
   ros2 node list
   # Should show: /interactive_pose_marker
   ```

2. **Check topics:**
   ```bash
   ros2 topic list | grep interactive
   # Should show interactive marker topics
   ```

3. **Check Fixed Frame:**
   - Make sure Fixed Frame matches your marker's frame (usually `base_link`)

4. **Check TF:**
   ```bash
   ros2 run tf2_ros tf2_echo base_link target_pose
   ```

### RViz2 Not Opening?

```bash
# Install if missing
sudo apt install -y ros-jazzy-rviz2

# Or install full desktop
sudo apt install -y ros-jazzy-desktop
```

### No Display Available?

If you're using SSH:
```bash
# Enable X11 forwarding
ssh -X username@hostname

# Or set display
export DISPLAY=:0
```

## Quick Test

1. **Terminal 1:** Run your node
   ```bash
   ros2 run piper_kinematics interactive_pose_marker.py
   ```

2. **Terminal 2:** Open RViz2
   ```bash
   rviz2
   ```

3. **In RViz2:**
   - Add InteractiveMarkers display
   - Set Fixed Frame to `base_link`
   - You should see a marker you can drag/rotate!

4. **Terminal 3 (optional):** Watch the pose updates
   ```bash
   ros2 topic echo /target_pose
   ```

## What You Should See

- A **3D marker** (usually a box or sphere with arrows/circles)
- **6 arrows** for translation (X, Y, Z movement)
- **6 circles** for rotation (X, Y, Z rotation)
- When you drag/rotate, the marker moves and your node publishes the new pose

## Saving Your Configuration

Once set up:
1. Go to **File → Save Config As...**
2. Save as `~/.rviz2/interactive_marker.rviz`
3. Next time: `rviz2 -d ~/.rviz2/interactive_marker.rviz`
