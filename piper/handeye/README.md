# Piper Hand-Eye Calibration

- **Eye-in-Hand**: Camera is fixed on the arm end-effector, calibration board is stationary. This yields the transformation matrix from end-effector to camera `T_ee_cam`. For grasping applications: `T_base_cam = T_base_ee × T_ee_cam`

- **Eye-to-Hand**: Calibration board is fixed on the arm end-effector, camera is stationary. This yields the transformation matrix from base frame to camera `T_base_cam`. For localization applications: `T_ee_cam = T_ee_base × T_base_cam`

## Prerequisites

- Ubuntu 22.04
- ROS2 Humble
- [Online calibration board generator](https://chev.me/arucogen/) (recommended to use `Original ArUco` dictionary)
- [ArUco marker detection](https://github.com/pal-robotics/aruco_ros/tree/humble-devel)
- [Piper arm control](https://github.com/agilexrobotics/piper_ros/tree/humble)
- [Hand-eye calibration package](https://github.com/agilexrobotics/handeye_calibration_ros)
- [USB camera intrinsic calibration](https://github.com/kehuanjack/camera) (optional)

## Calibration Steps

1. Create workspace and clone packages

    ```bash
    mkdir -p ~/handeye/src
    cd ~/handeye/src
    git clone -b humble-devel https://github.com/pal-robotics/aruco_ros.git
    git clone -b humble https://github.com/agilexrobotics/piper_ros.git
    git clone -b humble https://github.com/agilexrobotics/handeye_calibration_ros.git
    ```

2. Build workspace

    ```bash
    cd ~/handeye
    colcon build
    ```

3. Run ArUco marker detection

    ```bash
    source ~/handeye/src/install/setup.sh

    # The marker_id and marker_size must match the actual calibration board
    ros2 launch aruco_ros single.launch.py eye:=left marker_id:=582 marker_size:=0.0677
    ```

4. Connect camera and run camera node to publish image and camera_info topics. Using [IntelRealSense](https://github.com/IntelRealSense/realsense-ros) as an example:

    ```bash
    # The 'left' corresponds to the 'eye' parameter in step 3
    # Remap original camera topics to those subscribed by the ArUco detection node
    ros2 run realsense2_camera realsense2_camera_node --ros-args \
    -p rgb_camera.color_profile:=640x480x60 \
    --remap /camera/camera/color/image_raw:=/stereo/left/image_rect_color \
    --remap /camera/camera/color/camera_info:=/stereo/left/camera_info
    ```

5. Connect Piper arm, activate CAN module, and run arm control node

    ```bash
    bash ~/handeye/src/piper_ros/can_activate.sh
    source ~/handeye/src/install/setup.sh
    ros2 launch piper start_single_piper.launch.py can_port:=can0
    ```

6. Run Piper hand-eye calibration

    ```bash
    # The mode parameter is either eye_in_hand or eye_to_hand
    ros2 run handeye_calibration_ros handeye_calibration --ros-args \
    -p piper_topic:=/end_pose \
    -p marker_topic:=/aruco_single/pose \
    -p mode:=eye_in_hand
    ```

7. Control the arm following the terminal prompts for calibration. Two control methods are available:

    - **Teach mode**: Press the teach button and drag the arm directly. This is MIT mode with lower precision than position-velocity mode.
    - **[Gamepad control](https://github.com/kehuanjack/Gamepad_PiPER)**: Uses position-velocity mode for higher precision. Requires the gamepad teleoperation program.

## Additional Notes

1. View images

    ```bash
    ros2 run image_view image_view --ros-args --remap /image:=/aruco_single/result
    ```

2. View ArUco marker pose

    ```bash
    ros2 topic echo /aruco_single/pose
    ```

3. View arm end-effector pose

    ```bash
    ros2 topic echo /end_pose
    ```

4. The camera_info topic contains camera intrinsics and distortion parameters required by the ArUco detection program.

5. Other cameras (industrial, webcams, etc.) may require additional intrinsic and distortion calibration, and publishing this data as a camera_info topic.

6. In eye-to-hand calibration, T_ee_aruco can be eliminated when it remains constant during calibration, so it doesn't need to be measured.

7. The difference between eye-in-hand and eye-to-hand calibration is that eye-to-hand converts T_base_ee to T_ee_base as input.
