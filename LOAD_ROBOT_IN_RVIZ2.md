# How to Load Robot Model in RViz2

## The Problem

The command-line approach failed because URDF XML contains special characters that break shell parsing.

## Solution: Use a Launch File

I've created a launch file for you. Here's how to use it:

### Step 1: Copy Launch File to Workspace (if not already there)

```bash
cp ~/Documents/Robotic\ AI/Robotic-AI/piper/piper_kinematics/launch/display_robot.launch.py \
   ~/ros2_ws/src/piper_kinematics/launch/
```

### Step 2: Rebuild Package

```bash
cd ~/ros2_ws
colcon build --packages-select piper_kinematics
source install/setup.bash
```

### Step 3: Run Robot State Publisher

```bash
# In a new terminal
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Launch robot state publisher
ros2 launch piper_kinematics display_robot.launch.py
```

### Step 4: In RViz2

1. Add "RobotModel" display
2. You should now see the robot arm!

## Alternative: Simple Python Script

If the launch file doesn't work, use this simple script:

```bash
# Create a simple script
cat > /tmp/load_robot.py << 'EOF'
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from robot_state_publisher import RobotStatePublisher
import os

urdf_path = os.path.expanduser('~/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf')
with open(urdf_path, 'r') as f:
    robot_description = f.read()

rclpy.init()
node = Node('robot_state_publisher')
publisher = RobotStatePublisher(node, robot_description)
rclpy.spin(node)
EOF

chmod +x /tmp/load_robot.py
python3 /tmp/load_robot.py
```

## What You Should See

After running robot_state_publisher:
- In RViz2, add "RobotModel" display
- You'll see the Piper robot arm model
- You can also see the interactive marker
- The robot will be in its default/home position

## Full Setup (3 Terminals)

**Terminal 1:** Interactive Marker
```bash
ros2 run piper_kinematics interactive_pose_marker.py
```

**Terminal 2:** Robot State Publisher
```bash
ros2 launch piper_kinematics display_robot.launch.py
```

**Terminal 3:** RViz2
```bash
rviz2
```

In RViz2:
- Add "InteractiveMarkers" display (to see draggable marker)
- Add "RobotModel" display (to see robot arm)
- Set Fixed Frame: `base_link`

## Troubleshooting

### Error: "robot_description parameter not set"

Make sure robot_state_publisher is running and the launch file found the URDF.

### Robot not visible

- Check Fixed Frame is set to `base_link` or `base_footprint`
- Check "RobotModel" display is added
- Check robot_state_publisher is running: `ros2 node list`

### URDF file not found

Update the path in `display_robot.launch.py` to point to your URDF file.
