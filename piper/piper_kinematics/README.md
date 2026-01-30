# Piper_kinematics - AgileX PiPER Robotic Arm Kinematics Tool

Implementation of inverse kinematics for AgileX PiPER robotic arm using the Eigen library.

![alt text](doc/image-2.gif)

## Tags
- Eigen
- Inverse Kinematics
- AgileX PiPER Robotic Arm
- Eigen3

## Repository
- Piper_kinematics: [https://github.com/vanstrong12138/Piper_kinematics](https://github.com/vanstrong12138/Piper_kinematics)
- Agilex-College: [https://github.com/agilexrobotics/Agilex-College](https://github.com/agilexrobotics/Agilex-College)

## Environment Setup

- Install Eigen3
```bash
sudo apt install libeigen3-dev
sudo apt install ros-noetic-eigen-conversions
```

## Build
```bash
cd your_ws
source devel/setup.sh
catkin_make
```

## Run RViz Simulation

1. Launch RViz simulation
```bash
roslaunch piper_description display_nocap_urdf_ik.launch
```

2. Launch inverse kinematics node
```bash
roslaunch piper_kinematics piper_ik.launch
```

3. Use interactive_marker_utils in RViz to publish 3D target positions
![alt text](doc/image.png)
![alt text](doc/image-1.png)

## Real Robot Deployment

1. Activate CAN communication
```bash
cd piper_ros
./find_all_can_port.sh
./can_activate.sh
```

2. Launch PiPER real robot control node
```bash
roslaunch piper_kinematics start_single_piper_ik_rviz.launch
```

3. Launch inverse kinematics node
```bash
roslaunch piper_kinematics piper_ik.launch
```

4. Use interactive_marker_utils in RViz to publish 3D target positions
![alt text](doc/image-2.gif)
