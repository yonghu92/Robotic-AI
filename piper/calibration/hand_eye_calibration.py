#!/usr/bin/env python3
"""
Hand-Eye Calibration for Piper Arm with Eye-in-Hand RealSense Camera

This script performs hand-eye calibration to find the transform between
the camera frame and the end-effector frame.

For eye-in-hand configuration:
- Camera is mounted on the robot's end-effector
- We find: T_camera_to_ee (camera frame relative to end-effector)

Usage:
1. Place a ChArUco board or checkerboard in the workspace
2. Run this script
3. Move the arm to different poses (the script will guide you)
4. The calibration will compute and save the transform
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np
import yaml
import os
from datetime import datetime
import sys
import time

# Add piper_sdk to path
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')
from piper_sdk import C_PiperInterface_V2


class HandEyeCalibration(Node):
    def __init__(self, piper_interface):
        super().__init__('hand_eye_calibration')

        self.bridge = CvBridge()
        self.piper = piper_interface  # Piper arm interface via CAN

        # Calibration board parameters (ChArUco) - User's A4 printed board (3cm squares)
        self.charuco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.charuco_board = cv2.aruco.CharucoBoard(
            (6, 9),   # 6x9 squares (A4 with 3cm squares)
            0.03,     # Square size in meters (3cm)
            0.023,    # Marker size in meters (2.3cm) - 77% of square size
            self.charuco_dict
        )

        # Detection parameters will be set in detect_charuco method

        # Alternative: Checkerboard parameters (if using checkerboard instead)
        self.checkerboard_size = (8, 6)  # Inner corners
        self.square_size = 0.025  # 2.5cm squares

        # Camera intrinsics (will be loaded from camera_info)
        self.camera_matrix = None
        self.dist_coeffs = None
        self.camera_info_received = False

        # Collected calibration data
        self.robot_poses = []  # T_base_to_ee for each capture
        self.camera_poses = []  # T_camera_to_target for each capture

        # Current state
        self.current_image = None
        self.capture_count = 0
        self.min_captures = 10

        # Subscribers (camera only - joints from piper_sdk)
        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw',
            self.image_callback, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_callback, 10)

        # Forward kinematics (simplified DH parameters for Piper)
        self.setup_forward_kinematics()

        self.get_logger().info('Hand-Eye Calibration Node Started')
        self.get_logger().info('Press SPACE to capture a pose, Q to finish and compute calibration')

    def setup_forward_kinematics(self):
        """Setup DH parameters for forward kinematics"""
        # Standard DH parameters for Piper [alpha, a, d, theta_offset]
        self.dh_params = [
            [-np.pi/2, 0, 0.123, 0],
            [0, 0.28503, 0, -172.22/180*np.pi],
            [np.pi/2, -0.021984, 0, -102.78/180*np.pi],
            [-np.pi/2, 0, 0.25075, 0],
            [np.pi/2, 0, 0, 0],
            [0, 0, 0.211, 0]
        ]

    def compute_dh_transform(self, alpha, a, d, theta):
        """Compute single DH transformation matrix"""
        ca, sa = np.cos(alpha), np.sin(alpha)
        ct, st = np.cos(theta), np.sin(theta)
        return np.array([
            [ct, -st*ca,  st*sa, a*ct],
            [st,  ct*ca, -ct*sa, a*st],
            [0,   sa,     ca,    d],
            [0,   0,      0,     1]
        ])

    def compute_forward_kinematics(self, joint_values):
        """Compute end-effector pose from joint values"""
        T = np.eye(4)
        for i in range(6):
            theta = joint_values[i] + self.dh_params[i][3]
            T = T @ self.compute_dh_transform(
                self.dh_params[i][0],
                self.dh_params[i][1],
                self.dh_params[i][2],
                theta
            )
        return T

    def camera_info_callback(self, msg):
        """Extract camera intrinsics from camera_info message"""
        if not self.camera_info_received:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.dist_coeffs = np.array(msg.d)
            self.camera_info_received = True
            self.get_logger().info('Camera intrinsics received')

    def image_callback(self, msg):
        """Store latest image"""
        try:
            self.current_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')

    def get_current_joints(self):
        """Get current joint positions from Piper arm via CAN (in radians)"""
        try:
            joints = self.piper.GetArmJointMsgs().joint_state
            # Convert from millidegrees to radians
            joint_values = np.array([
                joints.joint_1 / 1000.0 * np.pi / 180.0,
                joints.joint_2 / 1000.0 * np.pi / 180.0,
                joints.joint_3 / 1000.0 * np.pi / 180.0,
                joints.joint_4 / 1000.0 * np.pi / 180.0,
                joints.joint_5 / 1000.0 * np.pi / 180.0,
                joints.joint_6 / 1000.0 * np.pi / 180.0,
            ])
            return joint_values
        except Exception as e:
            self.get_logger().error(f'Failed to get joint states: {e}')
            return None

    def detect_charuco(self, image):
        """Detect ChArUco board and estimate pose"""
        if self.camera_matrix is None:
            return None, None, image

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Step 1: Detect ArUco markers first with improved parameters
        detector_params = cv2.aruco.DetectorParameters()
        detector_params.adaptiveThreshWinSizeMin = 3
        detector_params.adaptiveThreshWinSizeMax = 23
        detector_params.adaptiveThreshWinSizeStep = 10
        detector_params.minMarkerPerimeterRate = 0.01
        detector_params.maxMarkerPerimeterRate = 4.0

        aruco_detector = cv2.aruco.ArucoDetector(self.charuco_dict, detector_params)
        marker_corners, marker_ids, rejected = aruco_detector.detectMarkers(gray)

        # Debug: show marker count on image
        marker_count = len(marker_ids) if marker_ids is not None else 0
        cv2.putText(image, f'Markers: {marker_count}', (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if marker_ids is not None and len(marker_ids) > 0:
            # Draw detected markers
            cv2.aruco.drawDetectedMarkers(image, marker_corners, marker_ids)

            # Step 2: Interpolate charuco corners from detected markers
            retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                marker_corners, marker_ids, gray, self.charuco_board
            )

            corners_count = len(charuco_corners) if charuco_corners is not None else 0
            cv2.putText(image, f'Corners: {corners_count}', (10, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            if charuco_corners is not None and len(charuco_corners) >= 4:
                # Draw charuco corners
                cv2.aruco.drawDetectedCornersCharuco(image, charuco_corners, charuco_ids)

                # Estimate pose
                success, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
                    charuco_corners, charuco_ids, self.charuco_board,
                    self.camera_matrix, self.dist_coeffs, None, None
                )

                if success:
                    cv2.drawFrameAxes(image, self.camera_matrix, self.dist_coeffs,
                                      rvec, tvec, 0.05)
                    return rvec, tvec, image

        return None, None, image

    def detect_checkerboard(self, image):
        """Detect checkerboard and estimate pose"""
        if self.camera_matrix is None:
            return None, None, image

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Find checkerboard corners
        ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)

        if ret:
            # Refine corners
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            # 3D object points
            objp = np.zeros((self.checkerboard_size[0] * self.checkerboard_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:self.checkerboard_size[0],
                                    0:self.checkerboard_size[1]].T.reshape(-1, 2)
            objp *= self.square_size

            # Estimate pose
            ret, rvec, tvec = cv2.solvePnP(objp, corners,
                                            self.camera_matrix, self.dist_coeffs)

            if ret:
                # Draw detection
                cv2.drawChessboardCorners(image, self.checkerboard_size, corners, ret)
                cv2.drawFrameAxes(image, self.camera_matrix, self.dist_coeffs,
                                  rvec, tvec, 0.05)
                return rvec, tvec, image

        return None, None, image

    def capture_pose(self):
        """Capture current pose for calibration"""
        print('[CAPTURE] Attempting capture...')
        current_joints = self.get_current_joints()
        if self.current_image is None:
            self.get_logger().warn('No image available')
            return False
        if current_joints is None:
            self.get_logger().warn('No joint data available')
            return False

        print(f'[CAPTURE] Joints (deg): {current_joints * 180 / np.pi}')

        # Try ChArUco first, then checkerboard
        rvec, tvec, vis_image = self.detect_charuco(self.current_image.copy())
        print(f'[CAPTURE] ChArUco detection: {"SUCCESS" if rvec is not None else "FAILED"}')

        if rvec is None:
            rvec, tvec, vis_image = self.detect_checkerboard(self.current_image.copy())
            print(f'[CAPTURE] Checkerboard detection: {"SUCCESS" if rvec is not None else "FAILED"}')

        if rvec is None:
            self.get_logger().warn('No calibration target detected! Make sure board is visible.')
            return False

        # Get robot pose (T_base_to_ee)
        T_base_to_ee = self.compute_forward_kinematics(current_joints)

        # Get camera pose (T_camera_to_target)
        R, _ = cv2.Rodrigues(rvec)
        T_camera_to_target = np.eye(4)
        T_camera_to_target[:3, :3] = R
        T_camera_to_target[:3, 3] = tvec.flatten()

        # Store poses
        self.robot_poses.append(T_base_to_ee)
        self.camera_poses.append(T_camera_to_target)
        self.capture_count += 1

        self.get_logger().info(f'Captured pose {self.capture_count}/{self.min_captures}')

        return True

    def compute_calibration(self):
        """Compute hand-eye calibration from collected poses"""
        if len(self.robot_poses) < self.min_captures:
            self.get_logger().error(f'Need at least {self.min_captures} poses, have {len(self.robot_poses)}')
            return None

        self.get_logger().info(f'Computing calibration with {len(self.robot_poses)} poses...')

        # Convert to rotation vectors and translation vectors
        R_gripper2base = []
        t_gripper2base = []
        R_target2cam = []
        t_target2cam = []

        for T_base_to_ee, T_cam_to_target in zip(self.robot_poses, self.camera_poses):
            # Gripper to base (inverse of base to ee)
            T_ee_to_base = np.linalg.inv(T_base_to_ee)
            R_gripper2base.append(T_ee_to_base[:3, :3])
            t_gripper2base.append(T_ee_to_base[:3, 3].reshape(3, 1))

            # Target to camera (inverse of camera to target)
            T_target_to_cam = np.linalg.inv(T_cam_to_target)
            R_target2cam.append(T_target_to_cam[:3, :3])
            t_target2cam.append(T_target_to_cam[:3, 3].reshape(3, 1))

        # Perform hand-eye calibration
        # For eye-in-hand: AX = XB
        # A = gripper motion, B = camera motion, X = cam_to_gripper
        R_cam2gripper, t_cam2gripper = cv2.calibrateHandEye(
            R_gripper2base, t_gripper2base,
            R_target2cam, t_target2cam,
            method=cv2.CALIB_HAND_EYE_TSAI
        )

        # Build transformation matrix
        T_camera_to_ee = np.eye(4)
        T_camera_to_ee[:3, :3] = R_cam2gripper
        T_camera_to_ee[:3, 3] = t_cam2gripper.flatten()

        return T_camera_to_ee

    def save_calibration(self, T_camera_to_ee):
        """Save calibration result to yaml file"""
        calibration_dir = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration'
        os.makedirs(calibration_dir, exist_ok=True)

        filepath = os.path.join(calibration_dir, 'hand_eye_calibration.yaml')

        # Extract rotation as quaternion and euler angles
        from scipy.spatial.transform import Rotation
        R = T_camera_to_ee[:3, :3]
        r = Rotation.from_matrix(R)
        quat = r.as_quat()  # [x, y, z, w]
        euler = r.as_euler('xyz', degrees=True)

        calibration_data = {
            'calibration_type': 'eye_in_hand',
            'calibration_date': datetime.now().isoformat(),
            'num_poses_used': len(self.robot_poses),
            'camera_to_end_effector': {
                'translation': {
                    'x': float(T_camera_to_ee[0, 3]),
                    'y': float(T_camera_to_ee[1, 3]),
                    'z': float(T_camera_to_ee[2, 3])
                },
                'rotation_quaternion': {
                    'x': float(quat[0]),
                    'y': float(quat[1]),
                    'z': float(quat[2]),
                    'w': float(quat[3])
                },
                'rotation_euler_xyz_degrees': {
                    'roll': float(euler[0]),
                    'pitch': float(euler[1]),
                    'yaw': float(euler[2])
                },
                'transformation_matrix': T_camera_to_ee.tolist()
            }
        }

        with open(filepath, 'w') as f:
            yaml.dump(calibration_data, f, default_flow_style=False)

        self.get_logger().info(f'Calibration saved to {filepath}')
        print(f'\nCalibration Result:')
        print(f'Translation (m): x={T_camera_to_ee[0,3]:.4f}, y={T_camera_to_ee[1,3]:.4f}, z={T_camera_to_ee[2,3]:.4f}')
        print(f'Rotation (deg): roll={euler[0]:.2f}, pitch={euler[1]:.2f}, yaw={euler[2]:.2f}')

        return filepath


def main():
    print('\n' + '='*60)
    print('  HAND-EYE CALIBRATION (Eye-in-Hand)')
    print('='*60)

    # Initialize Piper arm via CAN
    print('\nConnecting to Piper arm via CAN...')
    try:
        piper = C_PiperInterface_V2("can0")
        piper.ConnectPort()
        time.sleep(0.5)

        # Check arm status
        status = piper.GetArmStatus()
        print(f'Arm connected! Control mode: {status.arm_status.ctrl_mode}')

        # Get current joint positions to verify
        joints = piper.GetArmJointMsgs().joint_state
        print(f'Current joints: J1={joints.joint_1/1000:.1f}, J2={joints.joint_2/1000:.1f}, '
              f'J3={joints.joint_3/1000:.1f}, J4={joints.joint_4/1000:.1f}, '
              f'J5={joints.joint_5/1000:.1f}, J6={joints.joint_6/1000:.1f} deg')
    except Exception as e:
        print(f'ERROR: Failed to connect to Piper arm: {e}')
        print('Make sure CAN is enabled: sudo ip link set can0 up type can bitrate 1000000')
        return

    rclpy.init()
    node = HandEyeCalibration(piper)

    print('\nInstructions:')
    print('1. Place ChArUco board(s) in workspace (A4, 6x9 grid, 3cm squares)')
    print('   Note: 2 boards placed = better workspace coverage')
    print('2. Move the arm to view the board from different angles')
    print('3. Press SPACE to capture each pose')
    print('4. Capture at least 10-15 poses from varied angles')
    print('5. Press Q when done to compute calibration')
    print('='*60 + '\n')

    cv2.namedWindow('Calibration View', cv2.WINDOW_NORMAL)

    # Wait for camera image (30 seconds)
    print('Waiting for camera image (up to 30s)...')
    for i in range(600):
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.current_image is not None:
            print('Camera image received!')
            break
        if i % 100 == 0:
            print(f'  Still waiting... ({i//20}s)')
    else:
        print('ERROR: No camera image received. Make sure the camera is running.')
        print('Try: ros2 launch realsense2_camera rs_launch.py')
        node.destroy_node()
        rclpy.shutdown()
        return

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)

            # Skip if no image
            if node.current_image is None:
                continue

            # Display current view
            vis_image = node.current_image.copy()

            # Try to detect calibration target
            rvec, tvec, vis_image = node.detect_charuco(vis_image)
            if rvec is None:
                rvec, tvec, vis_image = node.detect_checkerboard(vis_image)

            # Show status
            status = f'Captures: {node.capture_count}/{node.min_captures}'
            if rvec is not None:
                status += ' | Target DETECTED'
                color = (0, 255, 0)
            else:
                status += ' | Target NOT FOUND'
                color = (0, 0, 255)

            cv2.putText(vis_image, status, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(vis_image, 'SPACE: Capture | Q: Finish', (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Show current joint angles
            current_joints = node.get_current_joints()
            if current_joints is not None:
                joints_deg = current_joints * 180 / np.pi
                joint_str = f'Joints: {joints_deg[0]:.0f}, {joints_deg[1]:.0f}, {joints_deg[2]:.0f}, {joints_deg[3]:.0f}, {joints_deg[4]:.0f}, {joints_deg[5]:.0f} deg'
                cv2.putText(vis_image, joint_str, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            cv2.imshow('Calibration View', vis_image)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' '):  # Space - capture
                node.capture_pose()
            elif key == ord('q') or key == ord('Q'):  # Q - finish
                break

    except KeyboardInterrupt:
        print('\nInterrupted by user')
    finally:
        cv2.destroyAllWindows()
        cv2.waitKey(1)  # Process any remaining events

    # Compute calibration if enough poses
    if node.capture_count >= node.min_captures:
        T_camera_to_ee = node.compute_calibration()
        if T_camera_to_ee is not None:
            node.save_calibration(T_camera_to_ee)
    else:
        print(f'\nNot enough poses captured ({node.capture_count}/{node.min_captures})')
        print('Run again and capture more poses.')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
