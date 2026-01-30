# Where the URDF File is Used

## Location in Launch File

**File:** `piper/piper_kinematics/launch/display_robot.launch.py` (or `piper_ik_with_robot.launch.py`)

### Step-by-Step URDF Usage:

#### 1. **URDF File Path Definition** (Lines 9-14)
```python
urdf_paths = [
    '~/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf',
    '~/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper_local.urdf',
    # ... more paths
]
```

#### 2. **Find URDF File** (Lines 16-25)
```python
urdf_path = None
for path in urdf_paths:
    if os.path.exists(path):
        urdf_path = path
        print(f"Using URDF: {urdf_path}")  # ← You saw this in terminal!
        break
```

#### 3. **Read URDF File** (Lines 28-33)
```python
with open(urdf_path, 'r') as f:
    robot_description = f.read()  # ← URDF content loaded here
```

#### 4. **Pass to robot_state_publisher** (Lines 36-44)
```python
robot_state_publisher = Node(
    package='robot_state_publisher',
    executable='robot_state_publisher',
    parameters=[{
        'robot_description': robot_description,  # ← URDF passed here!
    }]
)
```

## How It Works:

1. **Launch file reads URDF** → Loads XML content
2. **Passes to robot_state_publisher** → As `robot_description` parameter
3. **robot_state_publisher publishes** → To `/robot_description` topic
4. **RViz2 subscribes** → Reads from `/robot_description` topic
5. **RViz2 renders** → Shows robot model in 3D

## Verification:

### Check if URDF is loaded:
```bash
ros2 param get /robot_state_publisher robot_description | head -5
```
Should show: `<?xml version="1.0" encoding="utf-8"?>`

### Check if topic exists:
```bash
ros2 topic list | grep robot_description
```
Should show: `/robot_description`

### Check which URDF was used:
Look at launch output - you saw:
```
Using URDF: /home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf
```

## Why Robot Might Not Show:

The URDF **IS** being used (you saw "Using URDF: ..." in terminal), but:

1. **RViz2 Fixed Frame wrong** → Set to `base_link` or `base_footprint`
2. **RobotModel display not added** → Add it in RViz2
3. **No joint_states** → Robot might be in default pose (all joints at 0)
4. **TF not publishing** → robot_state_publisher needs joint_states to publish TF

## To See Robot Move:

The robot needs `/joint_states` topic to show different poses. Currently it's probably in default/home position (all joints at 0).

To publish joint states (for testing):
```bash
# This would need the IK solver node running, or manually publish joint states
```
