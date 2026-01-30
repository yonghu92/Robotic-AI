#!/usr/bin/env python3
"""
Bridge node that connects RViz2 joint state simulation to the physical Piper arm.
Subscribes to /joint_states and sends commands to the real arm via CAN bus.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import sys
import time

# Add piper_sdk to path
sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')

from piper_sdk import Piper


class SimToRealBridge(Node):
    def __init__(self):
        super().__init__('sim_to_real_bridge')

        # Parameters
        self.declare_parameter('can_interface', 'can0')
        self.declare_parameter('speed_percent', 30)  # Movement speed (1-100%)
        self.declare_parameter('enable_on_start', True)

        can_interface = self.get_parameter('can_interface').value
        self.speed = self.get_parameter('speed_percent').value
        enable_on_start = self.get_parameter('enable_on_start').value

        self.get_logger().info(f'Initializing Piper arm on {can_interface}...')

        # Initialize Piper arm
        try:
            self.piper = Piper(can_interface)
            self.piper.init()
            self.piper.connect()
            self.get_logger().info('Connected to Piper arm')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to arm: {e}')
            raise

        # Enable arm if requested
        self.arm_enabled = False
        if enable_on_start:
            self.enable_arm()

        # Joint name to index mapping (from URDF)
        self.joint_map = {
            'joint1': 0,
            'joint2': 1,
            'joint3': 2,
            'joint4': 3,
            'joint5': 4,
            'joint6': 5,
        }

        # Last commanded positions to avoid redundant commands
        self.last_positions = None
        self.position_threshold = 0.01  # radians - only send if change > this

        # Subscribe to joint states from simulation
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10
        )

        self.get_logger().info('Sim-to-Real bridge is ready! Move joints in RViz2 to control the arm.')
        self.get_logger().info(f'Speed: {self.speed}%')

    def enable_arm(self):
        """Enable all arm motors."""
        self.get_logger().info('Enabling arm motors...')
        try:
            attempts = 0
            while not self.piper.enable_arm() and attempts < 100:
                time.sleep(0.01)
                attempts += 1

            if attempts < 100:
                self.arm_enabled = True
                self.get_logger().info('Arm enabled successfully!')
            else:
                self.get_logger().warn('Arm enable timed out - may not be fully enabled')
                self.arm_enabled = True  # Try anyway
        except Exception as e:
            self.get_logger().error(f'Failed to enable arm: {e}')

    def disable_arm(self):
        """Disable all arm motors."""
        self.get_logger().info('Disabling arm motors...')
        try:
            self.piper.disable_arm()
            self.arm_enabled = False
            self.get_logger().info('Arm disabled')
        except Exception as e:
            self.get_logger().error(f'Failed to disable arm: {e}')

    def joint_state_callback(self, msg: JointState):
        """Handle incoming joint states from simulation."""
        if not self.arm_enabled:
            return

        # Build joint position array (6 joints)
        positions = [0.0] * 6

        for i, name in enumerate(msg.name):
            if name in self.joint_map:
                idx = self.joint_map[name]
                positions[idx] = msg.position[i]

        # Check if positions changed significantly
        if self.last_positions is not None:
            max_change = max(abs(positions[i] - self.last_positions[i]) for i in range(6))
            if max_change < self.position_threshold:
                return  # Skip if no significant change

        self.last_positions = positions.copy()

        # Send to physical arm
        try:
            joint_tuple = tuple(positions)
            self.piper.move_j(joint_tuple, self.speed)
            self.get_logger().debug(f'Sent joints: {[f"{p:.3f}" for p in positions]}')
        except Exception as e:
            self.get_logger().error(f'Failed to send joint command: {e}')

    def destroy_node(self):
        """Clean up when shutting down."""
        self.get_logger().info('Shutting down bridge...')
        if self.arm_enabled:
            self.disable_arm()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    print("=" * 60)
    print("  SIM-TO-REAL BRIDGE FOR PIPER ARM")
    print("=" * 60)
    print("\nThis will connect RViz2 simulation to the PHYSICAL arm!")
    print("The real arm will move when you move sliders in the GUI.\n")
    print("SAFETY: Make sure the arm has clearance to move!")
    print("Press Ctrl+C to stop.\n")

    try:
        bridge = SimToRealBridge()
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
