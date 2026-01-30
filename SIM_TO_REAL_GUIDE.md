# Sim-to-Real Interactive Marker Control Guide

Control the physical Piper arm by dragging an interactive marker in RViz2.

## Architecture

```
┌─────────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Interactive Marker │────▶│   IK Node       │────▶│  /joint_states  │
│  (drag in RViz2)    │     │ (computes IK)   │     │                 │
└─────────────────────┘     └─────────────────┘     └────────┬────────┘
        publishes                                            │
      /target_pose                              ┌────────────┴────────────┐
                                                ▼                         ▼
                                    ┌─────────────────┐      ┌────────────────────┐
                                    │ robot_state_pub │      │ sim_to_real_bridge │
                                    │ (RViz2 visual)  │      │ (physical arm)     │
                                    └─────────────────┘      └────────────────────┘
```

## Quick Start

### Step 1: Set up CAN Connection

Power on the arm first, then run:

```bash
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can0 txqueuelen 1000
```

Verify arm is communicating (should see scrolling data):

```bash
candump can0
# Press Ctrl+C once you see data
```

### Step 2: Start All Nodes

```bash
cd "/home/robotics_urop/Documents/Robotic AI/Robotic-AI"

# Terminal 1: Robot state publisher
ros2 launch piper_kinematics display_robot.launch.py &

# Terminal 2: RViz2
rviz2 &

# Terminal 3: Interactive marker
python3 piper/piper_kinematics/scripts/interactive_pose_marker.py &

# Terminal 4: IK node
python3 piper/piper_kinematics/scripts/piper_ik_node.py &

# Terminal 5: Sim-to-real bridge (connects to physical arm)
python3 sim_to_real_bridge.py
```

### Step 3: Configure RViz2

1. Set **Fixed Frame** (top left) to `base_link`
2. Click **Add** → Select **RobotModel** → Click OK
3. Click **Add** → Go to **By topic** tab → Expand `/interactive_marker` → Select **InteractiveMarkers** → Click OK

### Step 4: Control the Arm

- Drag the interactive marker (colored arrows/rings) in RViz2
- Both the simulated and physical arm will follow
- Speed is set to 30% by default (safe for testing)

## One-Liner Start (After CAN is Set Up)

```bash
cd "/home/robotics_urop/Documents/Robotic AI/Robotic-AI" && \
ros2 launch piper_kinematics display_robot.launch.py & \
sleep 2 && rviz2 & \
sleep 3 && python3 piper/piper_kinematics/scripts/interactive_pose_marker.py & \
sleep 2 && python3 piper/piper_kinematics/scripts/piper_ik_node.py & \
sleep 2 && python3 sim_to_real_bridge.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| CAN "No buffer space" errors | Reset CAN: `sudo ip link set can0 down && sudo ip link set can0 up type can bitrate 1000000` |
| `candump can0` shows nothing | Power cycle the arm, unplug/replug USB-CAN adapter, then reset CAN |
| Arm not following marker | Check `ros2 node list` - make sure `piper_ik_node` is running |
| IK not converging | Move marker closer to arm's current position (stay within reachable workspace) |
| Marker not visible in RViz2 | Re-add InteractiveMarkers display: Remove old one, Add → By topic → /interactive_marker |
| Physical arm not moving | Check if `sim_to_real_bridge` is running and arm is enabled |

## Files Involved

| File | Purpose |
|------|---------|
| `sim_to_real_bridge.py` | Bridges ROS2 joint states to physical arm via CAN |
| `piper/piper_kinematics/scripts/piper_ik_node.py` | Computes inverse kinematics from target pose |
| `piper/piper_kinematics/scripts/interactive_pose_marker.py` | Creates draggable 6-DOF marker in RViz2 |
| `piper/piper_kinematics/launch/display_robot.launch.py` | Launches robot state publisher with URDF |
| `piper/gamepad/piper/piper.urdf` | Robot description file |

## Parameters

### sim_to_real_bridge.py

- `can_interface`: CAN interface name (default: `can0`)
- `speed_percent`: Movement speed 1-100% (default: `30`)
- `enable_on_start`: Auto-enable arm motors (default: `True`)

### piper_ik_node.py

- `max_iterations`: IK solver iterations (default: `200`)
- `position_tolerance`: Position accuracy in meters (default: `0.005`)
- `orientation_tolerance`: Orientation accuracy in radians (default: `0.1`)
- `damping`: Damped least squares factor (default: `0.5`)

## Stopping Everything

```bash
# Kill all related processes
pkill -f interactive_pose_marker
pkill -f piper_ik_node
pkill -f sim_to_real_bridge
pkill -f rviz2
pkill -f robot_state_publisher
```

## Notes

- Always ensure the arm has clearance to move before starting
- The IK solver uses a Jacobian-based method which works best when the target is close to the current position
- If the arm shakes, there may be multiple nodes publishing to `/joint_states` - kill duplicates
- The grey box in RViz2 is the gripper (simplified collision geometry)
