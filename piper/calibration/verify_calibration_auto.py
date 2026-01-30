#!/usr/bin/env python3
"""
Automated Calibration Verification Script

Uses two colored cubes (red and green) with known separation distance
to verify the camera-arm calibration accuracy.

Runs automatically without keyboard input - captures measurements
when both cubes are detected.

Physical setup:
- Red cube: 2 inches (5.08 cm)
- Green cube: 2 inches (5.08 cm)
- Separation: 21 cm center-to-center
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
from datetime import datetime

# Add piper_sdk to path
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')
from piper_sdk import C_PiperInterface_V2


class AutoCalibrationVerifier(Node):
    def __init__(self, piper_interface):
        super().__init__('auto_calibration_verifier')

        self.bridge = CvBridge()
        self.piper = piper_interface

        # Expected parameters
        self.CUBE_SIZE_M = 0.0508  # 2 inches in meters
        self.EXPECTED_SEPARATION_M = 0.21  # 21 cm
        self.TOLERANCE_M = 0.02  # 2 cm tolerance

        # HSV ranges for color detection (will be tuned)
        self.RED_LOWER1 = np.array([0, 80, 80])
        self.RED_UPPER1 = np.array([15, 255, 255])
        self.RED_LOWER2 = np.array([165, 80, 80])
        self.RED_UPPER2 = np.array([180, 255, 255])
        self.GREEN_LOWER = np.array([35, 60, 60])
        self.GREEN_UPPER = np.array([90, 255, 255])

        # Depth camera intrinsics (for non-aligned depth)
        self.depth_camera_matrix = None
        self.depth_info_received = False

        # Color camera data
        self.camera_matrix = None
        self.dist_coeffs = None
        self.camera_info_received = False
        self.current_image = None
        self.current_depth = None

        # Depth to color extrinsics
        self.depth_to_color_extrinsics = None

        # Load calibration
        self.T_camera_to_ee = self.load_calibration()
        self.setup_forward_kinematics()

        # Subscribers
        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw',
            self.image_callback, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/depth/image_rect_raw',
            self.depth_callback, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_callback, 10)
        self.depth_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/depth/camera_info',
            self.depth_info_callback, 10)

        # Results storage
        self.measurements = []
        self.num_measurements = 5  # Number of measurements to average

        self.get_logger().info('Auto Calibration Verifier started')
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
            self.get_logger().info(f'Color camera intrinsics received: fx={self.camera_matrix[0,0]:.1f}')

    def depth_info_callback(self, msg):
        if not self.depth_info_received:
            self.depth_camera_matrix = np.array(msg.k).reshape(3, 3)
            self.depth_info_received = True
            self.get_logger().info(f'Depth camera intrinsics received: fx={self.depth_camera_matrix[0,0]:.1f}')

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
            return None, None, None

        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None, None, mask

        # Find largest contour (should be the cube)
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        # Filter by minimum area
        if area < 300:
            return None, None, mask

        # Get bounding rect and center
        x, y, w, h = cv2.boundingRect(largest)
        center_x = x + w // 2
        center_y = y + h // 2

        return (center_x, center_y), (x, y, w, h), mask

    def pixel_to_3d_camera(self, u, v, depth_image):
        """Convert pixel coordinates to 3D camera frame coordinates.

        Since we're using non-aligned depth, we need to:
        1. Map color pixel to depth pixel using approximate scale
        2. Get depth at that location
        3. Unproject using depth intrinsics
        """
        if self.depth_camera_matrix is None or self.camera_matrix is None:
            return None

        # Approximate mapping from color to depth pixel
        # Assuming similar resolution and roughly aligned sensors
        color_h, color_w = self.current_image.shape[:2]
        depth_h, depth_w = depth_image.shape[:2]

        # Scale coordinates if resolutions differ
        u_depth = int(u * depth_w / color_w)
        v_depth = int(v * depth_h / color_h)

        # Clamp to valid range
        u_depth = max(0, min(depth_w - 1, u_depth))
        v_depth = max(0, min(depth_h - 1, v_depth))

        # Get depth at pixel (average over small region for noise reduction)
        roi_size = 8
        u_min = max(0, u_depth - roi_size)
        u_max = min(depth_w, u_depth + roi_size)
        v_min = max(0, v_depth - roi_size)
        v_max = min(depth_h, v_depth + roi_size)

        depth_roi = depth_image[v_min:v_max, u_min:u_max]
        valid_depths = depth_roi[depth_roi > 0]

        if len(valid_depths) == 0:
            return None

        depth_mm = np.median(valid_depths)
        depth_m = depth_mm / 1000.0

        # Unproject using depth camera intrinsics
        fx = self.depth_camera_matrix[0, 0]
        fy = self.depth_camera_matrix[1, 1]
        cx = self.depth_camera_matrix[0, 2]
        cy = self.depth_camera_matrix[1, 2]

        X = (u_depth - cx) * depth_m / fx
        Y = (v_depth - cy) * depth_m / fy
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

    def perform_measurement(self, red_center, green_center):
        """Perform a single calibration measurement"""
        # Get 3D positions in camera frame
        red_3d_camera = self.pixel_to_3d_camera(red_center[0], red_center[1], self.current_depth)
        green_3d_camera = self.pixel_to_3d_camera(green_center[0], green_center[1], self.current_depth)

        if red_3d_camera is None or green_3d_camera is None:
            return None

        # Calculate distance in camera frame
        dist_camera = np.linalg.norm(red_3d_camera - green_3d_camera)

        # Transform to base frame
        red_3d_base = self.transform_camera_to_base(red_3d_camera)
        green_3d_base = self.transform_camera_to_base(green_3d_camera)

        if red_3d_base is None or green_3d_base is None:
            return None

        # Calculate distance in base frame
        dist_base = np.linalg.norm(red_3d_base - green_3d_base)

        return {
            'red_camera': red_3d_camera,
            'green_camera': green_3d_camera,
            'red_base': red_3d_base,
            'green_base': green_3d_base,
            'dist_camera': dist_camera,
            'dist_base': dist_base
        }

    def save_results(self, results):
        """Save verification results to file"""
        filepath = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration/calibration_verification_results.yaml'

        avg_dist_camera = np.mean([r['dist_camera'] for r in results])
        avg_dist_base = np.mean([r['dist_base'] for r in results])
        std_dist_camera = np.std([r['dist_camera'] for r in results])
        std_dist_base = np.std([r['dist_base'] for r in results])

        error = abs(avg_dist_base - self.EXPECTED_SEPARATION_M)
        passed = error <= self.TOLERANCE_M

        data = {
            'verification_date': datetime.now().isoformat(),
            'expected_separation_m': float(self.EXPECTED_SEPARATION_M),
            'tolerance_m': float(self.TOLERANCE_M),
            'num_measurements': len(results),
            'results': {
                'avg_distance_camera_m': float(avg_dist_camera),
                'std_distance_camera_m': float(std_dist_camera),
                'avg_distance_base_m': float(avg_dist_base),
                'std_distance_base_m': float(std_dist_base),
                'error_m': float(error),
                'passed': passed
            },
            'individual_measurements': [
                {
                    'dist_camera_m': float(r['dist_camera']),
                    'dist_base_m': float(r['dist_base']),
                    'red_camera': [float(x) for x in r['red_camera']],
                    'green_camera': [float(x) for x in r['green_camera']],
                    'red_base': [float(x) for x in r['red_base']],
                    'green_base': [float(x) for x in r['green_base']]
                }
                for r in results
            ]
        }

        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        return filepath, passed, error, avg_dist_camera, avg_dist_base

    def run_auto_verification(self):
        """Automated verification loop"""
        print('\n' + '='*60)
        print('  AUTOMATED CALIBRATION VERIFICATION')
        print('='*60)
        print(f'Expected cube separation: {self.EXPECTED_SEPARATION_M*100:.1f} cm')
        print(f'Tolerance: ±{self.TOLERANCE_M*100:.1f} cm')
        print(f'Will collect {self.num_measurements} measurements')
        print('='*60 + '\n')

        # Wait for data
        print('Waiting for camera data...')
        for i in range(600):  # 30 seconds
            rclpy.spin_once(self, timeout_sec=0.05)
            if (self.current_image is not None and
                self.current_depth is not None and
                self.camera_info_received and
                self.depth_info_received):
                print('Camera ready!')
                break
            if i % 40 == 0:
                print(f'  Waiting... ({i//20}s)')
        else:
            print('ERROR: No camera data received')
            return False, None

        # Wait a bit for stable readings
        print('\nWaiting for stable readings...')
        time.sleep(2)

        # Collect measurements
        measurements = []
        failed_attempts = 0
        max_failed = 30
        stable_count = 0
        required_stable = 5  # Need 5 consecutive good detections before measuring

        print('\nLooking for cubes...')

        while len(measurements) < self.num_measurements and failed_attempts < max_failed:
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.current_image is None or self.current_depth is None:
                failed_attempts += 1
                continue

            # Detect cubes
            red_center, red_rect, red_mask = self.detect_cube_by_color(self.current_image, 'red')
            green_center, green_rect, green_mask = self.detect_cube_by_color(self.current_image, 'green')

            if red_center is None or green_center is None:
                stable_count = 0
                failed_attempts += 1
                if failed_attempts % 10 == 0:
                    missing = []
                    if red_center is None:
                        missing.append('RED')
                    if green_center is None:
                        missing.append('GREEN')
                    print(f'  Cubes not detected: missing {", ".join(missing)} (attempt {failed_attempts}/{max_failed})')
                continue

            stable_count += 1

            if stable_count >= required_stable:
                # Take measurement
                result = self.perform_measurement(red_center, green_center)

                if result is not None:
                    measurements.append(result)
                    print(f'Measurement {len(measurements)}/{self.num_measurements}: '
                          f'Camera dist: {result["dist_camera"]*100:.2f}cm, '
                          f'Base dist: {result["dist_base"]*100:.2f}cm')
                    stable_count = 0  # Reset for next measurement
                    time.sleep(0.5)  # Small delay between measurements
                else:
                    print('  Measurement failed (depth error)')
                    failed_attempts += 1

        if len(measurements) < self.num_measurements:
            print(f'\nWARNING: Only collected {len(measurements)} measurements')
            if len(measurements) == 0:
                print('ERROR: No measurements could be taken')
                return False, None

        # Save and report results
        filepath, passed, error, avg_cam, avg_base = self.save_results(measurements)

        print('\n' + '='*60)
        print('VERIFICATION RESULTS:')
        print('='*60)
        print(f'Expected separation: {self.EXPECTED_SEPARATION_M*100:.1f} cm')
        print(f'Measured (camera):   {avg_cam*100:.2f} cm')
        print(f'Measured (base):     {avg_base*100:.2f} cm')
        print(f'Error:               {error*100:.2f} cm')
        print(f'Tolerance:           ±{self.TOLERANCE_M*100:.1f} cm')

        if passed:
            print(f'\n✓ CALIBRATION PASSED!')
        else:
            print(f'\n✗ CALIBRATION FAILED - error exceeds tolerance')

            # Analyze error
            error_camera = abs(avg_cam - self.EXPECTED_SEPARATION_M)
            if error_camera > self.TOLERANCE_M:
                print('\nDiagnosis:')
                print('  - Camera-measured distance already has error')
                print('  - This suggests depth measurement issues')
                print('  - Try moving cubes closer to camera (30-60cm range)')
            elif error > error_camera:
                print('\nDiagnosis:')
                print('  - Base frame error is larger than camera error')
                print('  - This suggests hand-eye calibration needs adjustment')
                print('  - Consider re-running hand_eye_calibration.py')

        print(f'\nResults saved to: {filepath}')
        print('='*60 + '\n')

        return passed, measurements


def main():
    print('\n' + '='*60)
    print('  AUTOMATED CAMERA-ARM CALIBRATION VERIFICATION')
    print('='*60)

    # Connect to arm
    print('\nConnecting to Piper arm via CAN...')
    try:
        piper = C_PiperInterface_V2("can0")
        piper.ConnectPort()
        time.sleep(0.5)

        # Get current joint positions
        joints = piper.GetArmJointMsgs().joint_state
        print(f'Arm connected!')
        print(f'Current joints: J1={joints.joint_1/1000:.1f}°, J2={joints.joint_2/1000:.1f}°, '
              f'J3={joints.joint_3/1000:.1f}°, J4={joints.joint_4/1000:.1f}°, '
              f'J5={joints.joint_5/1000:.1f}°, J6={joints.joint_6/1000:.1f}°')
    except Exception as e:
        print(f'ERROR: Failed to connect to arm: {e}')
        print('Make sure CAN is up: sudo ip link set can0 up type can bitrate 1000000')
        return

    rclpy.init()
    node = AutoCalibrationVerifier(piper)

    try:
        passed, measurements = node.run_auto_verification()
        if passed:
            print('\nCalibration is GOOD - no corrections needed!')
        else:
            print('\nCalibration needs correction - see recommendations above')
    except KeyboardInterrupt:
        print('\nInterrupted')
    except Exception as e:
        print(f'\nERROR: {e}')
        import traceback
        traceback.print_exc()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
