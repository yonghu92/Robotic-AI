#!/usr/bin/env python3
"""
Piper Robot URDF Visualization and Kinematics Demo
Uses PyBullet for visualization and simulation
"""

import pybullet as p
import pybullet_data
import time
import numpy as np
import math

class PiperVisualizer:
    def __init__(self, urdf_path=None):
        if urdf_path is None:
            urdf_path = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper_local.urdf'

        self.urdf_path = urdf_path
        self.robot_id = None
        self.joint_indices = []  # Movable joint indices
        self.joint_names = []
        self.joint_limits = []

    def connect(self, gui=True):
        """Connect to PyBullet"""
        if gui:
            self.physics_client = p.connect(p.GUI)
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        else:
            self.physics_client = p.connect(p.DIRECT)

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)

        # Load ground
        p.loadURDF('plane.urdf')

        # Load robot
        self.robot_id = p.loadURDF(
            self.urdf_path,
            [0, 0, 0],
            useFixedBase=True
        )

        # Get joint info
        self._get_joint_info()

        print(f"Loaded Piper robot with {len(self.joint_indices)} movable joints:")
        for i, (idx, name, limits) in enumerate(zip(self.joint_indices, self.joint_names, self.joint_limits)):
            print(f"  {i}: {name} (joint {idx}), limits: [{limits[0]:.2f}, {limits[1]:.2f}] rad")

        return self

    def _get_joint_info(self):
        """Get movable joint information"""
        num_joints = p.getNumJoints(self.robot_id)

        for i in range(num_joints):
            joint_info = p.getJointInfo(self.robot_id, i)
            joint_type = joint_info[2]

            # Only include revolute (0) and prismatic (1) joints
            if joint_type in [0, 1]:
                self.joint_indices.append(i)
                self.joint_names.append(joint_info[1].decode('utf-8'))
                self.joint_limits.append((joint_info[8], joint_info[9]))

    def set_joint_positions(self, positions):
        """Set joint positions directly"""
        for i, (idx, pos) in enumerate(zip(self.joint_indices, positions)):
            if i < len(positions):
                p.resetJointState(self.robot_id, idx, pos)

    def get_joint_positions(self):
        """Get current joint positions"""
        positions = []
        for idx in self.joint_indices:
            state = p.getJointState(self.robot_id, idx)
            positions.append(state[0])
        return positions

    def get_end_effector_pose(self):
        """Get end effector (link6) position and orientation"""
        # Find link6 index
        link_idx = -1
        for i in range(p.getNumJoints(self.robot_id)):
            info = p.getJointInfo(self.robot_id, i)
            if info[12].decode('utf-8') == 'link6':
                link_idx = i
                break

        if link_idx >= 0:
            state = p.getLinkState(self.robot_id, link_idx)
            pos = state[0]  # World position
            orn = state[1]  # World orientation (quaternion)
            return pos, orn
        return None, None

    def inverse_kinematics(self, target_pos, target_orn=None):
        """Calculate inverse kinematics for target position"""
        # Find end effector link
        end_effector_idx = 6  # link6 joint index

        if target_orn is None:
            joint_positions = p.calculateInverseKinematics(
                self.robot_id,
                end_effector_idx,
                target_pos
            )
        else:
            joint_positions = p.calculateInverseKinematics(
                self.robot_id,
                end_effector_idx,
                target_pos,
                target_orn
            )

        return joint_positions[:6]  # Return only arm joints (not gripper)

    def run_demo(self):
        """Run interactive demo with sliders"""
        print("\n" + "="*60)
        print("PIPER URDF VISUALIZATION")
        print("="*60)
        print("Use sliders to control joints")
        print("Press Ctrl+C or close window to exit")
        print("="*60 + "\n")

        # Create sliders for each joint (only arm joints, not gripper)
        sliders = []
        for i, (name, limits) in enumerate(zip(self.joint_names[:6], self.joint_limits[:6])):
            slider = p.addUserDebugParameter(
                name,
                limits[0],
                limits[1],
                0  # Initial value
            )
            sliders.append(slider)

        # Add gripper slider
        gripper_slider = p.addUserDebugParameter("Gripper", 0, 1, 0.5)

        try:
            while p.isConnected():
                # Read slider values
                positions = []
                try:
                    for i, slider in enumerate(sliders):
                        val = p.readUserDebugParameter(slider)
                        positions.append(val)
                except:
                    break

                # Apply to robot
                for i, (idx, pos) in enumerate(zip(self.joint_indices[:6], positions[:6])):
                    p.setJointMotorControl2(
                        self.robot_id, idx,
                        p.POSITION_CONTROL,
                        targetPosition=pos
                    )

                # Gripper control
                try:
                    gripper_val = p.readUserDebugParameter(gripper_slider)
                    gripper_pos = gripper_val * 0.04  # Max opening 0.04m

                    # Joint 7 and 8 are gripper fingers
                    if len(self.joint_indices) > 6:
                        p.setJointMotorControl2(
                            self.robot_id, self.joint_indices[6],
                            p.POSITION_CONTROL,
                            targetPosition=gripper_pos
                        )
                    if len(self.joint_indices) > 7:
                        p.setJointMotorControl2(
                            self.robot_id, self.joint_indices[7],
                            p.POSITION_CONTROL,
                            targetPosition=-gripper_pos
                        )
                except:
                    pass

                p.stepSimulation()
                time.sleep(1/240)

        except KeyboardInterrupt:
            print("\nExiting...")

    def disconnect(self):
        """Disconnect from PyBullet"""
        p.disconnect()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Piper URDF Visualization')
    parser.add_argument('--no-gui', action='store_true', help='Run without GUI')
    args = parser.parse_args()

    viz = PiperVisualizer()
    viz.connect(gui=not args.no_gui)

    if not args.no_gui:
        viz.run_demo()
    else:
        # Print joint info and exit
        print("\nTesting IK...")
        target = [0.2, 0.1, 0.3]
        joints = viz.inverse_kinematics(target)
        print(f"IK for target {target}: {joints}")

    viz.disconnect()


if __name__ == "__main__":
    main()
