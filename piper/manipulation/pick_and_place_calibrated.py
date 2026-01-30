#!/usr/bin/env python3
"""
Pick and Place with Hand-Eye Calibration

This script:
1. Subscribes to cube detection from cube_det node
2. Transforms detected object positions to robot base frame using calibration
3. Uses Trac-IK to compute joint angles for target position
4. Commands the Piper arm to pick up detected objects

Requirements:
- Run cube_det node first: ros2 run cubeAndLineDet cube_det
- Camera must be running: ros2 launch realsense2_camera rs_launch.py
- Arm must be connected via CAN

Usage:
    python3 pick_and_place_calibrated.py
"""

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import MarkerArray
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np
import yaml
import sys
import time
import threading
from scipy.spatial.transform import Rotation as R

# Add paths
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/gamepad/src')

from piper_sdk import C_PiperInterface_V2

# Try to import IK solver
try:
    from kinematic_trac_ik import Kinematic
    IK_AVAILABLE = True
except ImportError:
    print("Warning: Trac-IK not available. Install with: pip install trac-ik")
    IK_AVAILABLE = False


class PickAndPlaceNode(Node):
    def __init__(self, piper_interface, ik_solver=None):
        super().__init__('pick_and_place_calibrated')

        self.piper = piper_interface
        self.ik_solver = ik_solver
        self.arm_enabled = False
        self.bridge = CvBridge()

        # Load hand-eye calibration
        calibration_path = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration/hand_eye_calibration.yaml'
        self.T_camera_to_ee = self.load_calibration(calibration_path)

        if self.T_camera_to_ee is None:
            self.get_logger().error('Failed to load calibration!')
            return

        # Setup forward kinematics
        self.setup_forward_kinematics()

        # Camera and detection state
        self.color_image = None
        self.depth_image = None
        self.camera_info = None
        self.detected_object = None
        self.detected_pixel = None  # For visualization
        self.detection_time = None
        self.detection_lock = threading.Lock()

        # HSV color detection parameters (for red/orange objects)
        self.hsv_lower = np.array([0, 100, 100])
        self.hsv_upper = np.array([15, 255, 255])

        # Pick and place state
        self.is_picking = False
        self.auto_pick = False  # Set to True to auto-pick detected objects
        self.pick_height_offset = 0.05  # 5cm above object for approach
        self.gripper_open = 70000  # Gripper open position
        self.gripper_closed = 15000  # Gripper closed position

        # Home position (joint angles in degrees)
        self.home_position = [0, 0, 0, 0, 0, 0]

        # Place position (where to drop objects) - adjust as needed
        self.place_position = [60, 20, -40, 0, 0, 0]  # Example position

        # Workspace limits (approximate for Piper arm) - expanded
        self.workspace_min = np.array([-0.5, -0.5, 0.0])  # meters
        self.workspace_max = np.array([0.5, 0.5, 0.7])  # meters

        # ========== CALIBRATION OFFSET (tune these if arm goes to wrong place) ==========
        # Positive X = move arm forward, Negative X = move arm backward
        # Positive Y = move arm left, Negative Y = move arm right
        # Positive Z = move arm up, Negative Z = move arm down
        self.calibration_offset = np.array([0.0, 0.0, 0.0])  # [x, y, z] in meters
        # ================================================================================

        # Camera subscribers
        self.color_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.color_callback, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/depth/image_rect_raw', self.depth_callback, 10)
        self.info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info', self.info_callback, 10)

        # Subscribe to cube detection
        self.cube_sub = self.create_subscription(
            MarkerArray, '/cube_coordinates',
            self.cube_callback, 10)

        # Also subscribe to object_point_camera for manual testing
        self.point_sub = self.create_subscription(
            PointStamped, '/object_point_camera',
            self.point_callback, 10)

        # Timer for pick and place logic
        self.timer = self.create_timer(0.1, self.pick_and_place_loop)

        # Publisher for object point (for testing with transform node)
        self.point_pub = self.create_publisher(PointStamped, '/object_point_base', 10)

        self.get_logger().info('Pick and Place Node started')
        self.get_logger().info('Waiting for object detection on /cube_coordinates...')
        self.get_logger().info('Commands: Press P to pick last detected object, H to go home')

    def manual_pick(self):
        """Manually trigger pick of last detected object"""
        print('[PICK] manual_pick called')
        with self.detection_lock:
            if self.detected_object is None:
                print('[PICK] ERROR: No object detected!')
                self.get_logger().warn('No object detected yet!')
                return

            target = self.detected_object.copy()
            print(f'[PICK] Target: x={target[0]:.3f}, y={target[1]:.3f}, z={target[2]:.3f}')

        if self.is_picking:
            print('[PICK] Already picking, skipping')
            self.get_logger().warn('Already picking!')
            return

        self.is_picking = True
        print('[PICK] Starting execute_pick...')
        try:
            self.execute_pick(target)
            print('[PICK] execute_pick completed')
        except Exception as e:
            print(f'[PICK] Exception: {e}')
            self.get_logger().error(f'Pick failed: {e}')
        finally:
            self.is_picking = False

    def color_callback(self, msg):
        """Handle color image"""
        self.color_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_callback(self, msg):
        """Handle depth image"""
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, 'passthrough')

    def info_callback(self, msg):
        """Handle camera info"""
        if self.camera_info is None:
            self.camera_info = msg
            self.get_logger().info('Camera info received')

    def pixel_to_3d(self, u, v, depth_mm):
        """Convert pixel + depth to 3D point in camera frame"""
        if self.camera_info is None:
            return None

        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        z = depth_mm / 1000.0  # Convert to meters
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        return np.array([x, y, z])

    def detect_object_hsv(self, image):
        """Detect object using HSV color thresholding"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create mask for the target color
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)

        # Also check for red wrap-around (hue > 170)
        hsv_lower2 = np.array([170, 100, 100])
        hsv_upper2 = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv, hsv_lower2, hsv_upper2)
        mask = cv2.bitwise_or(mask, mask2)

        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            return None, None, mask

        # Find largest contour
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        if area < 500:  # Minimum area threshold
            return None, None, mask

        # Get center of contour
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None, None, mask

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        return (cx, cy), largest, mask

    def process_detection(self):
        """Process camera images and detect objects"""
        if self.color_image is None or self.depth_image is None:
            return

        # Detect object in color image
        center, contour, mask = self.detect_object_hsv(self.color_image)

        if center is None:
            return

        cx, cy = center

        # Get depth at center (average over small region)
        region_size = 5
        y1 = max(0, cy - region_size)
        y2 = min(self.depth_image.shape[0], cy + region_size)
        x1 = max(0, cx - region_size)
        x2 = min(self.depth_image.shape[1], cx + region_size)

        depth_region = self.depth_image[y1:y2, x1:x2]
        valid_depths = depth_region[depth_region > 0]

        if len(valid_depths) == 0:
            return

        depth_mm = np.median(valid_depths)

        # Convert to 3D in camera frame
        point_camera = self.pixel_to_3d(cx, cy, depth_mm)
        if point_camera is None:
            return

        # Transform to base frame
        point_base = self.transform_to_base(point_camera)
        if point_base is None:
            return

        # Only update if within reachable workspace
        if not self.check_workspace(point_base):
            # Still update pixel for visualization but mark as out of reach
            with self.detection_lock:
                self.detected_pixel = (cx, cy)
                self.detected_object = None  # Can't reach this
            return

        # Update detection
        with self.detection_lock:
            self.detected_object = point_base
            self.detected_pixel = (cx, cy)
            self.detection_time = time.time()

    def load_calibration(self, filepath):
        """Load hand-eye calibration from yaml file"""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            T = np.array(data['camera_to_end_effector']['transformation_matrix'])
            self.get_logger().info(f'Loaded calibration from {filepath}')
            return T
        except Exception as e:
            self.get_logger().error(f'Failed to load calibration: {e}')
            return None

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
        """Compute end-effector pose from joint values (radians)"""
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
        """Get current joint positions from Piper arm (in radians)"""
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

    def transform_to_base(self, point_camera):
        """Transform point from camera frame to base frame"""
        current_joints = self.get_current_joints()
        if current_joints is None:
            return None

        # T_base_to_camera = T_base_to_ee @ T_ee_to_camera
        T_base_to_ee = self.compute_forward_kinematics(current_joints)
        T_ee_to_camera = np.linalg.inv(self.T_camera_to_ee)
        T_base_to_camera = T_base_to_ee @ T_ee_to_camera

        # Transform point
        point_homogeneous = np.array([point_camera[0], point_camera[1], point_camera[2], 1.0])
        point_base = T_base_to_camera @ point_homogeneous

        return point_base[:3]

    def cube_callback(self, msg):
        """Handle cube detection from cube_det node"""
        if len(msg.markers) == 0:
            return

        # Get the sphere marker (first marker contains position)
        for marker in msg.markers:
            if marker.type == 2:  # SPHERE type
                point_camera = np.array([
                    marker.pose.position.x,
                    marker.pose.position.y,
                    marker.pose.position.z
                ])

                # Transform to base frame
                point_base = self.transform_to_base(point_camera)

                if point_base is not None:
                    with self.detection_lock:
                        self.detected_object = point_base
                        self.detection_time = time.time()

                    self.get_logger().info(
                        f'Cube detected at base frame: '
                        f'x={point_base[0]:.3f}, y={point_base[1]:.3f}, z={point_base[2]:.3f} m'
                    )
                break

    def point_callback(self, msg):
        """Handle manual point input from test_transform.py"""
        point_camera = np.array([msg.point.x, msg.point.y, msg.point.z])
        point_base = self.transform_to_base(point_camera)

        if point_base is not None:
            with self.detection_lock:
                self.detected_object = point_base
                self.detection_time = time.time()

            self.get_logger().info(
                f'Point received at base frame: '
                f'x={point_base[0]:.3f}, y={point_base[1]:.3f}, z={point_base[2]:.3f} m'
            )

    def enable_arm(self):
        """Enable the arm for control"""
        if self.arm_enabled:
            return True

        self.get_logger().info('Enabling arm...')

        # Set CAN control mode
        for _ in range(50):
            self.piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
            time.sleep(0.05)

        # Enable motors
        for _ in range(100):
            if self.piper.EnablePiper():
                self.arm_enabled = True
                self.get_logger().info('Arm enabled!')
                return True
            time.sleep(0.05)

        self.get_logger().error('Failed to enable arm')
        return False

    def move_to_joint_position(self, joints_deg, speed=30):
        """Move arm to joint position (degrees)"""
        if not self.enable_arm():
            return False

        # Convert to millidegrees
        joints_mdeg = [int(j * 1000) for j in joints_deg]

        self.get_logger().info(f'Moving to joints: {joints_deg}')

        # Send command repeatedly
        for _ in range(100):
            self.piper.MotionCtrl_2(0x01, 0x01, speed, 0x00)
            self.piper.JointCtrl(*joints_mdeg)
            time.sleep(0.02)

            # Check if close to target
            current = self.get_current_joints()
            if current is not None:
                current_deg = current * 180 / np.pi
                error = np.max(np.abs(current_deg - np.array(joints_deg)))
                if error < 3:  # Within 3 degrees
                    self.get_logger().info('Position reached!')
                    return True

        return True

    def move_gripper(self, position, speed=200):
        """Move gripper to position (0=closed, 70000=open)"""
        self.get_logger().info(f'Moving gripper to {position}')
        for _ in range(50):
            self.piper.GripperCtrl(position, speed, 0x01, 0)
            time.sleep(0.02)

    def go_home(self):
        """Move arm to home position"""
        self.get_logger().info('Going home...')
        self.move_to_joint_position(self.home_position)

    def check_workspace(self, target_xyz):
        """Check if target is within workspace"""
        target = np.array(target_xyz)
        if np.any(target < self.workspace_min) or np.any(target > self.workspace_max):
            self.get_logger().warn(
                f'Target outside workspace: ({target[0]:.3f}, {target[1]:.3f}, {target[2]:.3f})\n'
                f'Workspace: x=[{self.workspace_min[0]:.2f}, {self.workspace_max[0]:.2f}], '
                f'y=[{self.workspace_min[1]:.2f}, {self.workspace_max[1]:.2f}], '
                f'z=[{self.workspace_min[2]:.2f}, {self.workspace_max[2]:.2f}]'
            )
            return False
        return True

    def compute_ik(self, target_xyz, orientation_euler=None):
        """Compute inverse kinematics for target position"""
        if self.ik_solver is None:
            self.get_logger().warn('IK solver not available')
            return None

        # Check workspace
        if not self.check_workspace(target_xyz):
            return None

        # Try multiple orientations to find a valid IK solution
        orientations_to_try = [
            [180, 0, 0],      # Pointing down
            [180, 30, 0],     # Tilted forward slightly
            [180, -30, 0],    # Tilted backward slightly
            [180, 45, 0],     # Tilted forward more
            [180, -45, 0],    # Tilted backward more
            [135, 0, 0],      # Angled down
            [150, 0, 0],      # Less angled
            [160, 0, 0],      # Almost vertical
            [180, 0, 45],     # Rotated around Z
            [180, 0, -45],    # Rotated other way
            [180, 0, 90],     # Rotated 90
            [180, 0, -90],    # Rotated -90
            [150, 30, 0],     # Combined tilt
            [150, -30, 0],    # Combined tilt other way
            [170, 20, 45],    # Complex orientation
            [170, 20, -45],   # Complex orientation
        ]

        if orientation_euler is not None:
            orientations_to_try.insert(0, orientation_euler)

        for euler in orientations_to_try:
            try:
                # Convert euler to quaternion wxyz
                quat_xyzw = R.from_euler('xyz', euler, degrees=True).as_quat()
                quat_wxyz = np.array([quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]])

                joint_angles = self.ik_solver.solve_ik(
                    target_position=np.array(target_xyz),
                    target_wxyz=quat_wxyz
                )

                if joint_angles is not None:
                    self.get_logger().info(f'IK solved with orientation {euler}')
                    return joint_angles

            except Exception as e:
                continue

        self.get_logger().error(f'IK failed for all orientations at ({target_xyz[0]:.3f}, {target_xyz[1]:.3f}, {target_xyz[2]:.3f})')
        return None

    def execute_pick(self, target):
        """Execute pick sequence for target position"""
        self.get_logger().info(f'Raw target: x={target[0]:.3f}, y={target[1]:.3f}, z={target[2]:.3f}')

        # Apply calibration offset
        target = target + self.calibration_offset
        self.get_logger().info(f'After offset: x={target[0]:.3f}, y={target[1]:.3f}, z={target[2]:.3f}')
        self.get_logger().info(f'Offset applied: {self.calibration_offset}')

        # Calculate horizontal distance from base
        h_dist = np.sqrt(target[0]**2 + target[1]**2)
        self.get_logger().info(f'Horizontal distance from base: {h_dist:.3f}m')

        # 1. Open gripper
        self.move_gripper(self.gripper_open)
        time.sleep(0.5)

        # 2. Compute approach position (above object)
        approach_pos = target.copy()
        approach_pos[2] += self.pick_height_offset

        self.get_logger().info(f'Approach position: x={approach_pos[0]:.3f}, y={approach_pos[1]:.3f}, z={approach_pos[2]:.3f}')

        # 3. Compute IK for approach - try with lower z if it fails
        approach_joints = self.compute_ik(approach_pos)
        if approach_joints is None:
            # Try with lower approach height
            approach_pos[2] = target[2] + 0.02  # Just 2cm above
            self.get_logger().info(f'Retry approach at: z={approach_pos[2]:.3f}')
            approach_joints = self.compute_ik(approach_pos)

        if approach_joints is None:
            # Skip approach, go directly to pick position
            self.get_logger().warn('Approach IK failed, trying direct pick')
            approach_joints = None
        else:
            # Convert to degrees and move
            approach_joints_deg = [j * 180 / np.pi for j in approach_joints]
            self.get_logger().info(f'Approach joints (deg): {[f"{j:.1f}" for j in approach_joints_deg]}')
            self.move_to_joint_position(approach_joints_deg, speed=20)
            time.sleep(1.0)

        # 5. Compute IK for pick position
        pick_joints = self.compute_ik(target)
        if pick_joints is None:
            self.get_logger().error('Failed to compute IK for pick position')
            return False

        pick_joints_deg = [j * 180 / np.pi for j in pick_joints]
        self.get_logger().info(f'Pick joints (deg): {[f"{j:.1f}" for j in pick_joints_deg]}')

        # 6. Move down to pick
        self.move_to_joint_position(pick_joints_deg, speed=15)
        time.sleep(0.5)

        # 7. Close gripper
        self.move_gripper(self.gripper_closed)
        time.sleep(0.5)

        # 8. Lift up
        self.move_to_joint_position(approach_joints_deg, speed=15)
        time.sleep(0.5)

        # 9. Move to place position
        self.get_logger().info('Moving to place position...')
        self.move_to_joint_position(self.place_position, speed=25)
        time.sleep(0.5)

        # 10. Open gripper to release
        self.move_gripper(self.gripper_open)
        time.sleep(0.5)

        # 11. Return home
        self.go_home()

        self.get_logger().info('Pick and place complete!')
        return True

    def pick_and_place_loop(self):
        """Main pick and place logic loop"""
        if self.is_picking:
            return

        with self.detection_lock:
            if self.detected_object is None:
                return

            # Check if detection is recent (within 2 seconds)
            if self.detection_time is None or (time.time() - self.detection_time) > 2.0:
                self.detected_object = None
                return

            target = self.detected_object.copy()

            # Only auto-pick if enabled
            if not self.auto_pick:
                # Just log the detection
                return

            self.detected_object = None  # Clear after processing

        # Start pick sequence
        self.is_picking = True

        try:
            self.execute_pick(target)
        except Exception as e:
            self.get_logger().error(f'Pick failed: {e}')
        finally:
            self.is_picking = False


def main():
    print('\n' + '='*60)
    print('  PICK AND PLACE WITH HAND-EYE CALIBRATION')
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
        return

    # Initialize IK solver
    ik_solver = None
    if IK_AVAILABLE:
        print('\nInitializing IK solver...')
        try:
            urdf_path = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf'
            ik_solver = Kinematic(urdf_path=urdf_path, target_link_name="link6")
            print('IK solver ready!')
        except Exception as e:
            print(f'WARNING: Failed to initialize IK: {e}')
            print('Pick and place will run in demo mode (no arm movement)')
    else:
        print('\nWARNING: Trac-IK not available. Running in demo mode.')

    print('\n' + '-'*60)
    print('Instructions:')
    print('1. Make sure cube_det is running: ros2 run cubeAndLineDet cube_det')
    print('2. Point camera at a colored cube')
    print('3. Detected objects will be logged')
    print('4. To enable auto-pick, set node.auto_pick = True')
    print('\nPress Ctrl+C to stop')
    print('='*60 + '\n')

    rclpy.init()
    node = PickAndPlaceNode(piper, ik_solver)

    # Create OpenCV window
    cv2.namedWindow('Pick and Place', cv2.WINDOW_NORMAL)

    gripper_open = True

    print('\nKeyboard commands (in OpenCV window):')
    print('  p - Pick last detected object')
    print('  h - Go to home position')
    print('  a - Toggle auto-pick mode')
    print('  g - Toggle gripper (open/close)')
    print('  q - Quit\n')

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.03)

            # Process detection
            node.process_detection()

            # Visualization
            if node.color_image is not None:
                vis_image = node.color_image.copy()

                # Draw detected object
                with node.detection_lock:
                    if node.detected_pixel is not None:
                        cx, cy = node.detected_pixel

                        if node.detected_object is not None:
                            # Object is reachable - green
                            cv2.circle(vis_image, (cx, cy), 10, (0, 255, 0), 2)
                            cv2.circle(vis_image, (cx, cy), 3, (0, 255, 0), -1)
                            obj = node.detected_object
                            text = f'Reachable: ({obj[0]*100:.1f}, {obj[1]*100:.1f}, {obj[2]*100:.1f}) cm'
                            cv2.putText(vis_image, text, (cx + 15, cy),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        else:
                            # Object detected but out of reach - red
                            cv2.circle(vis_image, (cx, cy), 10, (0, 0, 255), 2)
                            cv2.circle(vis_image, (cx, cy), 3, (0, 0, 255), -1)
                            cv2.putText(vis_image, 'OUT OF REACH', (cx + 15, cy),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # Status bar
                h, w = vis_image.shape[:2]
                status = f'Auto-pick: {"ON" if node.auto_pick else "OFF"}'
                status += f' | Picking: {"YES" if node.is_picking else "NO"}'
                cv2.putText(vis_image, status, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                cv2.putText(vis_image, 'P:Pick H:Home A:Auto G:Gripper Q:Quit', (10, h - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow('Pick and Place', vis_image)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            if key == ord('p'):
                print('\n>>> Manual pick triggered')
                threading.Thread(target=node.manual_pick).start()

            elif key == ord('h'):
                print('\n>>> Going home')
                threading.Thread(target=node.go_home).start()

            elif key == ord('a'):
                node.auto_pick = not node.auto_pick
                print(f'\n>>> Auto-pick: {"ON" if node.auto_pick else "OFF"}')

            elif key == ord('g'):
                gripper_open = not gripper_open
                pos = node.gripper_open if gripper_open else node.gripper_closed
                print(f'\n>>> Gripper: {"OPEN" if gripper_open else "CLOSED"}')
                threading.Thread(target=node.move_gripper, args=(pos,)).start()

            elif key == ord('q') or key == 27:  # q or ESC
                print('\n>>> Quit')
                break

    except KeyboardInterrupt:
        print('\nShutting down...')
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
