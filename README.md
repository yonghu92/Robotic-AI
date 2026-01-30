# Piper Arm Robotics Project

A comprehensive robotics project featuring the Piper 6-DOF robotic arm with vision-guided manipulation, multiple control interfaces, and imitation learning capabilities.

---

## Project Highlights

| Feature | Description | Location |
|---------|-------------|----------|
| **Pick & Place** | Vision-guided object manipulation with depth camera | [`piper/manipulation/`](piper/manipulation/) |
| **Trajectory Recording** | Record and playback arm movements using teach mode | [`piper/recordAndPlayTraj/`](piper/recordAndPlayTraj/) |
| **Hand Gesture Control** | Arm mimics physical hand movements in real-time | [`piper/handpose_det/`](piper/handpose_det/) |
| **Gamepad Control** | Full arm control with Logitech gamepad | [`piper/gamepad/`](piper/gamepad/) |
| **RGI Rotating Gripper** | Integrated rotating gripper with open/close/rotate | [`rgi_gripper/`](rgi_gripper/) |
| **Web Remote Control** | Browser-based control with live camera feed | [`rgi_gripper/web_controller.py`](rgi_gripper/web_controller.py) |
| **Camera Calibration** | Hand-eye calibration for accurate positioning | [`piper/calibration/`](piper/calibration/) |
| **Imitation Learning** | LeRobot ACT policy training and deployment | Training data samples included |
| **ROS2 Integration** | URDF, RViz2, inverse kinematics solver | [`piper/piper_kinematics/`](piper/piper_kinematics/) |

---

## Demo

![Pick and Place Demo](training_data_samples/pick_and_place_demo.gif)

*Wrist camera view during pick-and-place task with red cube*

---

## Quick Start

### 1. Setup CAN Bus
```bash
sudo ip link set can0 up type can bitrate 1000000
```

### 2. Main Control (Trajectories + Gamepad + Gripper)
```bash
cd rgi_gripper
python3 play_and_adjust.py
```

### 3. Web Control Interface
```bash
cd rgi_gripper
python3 web_controller.py
# Open http://localhost:5000 in browser
```

### 4. Gamepad-Only Control
```bash
cd piper/gamepad
python3 gamepadecontrol.py
```

---

## Project Structure

```
├── rgi_gripper/                  # RGI Gripper + Main Control System
│   ├── play_and_adjust.py        # Trajectory record/play + gamepad + gripper
│   ├── web_controller.py         # Web interface with live camera
│   ├── rotation_arm_gamepad.py   # Combined arm + gripper gamepad control
│   └── saved_positions.json      # Saved trajectories
│
├── piper/
│   ├── manipulation/             # Pick and Place Scripts
│   │   ├── pick_and_place.py
│   │   ├── pick_and_place_calibrated.py
│   │   ├── object_detection_pick_place.py
│   │   ├── hand_to_arm_control.py
│   │   └── sim_to_real_bridge.py
│   │
│   ├── recordAndPlayTraj/        # Trajectory Recording & Playback
│   │   ├── recordTrajectory_new_en.py
│   │   └── playTrajectory_new_en.py
│   │
│   ├── recordAndPlayPos/         # Position Recording & Playback
│   │   ├── recordPos.py
│   │   ├── playPos.py
│   │   └── goHome.py
│   │
│   ├── handpose_det/             # Hand Gesture Control
│   │   └── (hand tracking to arm control)
│   │
│   ├── gamepad/                  # Gamepad Control
│   │   ├── gamepadecontrol.py
│   │   └── main.py
│   │
│   ├── calibration/              # Camera Calibration
│   │   ├── hand_eye_calibration.py
│   │   ├── camera_intrinsics.yaml
│   │   ├── charuco_board_A4.png
│   │   └── verify_calibration.py
│   │
│   ├── piper_kinematics/         # ROS2 Kinematics Package
│   │   ├── scripts/piper_ik_node.py
│   │   └── launch/
│   │
│   ├── cubeAndLineDet/           # Object Detection (ROS2)
│   │   ├── depth_camera_gui.py
│   │   └── src/cube_det.cpp
│   │
│   └── detection/                # Color-based Detection
│       ├── object_detector.py
│       └── calibrate_colors.py
│
├── training_data_samples/        # Imitation Learning Demo Data
│   ├── pick_and_place_demo.gif   # Animated demo
│   ├── episode1_*.png            # Sample frames
│   └── info.json                 # Dataset metadata
│
├── docs/                         # Documentation (18 guides)
│   ├── QUICK_SETUP.md
│   ├── CAN_TROUBLESHOOTING.md
│   ├── HOW_TO_USE_RVIZ2.md
│   └── ...
│
├── scripts/                      # Utility Scripts
│   ├── setup/                    # Installation & setup
│   ├── camera/                   # Camera utilities
│   └── can_debug/                # CAN bus debugging
│
├── PROJECT_MONTHLY_SUMMARY.md    # Detailed project summary
└── PROJECT_MONTHLY_SUMMARY.pdf   # PDF version
```

