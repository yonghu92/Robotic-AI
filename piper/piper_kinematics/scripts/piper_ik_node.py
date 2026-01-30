#!/usr/bin/env python3
"""
Piper Robot Inverse Kinematics Node for ROS2
Subscribes to target pose and publishes joint states
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool
import numpy as np
from scipy.spatial.transform import Rotation

class PiperForwardKinematics:
    """Forward kinematics for Piper 6-DOF arm using DH parameters"""

    def __init__(self, dh_type='standard'):
        self.dh_type = dh_type
        self.setup_dh_parameters()

    def setup_dh_parameters(self):
        """Setup DH parameters [alpha, a, d, theta_offset]"""
        if self.dh_type == 'standard':
            self.dh_params = [
                [-np.pi/2, 0, 0.123, 0],                          # Joint 1
                [0, 0.28503, 0, -172.22/180*np.pi],               # Joint 2
                [np.pi/2, -0.021984, 0, -102.78/180*np.pi],       # Joint 3
                [-np.pi/2, 0, 0.25075, 0],                        # Joint 4
                [np.pi/2, 0, 0, 0],                               # Joint 5
                [0, 0, 0.211, 0]                                  # Joint 6
            ]
        else:  # modified
            self.dh_params = [
                [0, 0, 0.123, 0],                                 # Joint 1
                [-np.pi/2, 0, 0, -172.22/180*np.pi],              # Joint 2
                [0, 0.28503, 0, -102.78/180*np.pi],               # Joint 3
                [np.pi/2, -0.021984, 0.25075, 0],                 # Joint 4
                [-np.pi/2, 0, 0, 0],                              # Joint 5
                [np.pi/2, 0, 0.211, 0]                            # Joint 6
            ]

    def compute_transform(self, alpha, a, d, theta):
        """Compute single DH transformation matrix"""
        ca, sa = np.cos(alpha), np.sin(alpha)
        ct, st = np.cos(theta), np.sin(theta)

        if self.dh_type == 'standard':
            T = np.array([
                [ct, -st*ca,  st*sa, a*ct],
                [st,  ct*ca, -ct*sa, a*st],
                [0,   sa,     ca,    d],
                [0,   0,      0,     1]
            ])
        else:  # modified
            T = np.array([
                [ct,      -st,       0,     a],
                [st*ca,   ct*ca,    -sa,   -sa*d],
                [st*sa,   ct*sa,    ca,    ca*d],
                [0,       0,        0,      1]
            ])
        return T

    def compute_fk(self, joint_values):
        """Compute forward kinematics for given joint values"""
        T = np.eye(4)
        for i in range(6):
            theta = joint_values[i] + self.dh_params[i][3]
            T = T @ self.compute_transform(
                self.dh_params[i][0],  # alpha
                self.dh_params[i][1],  # a
                self.dh_params[i][2],  # d
                theta                  # theta
            )
        return T


class PiperJacobianIK:
    """Jacobian-based IK solver for Piper arm"""

    def __init__(self, dh_type='standard'):
        self.fk = PiperForwardKinematics(dh_type)
        self.max_iterations = 200
        self.position_tolerance = 5e-3  # 5mm tolerance
        self.orientation_tolerance = 0.1  # More relaxed orientation
        self.damping = 0.5  # More damping for stability

        # Joint limits (radians)
        self.joint_limits = [
            (-2.618, 2.618),   # Joint 1: +/-150 deg
            (0, np.pi),        # Joint 2: 0-180 deg
            (-np.pi, 0),       # Joint 3: -180-0 deg
            (-2.967, 2.967),   # Joint 4: +/-170 deg
            (-1.2, 1.2),       # Joint 5: +/-69 deg
            (-1.22, 1.22)      # Joint 6: +/-70 deg
        ]

    def compute_numerical_jacobian(self, joint_values, delta=1e-6):
        """Compute Jacobian numerically"""
        J = np.zeros((6, 6))
        T0 = self.fk.compute_fk(joint_values)
        p0 = T0[:3, 3]
        R0 = T0[:3, :3]

        for i in range(6):
            joints_plus = joint_values.copy()
            joints_plus[i] += delta
            T_plus = self.fk.compute_fk(joints_plus)

            # Position derivative
            J[:3, i] = (T_plus[:3, 3] - p0) / delta

            # Orientation derivative (using rotation matrix difference)
            R_plus = T_plus[:3, :3]
            dR = (R_plus - R0) / delta
            # Extract angular velocity from skew-symmetric part
            J[3, i] = dR[2, 1] - dR[1, 2]
            J[4, i] = dR[0, 2] - dR[2, 0]
            J[5, i] = dR[1, 0] - dR[0, 1]

        return J

    def compute_pose_error(self, current_T, target_T):
        """Compute pose error (position + orientation)"""
        error = np.zeros(6)

        # Position error
        error[:3] = target_T[:3, 3] - current_T[:3, 3]

        # Orientation error (axis-angle)
        R_error = target_T[:3, :3] @ current_T[:3, :3].T
        r = Rotation.from_matrix(R_error)
        rotvec = r.as_rotvec()
        error[3:6] = rotvec

        return error

    def clamp_joints(self, joints):
        """Clamp joint values to limits"""
        clamped = joints.copy()
        for i in range(6):
            clamped[i] = np.clip(clamped[i], self.joint_limits[i][0], self.joint_limits[i][1])
        return clamped

    def compute_ik(self, initial_guess, target_pose):
        """
        Compute IK using damped least squares (Levenberg-Marquardt)

        Args:
            initial_guess: Initial joint values (6,)
            target_pose: Target pose as 4x4 transformation matrix

        Returns:
            joint_values: Solution joint values (6,)
            success: Whether IK converged
        """
        joints = np.array(initial_guess[:6], dtype=float)

        for iteration in range(self.max_iterations):
            current_T = self.fk.compute_fk(joints)
            error = self.compute_pose_error(current_T, target_pose)

            pos_error = np.linalg.norm(error[:3])
            orient_error = np.linalg.norm(error[3:6])

            # Check convergence
            if pos_error < self.position_tolerance and orient_error < self.orientation_tolerance:
                return joints, True

            # Compute Jacobian
            J = self.compute_numerical_jacobian(joints)

            # Damped least squares
            JJt = J @ J.T
            JJt += self.damping**2 * np.eye(6)
            delta_theta = J.T @ np.linalg.solve(JJt, error)

            # Update joints
            joints = joints + delta_theta
            joints = self.clamp_joints(joints)

        return joints, False


class PiperIKNode(Node):
    """ROS2 node for Piper IK"""

    def __init__(self):
        super().__init__('piper_ik_node')

        # Parameters
        self.declare_parameter('dh_type', 'standard')
        self.declare_parameter('publish_rate', 30.0)

        dh_type = self.get_parameter('dh_type').get_parameter_value().string_value
        publish_rate = self.get_parameter('publish_rate').get_parameter_value().double_value

        # Initialize IK solver
        self.ik_solver = PiperJacobianIK(dh_type)

        # Current joint state (start at home position)
        self.current_joints = np.array([0.0, 0.5, -0.5, 0.0, 0.0, 0.0])
        self.gripper_value = 0.0

        # Target pose (initialize to current FK)
        self.target_pose = self.ik_solver.fk.compute_fk(self.current_joints)
        self.has_target = False

        # Publishers
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.ik_status_pub = self.create_publisher(Bool, '/ik_status', 10)

        # Subscribers
        self.target_sub = self.create_subscription(
            PoseStamped, '/target_pose', self.target_pose_callback, 10)

        # Timer for publishing
        self.timer = self.create_timer(1.0/publish_rate, self.publish_joint_state)

        self.get_logger().info(f'Piper IK Node started with {dh_type} DH parameters')

    def pose_msg_to_matrix(self, pose_msg):
        """Convert geometry_msgs/Pose to 4x4 transformation matrix"""
        T = np.eye(4)
        T[0, 3] = pose_msg.position.x
        T[1, 3] = pose_msg.position.y
        T[2, 3] = pose_msg.position.z

        q = [pose_msg.orientation.x, pose_msg.orientation.y,
             pose_msg.orientation.z, pose_msg.orientation.w]
        R = Rotation.from_quat(q).as_matrix()
        T[:3, :3] = R

        return T

    def target_pose_callback(self, msg):
        """Handle new target pose"""
        self.target_pose = self.pose_msg_to_matrix(msg.pose)
        self.has_target = True

        # Compute IK
        new_joints, success = self.ik_solver.compute_ik(self.current_joints, self.target_pose)

        # Publish IK status
        status_msg = Bool()
        status_msg.data = success
        self.ik_status_pub.publish(status_msg)

        # Always update joints (even partial solutions move towards target)
        self.current_joints = new_joints
        if success:
            self.get_logger().debug(f'IK solved: {np.rad2deg(new_joints)}')
        else:
            self.get_logger().debug('IK partial solution')

    def publish_joint_state(self):
        """Publish current joint state"""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6', 'joint7', 'joint8']

        # 6 arm joints + 2 gripper joints
        positions = list(self.current_joints) + [self.gripper_value, self.gripper_value]
        msg.position = positions

        self.joint_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PiperIKNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()
