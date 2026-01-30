# Low-Cost Teleoperation Using Depth Camera

This project implements simple, low-cost teleoperation functionality using a depth camera for hand pose detection and robotic arm control.

## Hardware Requirements

- Orbbec Petrel (aligned depth and RGB images: 640x400 @ 30fps)
- (Optional): Intel RealSense D435 (aligned depth and RGB images: 640x480 @ 30fps)
- (Optional): Orbbec Gemini (aligned depth and RGB images: 640x400 @ 60fps)
- NVIDIA 3050 laptop (laptop with mobile 3050 GPU)
- AgileX Robotics Piper robotic arm

## Software Environment

- Ubuntu 20.04
- ROS Noetic

## Dependencies

### Install Required ROS Packages

```bash
sudo apt install -y ros-noetic-sensor-msgs ros-noetic-image-transport ros-noetic-cv-bridge ros-noetic-vision-msgs ros-noetic-image-geometry ros-noetic-pcl-conversions ros-noetic-pcl-ros ros-noetic-message-filters

git clone https://github.com/agilexrobotics/Agilex-College.git
cd Agilex-College/piper/
cp -r piper_kinematics/ your_ws/src/
catkin_make
```

### Reference Documentation

- Piper arm driver deployment: https://github.com/agilexrobotics/piper_sdk/blob/1_0_0_beta/README(ZH).MD
- Piper arm ROS control node: https://github.com/agilexrobotics/piper_ros/blob/noetic/README.MD

### Clone and Compile This Package

```bash
cd your_ws/src
git clone https://github.com/agilexrobotics/Agilex-College.git
cd Agilex-College/piper/
cp -r handpose_det/ your_ws/src/
cd your_ws/
catkin_make
source devel/setup.bash
```

## Launch Camera ROS Node

The camera must support automatic depth-to-color alignment (D2C). This project does not currently support cameras without automatic alignment. After alignment, depth and RGB images should have the same dimensions.

This project uses the [Orbbec Gemini](https://orbbec.com.cn/index/Product/info.html?cate=38&id=28) depth camera for testing. For configuration and setup, refer to the [Orbbec camera driver repository](https://github.com/orbbec/ros_astra_camera.git).

### Orbbec Gemini

Configure depth alignment in `gemini.launch` first, then:

```bash
source devel/setup.bash
roslaunch astra_camera gemini.launch
```

### Intel RealSense D435

```bash
roslaunch realsense2_camera rs_aligned_depth.launch
```

## Modify Robot Arm URDF File

1. Change the arm base coordinate frame name from `arm_base` to `base_link` in the URDF file
2. Reference `handpose_det/models/modified_piper.urdf` or `modified_piper_without_camera.urdf`
3. If replacing the model in [piper_ros](https://github.com/agilexrobotics/piper_ros/), remember to modify the launch file

## Setup CAN Communication and Arm Driver

Connect the CAN module to the PC, find the CAN bus, and launch the arm driver node:

```bash
# Find the arm's CAN port
./find_all_can_port.sh

# Connect to the arm's CAN port
./can_activate.sh

# Launch arm driver
roslaunch piper start_single_piper.launch
```

## Setup Inverse Kinematics

Use the `interactive_pose_marker` tool in `piper_kinematics` to drag the arm to the desired home position.

See the tool in [piper_kinematics](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/piper_kinematics).

Launch the inverse kinematics node to send control commands to Piper:

```bash
rosrun piper_kinematics piper_ik_node
rosrun piper_kinematics interactive_pose_marker.py
```

## Define Hand Pose Home Point

### Launch Hand Pose Detection Node

```bash
rosrun handpose_det handpose_det_new_ik.py
```

### Using RViz

Launch RViz to observe real-time image detection:
- **Red dots** in MarkerArray represent finger joints
- **Green dots** represent the palm center

### Calibration Process

1. **Hold a fist for 5 seconds** without moving
2. After 5 seconds, the current hand position will be defined as the origin of the hand coordinate system
3. Then **open your hand** to start mapping hand poses relative to this origin

**Tips for calibration:**
- Position your hand near the center of the image
- Don't be too far from the camera (causes unstable hand recognition)
- Don't be too close (limits teleoperation workspace due to restricted camera field of view)

### Gripper Control

Adjust the distance between thumb and index finger to control gripper open/close.

---

# Complete Workflow

```bash
cd your_ws
source devel/setup.sh

# 1. Activate CAN communication
cd piper_ros
./can_activate.sh

# 2. Launch arm control ROS node
roslaunch piper start_single_piper_rviz.launch

# 3. Launch camera driver node
roslaunch realsense2_camera rs_aligned_depth.launch

# 4. Launch hand gesture detection node
# Note: Modify topic names in scripts/handpose_det_new_ik.py to match your camera
roslaunch handpose_det hand_det_6d_pose.launch

# 5. Launch Piper inverse kinematics node
roslaunch piper_kinematics piper_ik.launch

# 6. Drag interactive_marker to define arm end-effector initial position

# 7. Position the camera as shown in the diagram below

# 8. Make a fist with right hand for 5 seconds to establish hand coordinate system

# 9. Open hand with four fingers together to control 6 DOF; thumb controls gripper
```

---

# Visual Workflow Guide

1. **Activate CAN communication**
   ![CAN activation](doc/image.png)

2. **Launch arm control ROS node**
   ![Arm control node](doc/image-1.png)

3. **Launch camera driver node**
   ![Camera driver](doc/image-2.png)

4. **Launch hand gesture detection node**
   ![Hand detection](doc/image-3.png)

5. **Launch Piper inverse kinematics node**
   ![IK node](doc/image-4.png)

6. **Drag interactive_marker to define arm end-effector initial position**
   ![Interactive marker 1](doc/image-5.png)
   ![Interactive marker 2](doc/image-6.png)
   ![Interactive marker 3](doc/image-7.png)

7. **Position camera as shown**
   ![Camera position](doc/image-8.png)

8. **Make fist with right hand for 5 seconds to establish hand coordinate system**
   ![Fist calibration](doc/image-9.png)

9. **Open hand with four fingers together to control 6 DOF; thumb controls gripper open/close**

---

# Control Summary

| Action | Result |
|--------|--------|
| Hold fist for 5 seconds | Calibrate hand coordinate origin |
| Move open hand | Control arm 6 DOF position |
| Pinch thumb + index finger | Close gripper |
| Spread thumb + index finger | Open gripper |