---

## Key Accomplishments

### 1. Vision-Guided Manipulation
- Integrated RealSense/Orbbec depth cameras
- Implemented object detection (color-based and depth-based)
- Built pick-and-place pipeline with coordinate transforms

### 2. Multiple Control Interfaces
- **Gamepad**: Full 6-DOF control with speed adjustment
- **Web Interface**: Remote control with live video streaming
- **Teach Mode**: Physical manipulation for trajectory recording
- **Hand Gestures**: Arm follows hand movements in real-time

### 3. Trajectory System
- Record movements using teach mode (press ENTER to stop)
- Save multiple named trajectories to JSON
- Playback with precise timing
- Management: rename, delete, view details, re-record

### 4. RGI Rotating Gripper Integration
- Modbus RTU serial communication
- Thread-safe concurrent control
- Open/close + rotation (specify degrees and direction)

### 5. Camera Calibration
- Hand-eye calibration using ChArUco markers
- Camera intrinsics calibration
- Coordinate transform verification

### 6. Imitation Learning (LeRobot)
- Dataset collection with gamepad teleoperation
- ACT (Action Chunking Transformer) policy training
- Real robot deployment

### 7. ROS2 Integration
- URDF visualization in RViz2
- Inverse kinematics solver
- Sim-to-real bridge

---

## Hardware

| Component | Model |
|-----------|-------|
| Robot Arm | Piper 6-DOF |
| Gripper | RGI Rotating Gripper |
| Depth Camera | Intel RealSense D435 / Orbbec Astra |
| Controller | Logitech Gamepad |
| Communication | CAN Bus @ 1Mbps |

---

## Documentation

All guides are in the [`docs/`](docs/) folder:

| Category | Guides |
|----------|--------|
| **Setup** | QUICK_SETUP, ROS_SETUP_GUIDE, BUILD_AND_RUN_ROS2 |
| **Visualization** | HOW_TO_USE_RVIZ2, LOAD_ROBOT_IN_RVIZ2, RVIZ2_SETUP_GUIDE |
| **Troubleshooting** | CAN_TROUBLESHOOTING, CAN_DEBUG_FIX |
| **Tutorials** | SIM_TO_REAL_GUIDE, QUICK_START_CUBE_DET |

---

## Technologies

**Languages:** Python, C++, Bash

**Frameworks:** ROS2 Jazzy, OpenCV, Flask, PyTorch, LeRobot

**Hardware Protocols:** CAN Bus, Modbus RTU, USB Serial

**Tools:** RViz2, Pygame, WebSockets

---

## Author

**Anika226** - Full system integration, control interfaces, trajectory system, web controller

---

## License

See individual component licenses. Original Piper resources from Agilex Robotics.
