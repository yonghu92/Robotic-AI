#!/usr/bin/env python3
"""
Pick and Place Controller for Piper Arm

Picks up detected objects and places them at designated locations.

Usage:
1. Start the camera and detection nodes
2. Run this script
3. Press number keys (1-4) to pick objects by color
4. The arm will pick the object and place it at the designated location
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
import numpy as np
import time
import sys
import json
import threading

sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')

from piper_sdk import C_PiperInterface


class PickAndPlaceController(Node):
    def __init__(self):
        super().__init__('pick_and_place_controller')

        # === Define ALL settings FIRST ===

        # Speed settings
        self.move_speed = 30  # 30% speed

        # Gripper settings
        self.gripper_open = 70000    # 70 degrees open (in 0.001 deg units)
        self.gripper_closed = 10000  # 10 degrees closed
        self.gripper_effort = 1500   # 1.5 N·m torque

        # Home position (safe starting position) - in meters
        self.home_position = {
            'x': 0.25,   # 25cm forward
            'y': 0.0,    # centered
            'z': 0.25,   # 25cm height
            'rx': 180.0, # gripper pointing down
            'ry': 0.0,
            'rz': 0.0
        }

        # Place positions for different colors - in meters
        self.place_positions = {
            'red':    {'x': 0.20, 'y': -0.15, 'z': 0.10},
            'green':  {'x': 0.20, 'y': -0.05, 'z': 0.10},
            'yellow': {'x': 0.20, 'y': 0.05,  'z': 0.10},
            'purple': {'x': 0.20, 'y': 0.15,  'z': 0.10},
        }

        # Fixed heights for table workspace (meters) - since camera coords don't give correct Z
        self.approach_height = 0.15  # Height to approach (15cm above table)
        self.grasp_height = 0.04     # Height to grasp cube top (4cm - cube is ~3cm tall)
        self.table_height = 0.05     # Table surface relative to robot base

        # Current detected objects
        self.detected_objects = []
        self.object_base_position = None

        # State
        self.is_busy = False

        # === Now initialize arm interface ===
        self.piper = C_PiperInterface("can0")
        self.piper.ConnectPort()
        time.sleep(0.5)

        # Enable arm
        self.enable_arm()
        time.sleep(1.0)

        # Enable gripper
        self.enable_gripper()
        time.sleep(0.5)

        # Subscribers
        self.objects_sub = self.create_subscription(
            String, '/detected_objects', self.objects_callback, 10)
        self.point_sub = self.create_subscription(
            PointStamped, '/object_point_base', self.point_callback, 10)

        self.get_logger().info('Pick and Place Controller initialized')
        self.get_logger().info('Press 1=red, 2=green, 3=yellow, 4=purple to pick')

    def enable_arm(self):
        """Enable the arm motors"""
        self.get_logger().info('Enabling arm...')

        # Enable all motors (don't disable first - arm would fall!)
        self.piper.EnableArm(7)  # Enable all motors
        time.sleep(0.3)

        # Set to CAN command mode with position control
        self.piper.MotionCtrl_2(
            ctrl_mode=0x01,      # CAN command control
            move_mode=0x00,      # MOVE P (end-effector position)
            move_spd_rate_ctrl=self.move_speed
        )
        time.sleep(0.2)
        self.get_logger().info('Arm enabled')

    def enable_gripper(self):
        """Enable the gripper"""
        self.get_logger().info('Enabling gripper...')
        self.piper.GripperCtrl(
            gripper_angle=self.gripper_open,
            gripper_effort=self.gripper_effort,
            gripper_code=0x01  # Enable
        )
        time.sleep(0.5)
        self.get_logger().info('Gripper enabled and opened')

    def objects_callback(self, msg):
        """Store detected objects"""
        try:
            self.detected_objects = json.loads(msg.data)
        except:
            self.detected_objects = []

    def point_callback(self, msg):
        """Store object position in base frame"""
        self.object_base_position = {
            'x': msg.point.x,
            'y': msg.point.y,
            'z': msg.point.z
        }

    def move_to_position(self, x, y, z, rx=180.0, ry=0.0, rz=0.0):
        """
        Move arm to cartesian position.

        Args:
            x, y, z: Position in meters
            rx, ry, rz: Orientation in degrees
        """
        # Convert meters to 0.001mm units
        X = int(x * 1_000_000)
        Y = int(y * 1_000_000)
        Z = int(z * 1_000_000)

        # Convert degrees to 0.001 degree units
        RX = int(rx * 1000)
        RY = int(ry * 1000)
        RZ = int(rz * 1000)

        self.get_logger().info(f'Moving to: x={x:.3f}, y={y:.3f}, z={z:.3f}')
        self.piper.EndPoseCtrl(X, Y, Z, RX, RY, RZ)

    def open_gripper(self):
        """Open the gripper"""
        self.get_logger().info('Opening gripper')
        self.piper.GripperCtrl(
            gripper_angle=self.gripper_open,
            gripper_effort=self.gripper_effort,
            gripper_code=0x01
        )

    def close_gripper(self):
        """Close the gripper to grasp object"""
        self.get_logger().info('Closing gripper')
        self.piper.GripperCtrl(
            gripper_angle=self.gripper_closed,
            gripper_effort=self.gripper_effort,
            gripper_code=0x01
        )

    def go_home(self):
        """Move to home position using joint control (more reliable)"""
        self.get_logger().info('Moving to home position (joint control)...')

        # Switch to joint control mode
        self.piper.MotionCtrl_2(
            ctrl_mode=0x01,      # CAN command control
            move_mode=0x01,      # Joint control mode (not end-effector)
            move_spd_rate_ctrl=self.move_speed
        )
        time.sleep(0.1)

        # Move all joints to 0 (home position)
        home_joints = [0, 0, 0, 0, 0, 0]
        for i in range(100):
            self.piper.JointCtrl(*home_joints)
            time.sleep(0.02)

        # Switch back to end-effector control mode for pick operations
        time.sleep(0.5)
        self.piper.MotionCtrl_2(
            ctrl_mode=0x01,
            move_mode=0x00,      # End-effector position mode
            move_spd_rate_ctrl=self.move_speed
        )
        self.get_logger().info('Home position reached')

    def pick_object_by_color(self, color):
        """Pick up an object of the specified color"""
        if self.is_busy:
            self.get_logger().warn('Arm is busy!')
            return False

        # Find object of this color
        target = None
        for obj in self.detected_objects:
            if obj['color'] == color:
                target = obj
                break

        if target is None:
            self.get_logger().warn(f'No {color} object detected!')
            return False

        self.is_busy = True
        self.get_logger().info(f'Picking up {color} object...')

        try:
            # Get object position - X,Y from camera, but use fixed Z heights
            # Camera frame: X,Y roughly correspond to robot X,Y; Z is depth (not height!)
            obj_x = target['position'][0]
            obj_y = target['position'][1]
            cam_depth = target['position'][2]  # This is camera depth, not robot Z!

            self.get_logger().info(f'Object at camera coords: x={obj_x:.3f}, y={obj_y:.3f}, depth={cam_depth:.3f}')
            self.get_logger().info(f'Using fixed heights: approach={self.approach_height:.3f}, grasp={self.grasp_height:.3f}')

            # 1. Open gripper
            self.open_gripper()
            time.sleep(0.5)

            # 2. Move above object (use fixed approach height, not camera depth)
            self.move_to_position(obj_x, obj_y, self.approach_height)
            time.sleep(1.5)

            # 3. Move down to grasp (use fixed grasp height for cube top)
            self.move_to_position(obj_x, obj_y, self.grasp_height)
            time.sleep(1.5)

            # 4. Close gripper
            self.close_gripper()
            time.sleep(0.8)

            # 5. Lift up
            self.move_to_position(obj_x, obj_y, self.approach_height)
            time.sleep(1.5)

            # 6. Move to place position
            place_pos = self.place_positions.get(color, self.place_positions['red'])
            self.move_to_position(
                place_pos['x'],
                place_pos['y'],
                place_pos['z'] + self.approach_height
            )
            time.sleep(1.5)

            # 7. Move down to place
            self.move_to_position(
                place_pos['x'],
                place_pos['y'],
                place_pos['z']
            )
            time.sleep(1.0)

            # 8. Open gripper to release
            self.open_gripper()
            time.sleep(0.5)

            # 9. Lift up
            self.move_to_position(
                place_pos['x'],
                place_pos['y'],
                place_pos['z'] + self.approach_height
            )
            time.sleep(1.0)

            # 10. Return home
            self.go_home()
            time.sleep(1.5)

            self.get_logger().info(f'Successfully picked and placed {color} object!')
            return True

        except Exception as e:
            self.get_logger().error(f'Pick and place failed: {e}')
            return False

        finally:
            self.is_busy = False

    def shutdown(self):
        """Safely shutdown the arm - keeps motors enabled to prevent falling"""
        self.get_logger().info('Shutting down (arm stays enabled)...')
        self.open_gripper()
        time.sleep(0.5)
        # NOT disabling arm - it would fall due to gravity!


def main():
    rclpy.init()
    node = PickAndPlaceController()

    print('\n' + '='*60)
    print('  PICK AND PLACE CONTROLLER')
    print('='*60)
    print('\nControls:')
    print('  1 = Pick RED object')
    print('  2 = Pick GREEN object')
    print('  3 = Pick YELLOW object')
    print('  4 = Pick PURPLE object')
    print('  h = Go to home position')
    print('  o = Open gripper')
    print('  c = Close gripper')
    print('  q = Quit')
    print('='*60 + '\n')

    # Key mapping
    color_map = {
        '1': 'red',
        '2': 'green',
        '3': 'yellow',
        '4': 'purple'
    }

    # Input handling in separate thread
    running = True

    def input_thread():
        nonlocal running
        while running:
            try:
                key = input().strip().lower()
                if key == 'q':
                    running = False
                elif key == 'h':
                    node.go_home()
                elif key == 'o':
                    node.open_gripper()
                elif key == 'c':
                    node.close_gripper()
                elif key in color_map:
                    color = color_map[key]
                    threading.Thread(target=node.pick_object_by_color, args=(color,)).start()
            except EOFError:
                break

    input_th = threading.Thread(target=input_thread, daemon=True)
    input_th.start()

    try:
        while running and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass

    node.shutdown()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
