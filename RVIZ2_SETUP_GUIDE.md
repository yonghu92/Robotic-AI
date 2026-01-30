# RViz2 Setup Guide for Interactive Marker

## Current Situation

You're running `interactive_pose_marker.py` which:
- ✅ Creates an interactive marker
- ✅ Publishes to `/target_pose` topic
- ❌ Does NOT show the robot arm
- ❌ Does NOT control the actual arm

## Step 1: See the Interactive Marker

### In RViz2:

1. **Add InteractiveMarkers Display:**
   - Click "Add" button (bottom left)
   - Select "InteractiveMarkers"
   - Click "OK"

2. **Set Fixed Frame:**
   - In left panel, find "Global Options"
   - Set "Fixed Frame" to `base_link`

3. **You should now see:**
   - A 3D marker (box/sphere) with arrows and circles
   - You can drag/rotate it

### If you still see blank:

```bash
# Check if marker is being published
ros2 topic list | grep interactive
ros2 topic echo /target_pose
```

## Step 2: See the Robot Arm (Optional)

To see the actual robot model, you need to publish the robot description:

### Option A: Use robot_state_publisher (if you have a URDF package)

```bash
# In a new terminal
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$(cat ~/path/to/piper.urdf)"
```

Then in RViz2:
- Add "RobotModel" display
- You'll see the robot arm

### Option B: Load URDF directly in RViz2

1. In RViz2, go to **File → Open Config**
2. Or manually add "RobotModel" display
3. Set "Robot Description" parameter to the URDF file path

## Step 3: Full Workflow (What You Want)

To have the complete system where:
- You drag marker in RViz2
- Robot arm moves in simulation
- (Eventually) Real arm moves

You need:

1. **Interactive Marker** (✅ You have this)
   ```bash
   ros2 run piper_kinematics interactive_pose_marker.py
   ```

2. **Robot Description Publisher** (❌ Missing)
   ```bash
   # Publish robot URDF
   ros2 run robot_state_publisher robot_state_publisher ...
   ```

3. **IK Solver Node** (❌ Not converted yet - C++ code)
   - Converts `/target_pose` → joint angles
   - Publishes to `/joint_states`

4. **Arm Control Node** (❌ Missing)
   - Reads joint angles
   - Sends commands to actual arm via CAN

## Quick Test: Just See the Marker

Right now, let's just get the marker visible:

1. **In RViz2:**
   - Add → InteractiveMarkers
   - Set Fixed Frame: `base_link`
   - You should see a draggable marker!

2. **Test it:**
   ```bash
   # In another terminal
   ros2 topic echo /target_pose
   # Drag the marker in RViz2, you should see pose updates
   ```

## Summary

- **Blank view** = Need to add InteractiveMarkers display
- **No robot** = Need robot description publisher
- **No arm control** = Need IK solver + arm control nodes
- **This node** = Just creates the marker, doesn't show robot

The marker is working, you just need to add the display in RViz2!
