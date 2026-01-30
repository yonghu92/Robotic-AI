#!/usr/bin/env python3
"""
Test Charuco Board Corner Detection and Arm Movement

This script:
1. Detects the charuco board corners using the camera
2. Lets you move the arm to each corner to verify calibration
3. Shows the camera view with detected corners

Press 1-4 to move to corners, Q to quit
"""

import cv2
import numpy as np
import time
import sys

sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')

from piper_sdk import C_PiperInterface

class CharucoCornerTest:
    def __init__(self):
        # Camera setup
        self.cap = None
        self.camera_index = None

        # Charuco board parameters (6x8 squares, 3cm squares based on hand_eye_calibration.py)
        self.charuco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.charuco_board = cv2.aruco.CharucoBoard(
            (6, 8),   # 6x8 squares
            0.03,     # Square size in meters (3cm)
            0.023,    # Marker size in meters (2.3cm)
            self.charuco_dict
        )
        self.charuco_detector = cv2.aruco.CharucoDetector(self.charuco_board)

        # Camera intrinsics (will get from camera)
        self.camera_matrix = None
        self.dist_coeffs = np.zeros(5)

        # Detected corners in camera frame
        self.board_corners_3d = None  # 4 corners of the board

        # Arm setup
        self.piper = None
        self.arm_enabled = False

        # Movement settings
        self.move_speed = 30
        self.safe_height = 0.15  # 15cm above table
        self.touch_height = 0.05  # 5cm - to touch the corner

    def find_camera(self):
        """Find working camera"""
        print("Searching for camera...")
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"Found camera at index {i}")
                    cap.release()
                    return i
                cap.release()
        return None

    def connect_camera(self):
        """Connect to camera"""
        self.camera_index = self.find_camera()
        if self.camera_index is None:
            print("ERROR: No camera found")
            return False

        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Simple camera matrix estimate (adjust if needed)
        self.camera_matrix = np.array([
            [600, 0, 320],
            [0, 600, 240],
            [0, 0, 1]
        ], dtype=np.float32)

        return True

    def connect_arm(self):
        """Connect to Piper arm"""
        try:
            print("Connecting to arm...")
            self.piper = C_PiperInterface("can0")
            self.piper.ConnectPort()
            time.sleep(0.5)

            # Enable arm
            print("Enabling arm...")
            self.piper.EnableArm(7)
            time.sleep(0.5)

            # Set to end-effector control mode
            self.piper.MotionCtrl_2(0x01, 0x00, self.move_speed, 0x00)
            time.sleep(0.2)

            self.arm_enabled = True
            print("Arm connected and enabled!")
            return True
        except Exception as e:
            print(f"ERROR connecting arm: {e}")
            return False

    def detect_charuco(self, frame):
        """Detect charuco board and get corner positions"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect charuco
        charuco_corners, charuco_ids, marker_corners, marker_ids = \
            self.charuco_detector.detectBoard(gray)

        vis_frame = frame.copy()
        board_corners = None

        if charuco_corners is not None and len(charuco_corners) >= 4:
            # Draw detected corners
            cv2.aruco.drawDetectedCornersCharuco(vis_frame, charuco_corners, charuco_ids)

            # Estimate board pose
            success, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
                charuco_corners, charuco_ids, self.charuco_board,
                self.camera_matrix, self.dist_coeffs, None, None
            )

            if success:
                # Draw axes
                cv2.drawFrameAxes(vis_frame, self.camera_matrix, self.dist_coeffs,
                                  rvec, tvec, 0.05)

                # Calculate the 4 corners of the board in camera frame
                # Board is 6x8 squares, each 3cm = 18cm x 24cm total
                board_width = 6 * 0.03   # 18cm
                board_height = 8 * 0.03  # 24cm

                # Corner points in board frame (origin at corner 0)
                corners_board = np.array([
                    [0, 0, 0],                          # Corner 0 (origin)
                    [board_width, 0, 0],                # Corner 1
                    [board_width, board_height, 0],    # Corner 2
                    [0, board_height, 0]               # Corner 3
                ], dtype=np.float32)

                # Transform to camera frame
                R, _ = cv2.Rodrigues(rvec)
                board_corners = []
                for corner in corners_board:
                    corner_cam = R @ corner + tvec.flatten()
                    board_corners.append(corner_cam)

                board_corners = np.array(board_corners)

                # Draw corner numbers on image
                for i, corner in enumerate(corners_board):
                    # Project to image
                    img_pt, _ = cv2.projectPoints(corner.reshape(1, 3), rvec, tvec,
                                                   self.camera_matrix, self.dist_coeffs)
                    pt = tuple(img_pt[0, 0].astype(int))
                    cv2.circle(vis_frame, pt, 10, (0, 255, 255), -1)
                    cv2.putText(vis_frame, str(i+1), (pt[0]-5, pt[1]+5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        return vis_frame, board_corners

    def move_to_corner(self, corner_idx):
        """Move arm to a board corner"""
        if self.board_corners_3d is None:
            print("No board detected!")
            return

        if not self.arm_enabled:
            print("Arm not enabled!")
            return

        corner = self.board_corners_3d[corner_idx]
        print(f"\nMoving to corner {corner_idx + 1}")
        print(f"Camera frame position: x={corner[0]:.3f}, y={corner[1]:.3f}, z={corner[2]:.3f}")

        # Simple transform: camera coords to arm coords
        # This assumes camera is roughly above workspace looking down
        # You may need to adjust this based on your setup!

        # For eye-in-hand with camera on gripper pointing forward/down:
        # Camera X (right) -> Arm Y (left, so negate)
        # Camera Y (down) -> Arm Z (down, so negate)
        # Camera Z (forward/depth) -> Arm X (forward)

        # ADJUST THESE OFFSETS based on your camera mount!
        arm_x = corner[2]         # Camera depth -> arm forward
        arm_y = -corner[0]        # Camera X -> arm Y (negated)
        arm_z = self.safe_height  # Use safe height first

        print(f"Arm frame position: x={arm_x:.3f}, y={arm_y:.3f}, z={arm_z:.3f}")

        # Convert to arm units (micrometers for position)
        X = int(arm_x * 1_000_000)
        Y = int(arm_y * 1_000_000)
        Z = int(arm_z * 1_000_000)
        RX = int(180 * 1000)  # Gripper pointing down
        RY = 0
        RZ = 0

        print(f"Moving above corner {corner_idx + 1}...")
        self.piper.MotionCtrl_2(0x01, 0x00, self.move_speed, 0x00)
        self.piper.EndPoseCtrl(X, Y, Z, RX, RY, RZ)
        time.sleep(2.0)

        # Ask if user wants to lower
        response = input(f"Lower to touch corner? (y/n): ").strip().lower()
        if response == 'y':
            Z_touch = int(self.touch_height * 1_000_000)
            print("Lowering...")
            self.piper.EndPoseCtrl(X, Y, Z_touch, RX, RY, RZ)
            time.sleep(1.5)

            input("Press Enter to lift back up...")
            self.piper.EndPoseCtrl(X, Y, Z, RX, RY, RZ)
            time.sleep(1.0)

    def run(self):
        """Main loop"""
        print("=" * 60)
        print("  CHARUCO CORNER TEST")
        print("=" * 60)

        if not self.connect_camera():
            return

        arm_ok = self.connect_arm()
        if not arm_ok:
            print("Running without arm (visualization only)")

        print("\nControls:")
        print("  1-4 = Move to corner 1-4")
        print("  h   = Go home")
        print("  q   = Quit")
        print("=" * 60)

        cv2.namedWindow('Charuco Corner Test', cv2.WINDOW_NORMAL)

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                # Detect charuco and get corners
                vis_frame, corners = self.detect_charuco(frame)

                if corners is not None:
                    self.board_corners_3d = corners
                    status = "Board DETECTED - Press 1-4 to move to corners"
                    color = (0, 255, 0)
                else:
                    status = "Board NOT detected - show charuco board to camera"
                    color = (0, 0, 255)

                cv2.putText(vis_frame, status, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.putText(vis_frame, "1-4: corners | h: home | q: quit", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow('Charuco Corner Test', vis_frame)

                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    break
                elif key == ord('1'):
                    self.move_to_corner(0)
                elif key == ord('2'):
                    self.move_to_corner(1)
                elif key == ord('3'):
                    self.move_to_corner(2)
                elif key == ord('4'):
                    self.move_to_corner(3)
                elif key == ord('h'):
                    if self.arm_enabled:
                        print("\nGoing home...")
                        self.piper.MotionCtrl_2(0x01, 0x01, self.move_speed, 0x00)
                        home = [0, 0, 0, 0, 0, 0]
                        for _ in range(100):
                            self.piper.JointCtrl(*home)
                            time.sleep(0.02)
                        print("Home!")

        except KeyboardInterrupt:
            print("\nInterrupted")

        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            print("Done!")


if __name__ == "__main__":
    test = CharucoCornerTest()
    test.run()
