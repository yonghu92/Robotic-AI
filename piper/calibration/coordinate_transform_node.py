#!/usr/bin/env python3
"""
Coordinate Transform Node for Piper Arm

Transforms points from camera frame to arm base frame using hand-eye calibration.

Subscribes to:
  - /object_point_camera: Points in camera frame (geometry_msgs/PointStamped)

Publishes:
  - /object_point_base: Points in arm base frame (geometry_msgs/PointStamped)
  - TF: camera_link -> base_link transform
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped, PoseStamped, TransformStamped
from tf2_ros import TransformBroadcaster
import numpy as np
import yaml
import os
import sys
import time

# Add piper_sdk to path
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')
from piper_sdk import C_PiperInterface_V2


class CoordinateTransformNode(Node):
    def __init__(self, piper_interface):
        super().__init__('coordinate_transform_node')

        self.piper = piper_interface

        # Load hand-eye calibration
        calibration_path = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration/hand_eye_calibration.yaml'
        self.T_camera_to_ee = self.load_calibration(calibration_path)

        if self.T_camera_to_ee is None:
            self.get_logger().error('Failed to load calibration! Run hand_eye_calibration.py first.')
            return

        # Setup forward kinematics (DH parameters for Piper)
        self.setup_forward_kinematics()

        # Publishers
        self.point_pub = self.create_publisher(PointStamped, '/object_point_base', 10)
        self.pose_pub = self.create_publisher(PoseStamped, '/object_pose_base', 10)

        # TF broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)

        # Subscribers
        self.point_sub = self.create_subscription(
            PointStamped, '/object_point_camera', self.point_callback, 10)
        self.pose_sub = self.create_subscription(
            PoseStamped, '/object_pose_camera', self.pose_callback, 10)

        # Timer to publish TF
        self.tf_timer = self.create_timer(0.05, self.publish_tf)  # 20Hz

        self.get_logger().info('Coordinate Transform Node started')
        self.get_logger().info(f'Camera to EE translation: x={self.T_camera_to_ee[0,3]:.3f}, y={self.T_camera_to_ee[1,3]:.3f}, z={self.T_camera_to_ee[2,3]:.3f}')

    def load_calibration(self, filepath):
        """Load hand-eye calibration from yaml file"""
        if not os.path.exists(filepath):
            self.get_logger().error(f'Calibration file not found: {filepath}')
            return None

        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)

            # Extract transformation matrix
            T = np.array(data['camera_to_end_effector']['transformation_matrix'])
            self.get_logger().info(f'Loaded calibration from {filepath}')
            return T
        except Exception as e:
            self.get_logger().error(f'Failed to load calibration: {e}')
            return None

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

    def get_current_joints(self):
        """Get current joint positions from Piper arm via CAN (in radians)"""
        try:
            joints = self.piper.GetArmJointMsgs().joint_state
            # Convert from millidegrees to radians
            return np.array([
                joints.joint_1 / 1000.0 * np.pi / 180.0,
                joints.joint_2 / 1000.0 * np.pi / 180.0,
                joints.joint_3 / 1000.0 * np.pi / 180.0,
                joints.joint_4 / 1000.0 * np.pi / 180.0,
                joints.joint_5 / 1000.0 * np.pi / 180.0,
                joints.joint_6 / 1000.0 * np.pi / 180.0,
            ])
        except Exception as e:
            self.get_logger().error(f'Failed to get joint states: {e}')
            return None

    def transform_point_to_base(self, point_camera):
        """
        Transform a point from camera frame to base frame.

        Args:
            point_camera: numpy array [x, y, z] in camera frame

        Returns:
            point_base: numpy array [x, y, z] in base frame
        """
        current_joints = self.get_current_joints()
        if current_joints is None:
            self.get_logger().warn('No joint state available')
            return None

        # Get current end-effector pose
        T_base_to_ee = self.compute_forward_kinematics(current_joints)

        # Full transform chain: base -> ee -> camera -> point
        # T_base_to_camera = T_base_to_ee @ T_ee_to_camera
        # T_ee_to_camera = inverse(T_camera_to_ee)
        T_ee_to_camera = np.linalg.inv(self.T_camera_to_ee)
        T_base_to_camera = T_base_to_ee @ T_ee_to_camera

        # Transform point
        point_camera_homogeneous = np.array([point_camera[0], point_camera[1], point_camera[2], 1.0])
        point_base_homogeneous = T_base_to_camera @ point_camera_homogeneous

        return point_base_homogeneous[:3]

    def point_callback(self, msg):
        """Transform point from camera frame to base frame"""
        point_camera = np.array([msg.point.x, msg.point.y, msg.point.z])

        point_base = self.transform_point_to_base(point_camera)
        if point_base is None:
            return

        # Publish transformed point
        out_msg = PointStamped()
        out_msg.header.stamp = self.get_clock().now().to_msg()
        out_msg.header.frame_id = 'base_link'
        out_msg.point.x = float(point_base[0])
        out_msg.point.y = float(point_base[1])
        out_msg.point.z = float(point_base[2])

        self.point_pub.publish(out_msg)
        self.get_logger().debug(f'Transformed point: camera({point_camera[0]:.3f}, {point_camera[1]:.3f}, {point_camera[2]:.3f}) -> base({point_base[0]:.3f}, {point_base[1]:.3f}, {point_base[2]:.3f})')

    def pose_callback(self, msg):
        """Transform pose from camera frame to base frame"""
        # For now, just transform the position
        point_camera = np.array([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z])

        point_base = self.transform_point_to_base(point_camera)
        if point_base is None:
            return

        # Publish transformed pose (orientation transformation would need more work)
        out_msg = PoseStamped()
        out_msg.header.stamp = self.get_clock().now().to_msg()
        out_msg.header.frame_id = 'base_link'
        out_msg.pose.position.x = float(point_base[0])
        out_msg.pose.position.y = float(point_base[1])
        out_msg.pose.position.z = float(point_base[2])
        out_msg.pose.orientation.w = 1.0  # Identity orientation for now

        self.pose_pub.publish(out_msg)

    def publish_tf(self):
        """Publish TF transform from camera to base"""
        current_joints = self.get_current_joints()
        if current_joints is None:
            return

        # Get current transforms
        T_base_to_ee = self.compute_forward_kinematics(current_joints)
        T_ee_to_camera = np.linalg.inv(self.T_camera_to_ee)
        T_base_to_camera = T_base_to_ee @ T_ee_to_camera

        # Extract rotation as quaternion
        from scipy.spatial.transform import Rotation
        R = T_base_to_camera[:3, :3]
        r = Rotation.from_matrix(R)
        quat = r.as_quat()  # [x, y, z, w]

        # Create transform message
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_link'
        t.child_frame_id = 'camera_color_optical_frame'

        t.transform.translation.x = float(T_base_to_camera[0, 3])
        t.transform.translation.y = float(T_base_to_camera[1, 3])
        t.transform.translation.z = float(T_base_to_camera[2, 3])
        t.transform.rotation.x = float(quat[0])
        t.transform.rotation.y = float(quat[1])
        t.transform.rotation.z = float(quat[2])
        t.transform.rotation.w = float(quat[3])

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    print('Connecting to Piper arm via CAN...')
    try:
        piper = C_PiperInterface_V2("can0")
        piper.ConnectPort()
        time.sleep(0.5)
        print('Arm connected!')
    except Exception as e:
        print(f'ERROR: Failed to connect to Piper arm: {e}')
        return

    rclpy.init(args=args)
    node = CoordinateTransformNode(piper)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\nShutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
