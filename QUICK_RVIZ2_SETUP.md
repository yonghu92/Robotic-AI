# Quick RViz2 Setup for Robot Visualization

## Launch RViz2

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
rviz2
```

## Once RViz2 Opens - Do These Steps:

### Step 1: Set Fixed Frame (CRITICAL!)
1. In left panel, find **"Global Options"**
2. Click on **"Fixed Frame"** dropdown
3. Select: **`base_link`** (or try `base_footprint` if that doesn't work)

### Step 2: Add RobotModel Display
1. Click **"Add"** button (bottom left)
2. Select **"RobotModel"** from the list
3. Click **"OK"**
4. **Make sure checkbox is checked** ✓

### Step 3: Add InteractiveMarkers Display (if you want the marker)
1. Click **"Add"** button again
2. Select **"InteractiveMarkers"**
3. Click **"OK"**
4. **Make sure checkbox is checked** ✓

## What You Should See:

- **Robot arm model** (all links and joints)
- **Interactive marker** (if added) - draggable object with arrows/circles
- Robot in default/home position

## If Robot Still Doesn't Show:

### Check 1: Verify robot_state_publisher is running
```bash
ros2 node list | grep robot_state_publisher
```
Should show: `/robot_state_publisher`

### Check 2: Verify robot_description exists
```bash
ros2 topic list | grep robot_description
```
Should show: `/robot_description`

### Check 3: Try different Fixed Frame
- `base_link`
- `base_footprint`  
- `world`

### Check 4: Check TF frames
```bash
ros2 run tf2_tools view_frames
```
Opens frames.pdf showing available frames

## Quick Launch Script

Save this as `launch_rviz2.sh`:
```bash
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
rviz2
```

Make it executable:
```bash
chmod +x launch_rviz2.sh
./launch_rviz2.sh
```
