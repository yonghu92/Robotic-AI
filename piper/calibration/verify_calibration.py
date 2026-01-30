#!/usr/bin/env python3
"""
Calibration Verification Script

Uses two colored cubes (red and green) with known separation distance
to verify the camera-arm calibration accuracy.

Physical setup:
- Red cube: 2 inches (5.08 cm)
- Green cube: 2 inches (5.08 cm)
- Separation: 21 cm center-to-center

Usage:
1. Place red and green cubes on the table, 21cm apart
2. Run this script
3. The script will detect both cubes and verify the calibration
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np
import yaml
import os
import sys
import time

# Add piper_sdk to path
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')
from piper_sdk import C_PiperInterface_V2


class CalibrationVerifier(Node):
    def __init__(self, piper_interface):
        super().__init__('calibration_verifier')

        self.bridge = CvBridge()
        self.piper = piper_interface

        # Expected parameters
        self.CUBE_SIZE_M = 0.0508  # 2 inches in meters
        self.EXPECTED_SEPARATION_M = 0.21  # 21 cm
        self.TOLERANCE_M = 0.02  # 2 cm tolerance

        # HSV ranges for color detection
        # Red has two ranges due to HSV wraparound
        self.RED_LOWER1 = np.array([0, 100, 100])
        self.RED_UPPER1 = np.array([10, 255, 255])
        self.RED_LOWER2 = np.array([160, 100, 100])
        self.RED_UPPER2 = np.array([180, 255, 255])

        # Green range
        self.GREEN_LOWER = np.array([35, 100, 100])
        self.GREEN_UPPER = np.array([85, 255, 255])

        # Camera data
        self.camera_matrix = None
        self.dist_coeffs = None
        self.camera_info_received = False
        self.current_image = None
        self.current_depth = None

        # Load calibration
        self.T_camera_to_ee = self.load_calibration()
        self.setup_forward_kinematics()

        # Subscribers
        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw',
            self.image_callback, 10)
        # Try aligned depth first, fall back to regular depth
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/depth/image_rect_raw',
            self.depth_callback, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_callback, 10)

        # Results storage
        self.red_cube_camera = None
        self.green_cube_camera = None
        self.red_cube_base = None
        self.green_cube_base = None

        self.get_logger().info('Calibration Verifier started')
        self.get_logger().info(f'Expected cube separation: {self.EXPECTED_SEPARATION_M*100:.1f} cm')

    def load_calibration(self):
        """Load hand-eye calibration"""
        filepath = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration/hand_eye_calibration.yaml'
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            T = np.array(data['camera_to_end_effector']['transformation_matrix'])
            self.get_logger().info(f'Loaded calibration from {filepath}')
            return T
        except Exception as e:
            self.get_logger().error(f'Failed to load calibration: {e}')
            return np.eye(4)

    def setup_forward_kinematics(self):
        """Setup DH parameters for forward kinematics"""
        self.dh_params = [
            [-np.pi/2, 0, 0.123, 0],
            [0, 0.28503, 0, -172.22/180*np.pi],
            [np.pi/2, -0.021984, 0, -102.78/180*np.pi],
            [-np.pi/2, 0, 0.25075, 0],
            [np.pi/2, 0, 0, 0],
            [0, 0, 0.211, 0]
        ]

    def compute_dh_transform(self, alpha, a, d, theta):
        ca, sa = np.cos(alpha), np.sin(alpha)
        ct, st = np.cos(theta), np.sin(theta)
        return np.array([
            [ct, -st*ca,  st*sa, a*ct],
            [st,  ct*ca, -ct*sa, a*st],
            [0,   sa,     ca,    d],
            [0,   0,      0,     1]
        ])

    def compute_forward_kinematics(self, joint_values):
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

    def get_current_joints(self):
        try:
            joints = self.piper.GetArmJointMsgs().joint_state
            return np.array([
                joints.joint_1 / 1000.0 * np.pi / 180.0,
                joints.joint_2 / 1000.0 * np.pi / 180.0,
                joints.joint_3 / 1000.0 * np.pi / 180.0,
                joints.joint_4 / 1000.0 * np.pi / 180.0,
                joints.joint_5 / 1000.0 * np.pi / 180.0,
                joints.joint_6 / 1000.0 * np.pi / 180.0,
            ])
        except Exception as e:
            self.get_logger().error(f'Failed to get joints: {e}')
            return None

    def camera_info_callback(self, msg):
        if not self.camera_info_received:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.dist_coeffs = np.array(msg.d)
            self.camera_info_received = True
            self.get_logger().info('Camera intrinsics received')

    def image_callback(self, msg):
        try:
            self.current_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'Image callback error: {e}')

    def depth_callback(self, msg):
        try:
            self.current_depth = self.bridge.imgmsg_to_cv2(msg, '16UC1')
        except Exception as e:
            self.get_logger().error(f'Depth callback error: {e}')

    def detect_cube_by_color(self, image, color_name):
        """Detect a cube by its color and return center pixel coordinates"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        if color_name == 'red':
            mask1 = cv2.inRange(hsv, self.RED_LOWER1, self.RED_UPPER1)
            mask2 = cv2.inRange(hsv, self.RED_LOWER2, self.RED_UPPER2)
            mask = cv2.bitwise_or(mask1, mask2)
        elif color_name == 'green':
            mask = cv2.inRange(hsv, self.GREEN_LOWER, self.GREEN_UPPER)
        else:
            return None, None

        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None, None

        # Find largest contour (should be the cube)
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        # Filter by minimum area
        if area < 500:
            return None, None

        # Get bounding rect and center
        x, y, w, h = cv2.boundingRect(largest)
        center_x = x + w // 2
        center_y = y + h // 2

        return (center_x, center_y), (x, y, w, h)

    def pixel_to_3d_camera(self, u, v, depth_image):
        """Convert pixel coordinates to 3D camera frame coordinates"""
        if self.camera_matrix is None:
            return None

        # Get depth at pixel (average over small region for noise reduction)
        roi_size = 5
        u_min = max(0, u - roi_size)
        u_max = min(depth_image.shape[1], u + roi_size)
        v_min = max(0, v - roi_size)
        v_max = min(depth_image.shape[0], v + roi_size)

        depth_roi = depth_image[v_min:v_max, u_min:u_max]
        valid_depths = depth_roi[depth_roi > 0]

        if len(valid_depths) == 0:
            return None

        depth_mm = np.median(valid_depths)
        depth_m = depth_mm / 1000.0

        # Unproject using camera intrinsics
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        X = (u - cx) * depth_m / fx
        Y = (v - cy) * depth_m / fy
        Z = depth_m

        return np.array([X, Y, Z])

    def transform_camera_to_base(self, point_camera):
        """Transform point from camera frame to base frame"""
        current_joints = self.get_current_joints()
        if current_joints is None:
            return None

        T_base_to_ee = self.compute_forward_kinematics(current_joints)
        T_ee_to_camera = np.linalg.inv(self.T_camera_to_ee)
        T_base_to_camera = T_base_to_ee @ T_ee_to_camera

        point_h = np.append(point_camera, 1.0)
        point_base_h = T_base_to_camera @ point_h

        return point_base_h[:3]

    def run_verification(self):
        """Main verification loop"""
        cv2.namedWindow('Calibration Verification', cv2.WINDOW_NORMAL)

        print('\n' + '='*60)
        print('  CALIBRATION VERIFICATION')
        print('='*60)
        print(f'Expected cube separation: {self.EXPECTED_SEPARATION_M*100:.1f} cm')
        print(f'Tolerance: ±{self.TOLERANCE_M*100:.1f} cm')
        print('\nPlace red and green cubes 21cm apart')
        print('Press SPACE to capture, Q to quit')
        print('='*60 + '\n')

        # Wait for data
        print('Waiting for camera data...')
        for _ in range(300):  # 15 seconds
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.current_image is not None and self.current_depth is not None and self.camera_info_received:
                print('Camera ready!')
                break
        else:
            print('ERROR: No camera data received')
            return

        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)

            if self.current_image is None or self.current_depth is None:
                continue

            vis_image = self.current_image.copy()

            # Detect cubes
            red_center, red_rect = self.detect_cube_by_color(vis_image, 'red')
            green_center, green_rect = self.detect_cube_by_color(vis_image, 'green')

            # Draw detections
            if red_rect:
                x, y, w, h = red_rect
                cv2.rectangle(vis_image, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(vis_image, 'RED', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                if red_center:
                    cv2.circle(vis_image, red_center, 5, (255, 255, 255), -1)

            if green_rect:
                x, y, w, h = green_rect
                cv2.rectangle(vis_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(vis_image, 'GREEN', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if green_center:
                    cv2.circle(vis_image, green_center, 5, (255, 255, 255), -1)

            # Status text
            status = "SPACE: Capture | Q: Quit"
            if red_center and green_center:
                status = "Both cubes detected! " + status
                cv2.putText(vis_image, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                missing = []
                if not red_center:
                    missing.append('RED')
                if not green_center:
                    missing.append('GREEN')
                status = f"Missing: {', '.join(missing)} | " + status
                cv2.putText(vis_image, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            cv2.imshow('Calibration Verification', vis_image)
            key = cv2.waitKey(1) & 0xFF

            if key == ord(' ') and red_center and green_center:
                self.perform_measurement(red_center, green_center, vis_image)
            elif key == ord('q') or key == ord('Q'):
                break

        cv2.destroyAllWindows()

    def perform_measurement(self, red_center, green_center, vis_image):
        """Perform calibration measurement"""
        print('\n' + '-'*50)
        print('MEASURING...')

        # Get 3D positions in camera frame
        red_3d_camera = self.pixel_to_3d_camera(red_center[0], red_center[1], self.current_depth)
        green_3d_camera = self.pixel_to_3d_camera(green_center[0], green_center[1], self.current_depth)

        if red_3d_camera is None or green_3d_camera is None:
            print('ERROR: Could not get depth for one or both cubes')
            return

        print(f'\nCamera Frame:')
        print(f'  Red cube:   X={red_3d_camera[0]*100:.2f}cm, Y={red_3d_camera[1]*100:.2f}cm, Z={red_3d_camera[2]*100:.2f}cm')
        print(f'  Green cube: X={green_3d_camera[0]*100:.2f}cm, Y={green_3d_camera[1]*100:.2f}cm, Z={green_3d_camera[2]*100:.2f}cm')

        # Calculate distance in camera frame
        dist_camera = np.linalg.norm(red_3d_camera - green_3d_camera)
        print(f'\n  Distance in camera frame: {dist_camera*100:.2f} cm')

        # Transform to base frame
        red_3d_base = self.transform_camera_to_base(red_3d_camera)
        green_3d_base = self.transform_camera_to_base(green_3d_camera)

        if red_3d_base is None or green_3d_base is None:
            print('ERROR: Could not transform to base frame')
            return

        print(f'\nBase Frame:')
        print(f'  Red cube:   X={red_3d_base[0]*100:.2f}cm, Y={red_3d_base[1]*100:.2f}cm, Z={red_3d_base[2]*100:.2f}cm')
        print(f'  Green cube: X={green_3d_base[0]*100:.2f}cm, Y={green_3d_base[1]*100:.2f}cm, Z={green_3d_base[2]*100:.2f}cm')

        # Calculate distance in base frame
        dist_base = np.linalg.norm(red_3d_base - green_3d_base)
        print(f'\n  Distance in base frame: {dist_base*100:.2f} cm')

        # Compare with expected
        error = abs(dist_base - self.EXPECTED_SEPARATION_M)
        error_camera = abs(dist_camera - self.EXPECTED_SEPARATION_M)

        print(f'\n' + '='*50)
        print(f'VERIFICATION RESULTS:')
        print(f'  Expected separation: {self.EXPECTED_SEPARATION_M*100:.1f} cm')
        print(f'  Measured (camera):   {dist_camera*100:.2f} cm (error: {error_camera*100:.2f} cm)')
        print(f'  Measured (base):     {dist_base*100:.2f} cm (error: {error*100:.2f} cm)')

        if error <= self.TOLERANCE_M:
            print(f'\n  ✓ CALIBRATION PASSED! Error within ±{self.TOLERANCE_M*100:.1f}cm tolerance')
        else:
            print(f'\n  ✗ CALIBRATION FAILED! Error exceeds ±{self.TOLERANCE_M*100:.1f}cm tolerance')
            print(f'\n  RECOMMENDATIONS:')

            # Analyze error sources
            if abs(error_camera) > self.TOLERANCE_M:
                print('    - Camera distance already has error -> Check depth accuracy')
                print('    - Try moving cubes closer to camera')

            if error > error_camera:
                print('    - Base frame error larger -> Calibration transform may need adjustment')
                print('    - Consider re-running hand-eye calibration with more poses')

            # Calculate approximate translation correction
            scale_factor = self.EXPECTED_SEPARATION_M / dist_base
            print(f'\n  Approximate scale correction needed: {scale_factor:.4f}')

            # Check Z difference (should be similar if cubes on same surface)
            z_diff_base = abs(red_3d_base[2] - green_3d_base[2])
            print(f'  Z-difference in base frame: {z_diff_base*100:.2f} cm (should be ~0 if on same surface)')

        print('='*50 + '\n')

        # Store results
        self.red_cube_camera = red_3d_camera
        self.green_cube_camera = green_3d_camera
        self.red_cube_base = red_3d_base
        self.green_cube_base = green_3d_base


def main():
    print('\n' + '='*60)
    print('  CAMERA-ARM CALIBRATION VERIFICATION')
    print('='*60)

    # Connect to arm
    print('\nConnecting to Piper arm via CAN...')
    try:
        piper = C_PiperInterface_V2("can0")
        piper.ConnectPort()
        time.sleep(0.5)
        print('Arm connected!')
    except Exception as e:
        print(f'ERROR: Failed to connect to arm: {e}')
        print('Make sure CAN is up: sudo ip link set can0 up type can bitrate 1000000')
        return

    rclpy.init()
    node = CalibrationVerifier(piper)

    try:
        node.run_verification()
    except KeyboardInterrupt:
        print('\nInterrupted')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
