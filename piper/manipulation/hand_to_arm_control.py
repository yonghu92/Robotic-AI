#!/usr/bin/env python3
"""
Hand Pose to Piper Arm Control
Controls the Piper robotic arm using hand gestures detected via RealSense camera

Usage:
    python3 hand_to_arm_control.py

Controls:
    - Move hand to move arm end effector
    - Pinch (thumb + index finger) to close gripper
    - Open hand to open gripper
    - Make FIST for 3 seconds to calibrate home position
    - Press 'q' to quit
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import sys

# MediaPipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

class HandArmController:
    def __init__(self, can_interface="can0", camera_index=6):
        self.can_interface = can_interface
        self.camera_index = camera_index

        # Arm control state
        self.piper = None
        self.arm_enabled = False

        # Hand tracking state
        self.home_position = None  # Hand home position (calibrated)
        self.calibrating = False
        self.calibration_start = None
        self.calibration_duration = 3.0  # seconds to hold fist

        # Arm position limits (mm)
        self.arm_home = [200.0, 0.0, 300.0, 0.0, 90.0, 0.0]  # X, Y, Z, RX, RY, RZ
        self.arm_range = [200.0, 200.0, 200.0, 45.0, 45.0, 45.0]  # Larger movement range

        # Mapping scale (hand movement in pixels -> arm movement in mm)
        self.scale_x = 0.6    # mm per pixel for left/right
        self.scale_y = 0.6    # mm per pixel for up/down
        self.scale_z = 3.0    # mm per depth unit for forward/back

        # Smoothing filter
        self.smoothing = 0.7  # Higher = more responsive (less smoothing)
        self.last_arm_pos = None

        # Gripper state
        self.gripper_open = 70000  # 70mm open
        self.gripper_closed = 5000  # 5mm closed

    def connect_arm(self):
        """Connect to Piper arm via CAN"""
        try:
            from piper_sdk import C_PiperInterface_V2
            print(f"Connecting to Piper arm on {self.can_interface}...")

            self.piper = C_PiperInterface_V2(self.can_interface)
            self.piper.ConnectPort()

            print("Enabling arm...")
            timeout = time.time() + 10  # 10 second timeout
            while not self.piper.EnablePiper():
                if time.time() > timeout:
                    print("ERROR: Timeout enabling arm")
                    return False
                time.sleep(0.01)

            self.arm_enabled = True
            print("Arm enabled successfully!")

            # Move to home position
            print("Moving to home position...")
            self.move_arm_to(self.arm_home)
            time.sleep(2)

            return True

        except Exception as e:
            print(f"ERROR connecting to arm: {e}")
            return False

    def move_arm_to(self, position):
        """Move arm to position [X, Y, Z, RX, RY, RZ] in mm and degrees"""
        if not self.arm_enabled or self.piper is None:
            return

        factor = 1000  # SDK uses micrometers
        X = int(position[0] * factor)
        Y = int(position[1] * factor)
        Z = int(position[2] * factor)
        RX = int(position[3] * factor)
        RY = int(position[4] * factor)
        RZ = int(position[5] * factor)

        # Set motion mode and send position
        self.piper.MotionCtrl_2(0x01, 0x00, 50, 0x00)  # Cartesian mode, 50% speed
        self.piper.EndPoseCtrl(X, Y, Z, RX, RY, RZ)

    def control_gripper(self, opening_mm):
        """Control gripper opening in mm (0-70)"""
        if not self.arm_enabled or self.piper is None:
            return

        opening = int(np.clip(opening_mm, 0, 70) * 1000)  # Convert to micrometers
        self.piper.GripperCtrl(opening, 1000, 0x01, 0)

    def get_finger_distance(self, hand_landmarks):
        """Get distance between thumb tip and index finger tip"""
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]

        distance = np.sqrt(
            (thumb_tip.x - index_tip.x)**2 +
            (thumb_tip.y - index_tip.y)**2
        )
        return distance

    def is_hand_stable(self, hand_pos):
        """Check if hand position is stable (not moving much)"""
        if not hasattr(self, 'last_positions'):
            self.last_positions = []

        self.last_positions.append(hand_pos.copy())

        # Keep last 15 frames (~0.5 sec at 30fps)
        if len(self.last_positions) > 15:
            self.last_positions.pop(0)

        if len(self.last_positions) < 10:
            return False

        # Check if positions are stable (low variance)
        positions = np.array(self.last_positions)
        variance = np.var(positions[:, :2], axis=0).sum()  # X,Y variance

        return variance < 500  # Low movement = stable

    def get_hand_center(self, hand_landmarks, frame_width, frame_height):
        """Get the wrist position in pixel coordinates - most stable point"""
        # Use wrist as the primary tracking point (most stable)
        wrist = hand_landmarks.landmark[0]

        center_x = wrist.x * frame_width
        center_y = wrist.y * frame_height

        # Use wrist z-coordinate directly (normalized depth from MediaPipe)
        # Closer to camera = more negative z value
        center_z = wrist.z * 100  # Scale for better range

        return np.array([center_x, center_y, center_z])

    def map_hand_to_arm(self, hand_pos):
        """Map hand position to arm position - intuitive 1:1 mapping"""
        if self.home_position is None:
            return None

        # Calculate offset from home position
        offset = hand_pos - self.home_position

        # Direct intuitive mapping:
        # Hand moves LEFT (negative X in image) -> Arm moves LEFT (positive Y)
        # Hand moves RIGHT (positive X in image) -> Arm moves RIGHT (negative Y)
        # Hand moves UP (negative Y in image) -> Arm moves UP (positive Z)
        # Hand moves DOWN (positive Y in image) -> Arm moves DOWN (negative Z)
        # Hand moves FORWARD (negative Z) -> Arm moves FORWARD (positive X)
        # Hand moves BACK (positive Z) -> Arm moves BACK (negative X)

        arm_offset = np.array([
            -offset[2] * self.scale_z,     # X: forward/back (inverted)
            -offset[0] * self.scale_x,     # Y: left/right (inverted for mirror)
            -offset[1] * self.scale_y,     # Z: up/down (inverted - image Y is flipped)
            0, 0, 0                         # Keep orientation fixed for now
        ])

        # Add to home position
        target = np.array(self.arm_home) + arm_offset

        # Clamp to safe range
        for i in range(3):
            target[i] = np.clip(
                target[i],
                self.arm_home[i] - self.arm_range[i],
                self.arm_home[i] + self.arm_range[i]
            )

        # Apply smoothing (blend with previous position)
        if self.last_arm_pos is not None:
            target = self.smoothing * target + (1 - self.smoothing) * self.last_arm_pos

        self.last_arm_pos = target
        return target

    def find_working_camera(self):
        """Find a working camera device"""
        print("Searching for working camera...")
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"  Found working camera at index {i}: {width}x{height}")
                    cap.release()
                    return i
                cap.release()
        return None

    def run(self, display=True, arm_control=True):
        """Main control loop"""
        print("=" * 60)
        print("HAND TO ARM CONTROL")
        print("=" * 60)

        # Connect to arm if enabled
        if arm_control:
            if not self.connect_arm():
                print("\nWARNING: Running without arm control (simulation mode)")
                arm_control = False
        else:
            print("Running in simulation mode (no arm control)")

        # Find working camera
        camera_idx = self.find_working_camera()
        if camera_idx is None:
            print("ERROR: No working camera found")
            return

        # Open camera
        print(f"\nOpening camera {camera_idx}...")
        cap = cv2.VideoCapture(camera_idx)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print("ERROR: Cannot open camera")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera opened: {width}x{height}")

        # Initialize hand detection - very low thresholds for robust tracking
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.2,
            min_tracking_confidence=0.1
        )

        print("\n" + "=" * 60)
        print("CONTROLS:")
        print("  - Hold hand STILL for 3 seconds to calibrate")
        print("  - Move hand to control arm")
        print("  - Pinch thumb+index to close gripper")
        print("  - Press 'q' to quit")
        print("=" * 60 + "\n")

        frame_count = 0
        start_time = time.time()

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                frame_count += 1
                frame = cv2.flip(frame, 1)  # Mirror for intuitive control

                # Process with MediaPipe
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                status_text = "No hand detected"
                gripper_text = ""

                if results.multi_hand_landmarks:
                    hand_landmarks = results.multi_hand_landmarks[0]

                    # Draw landmarks
                    if display:
                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )

                    # Get hand position
                    hand_pos = self.get_hand_center(hand_landmarks, width, height)

                    # Check if hand is stable for calibration
                    hand_stable = self.is_hand_stable(hand_pos)

                    if self.home_position is None:
                        # Need to calibrate first
                        if hand_stable:
                            if not self.calibrating:
                                self.calibrating = True
                                self.calibration_start = time.time()
                                print("Hand detected - hold still to calibrate...")

                            elapsed = time.time() - self.calibration_start
                            remaining = self.calibration_duration - elapsed

                            if remaining > 0:
                                status_text = f"CALIBRATING... {remaining:.1f}s"
                            else:
                                # Calibration complete
                                self.home_position = hand_pos.copy()
                                self.calibrating = False
                                self.last_positions = []  # Reset
                                print(f"HOME CALIBRATED at {hand_pos}")
                                status_text = "CALIBRATED! Move hand to control"
                        else:
                            self.calibrating = False
                            status_text = "Hold hand STILL to calibrate..."

                    if self.home_position is not None:
                            # Map hand to arm position
                            arm_target = self.map_hand_to_arm(hand_pos)

                            if arm_target is not None:
                                status_text = f"Arm: X={arm_target[0]:.0f} Y={arm_target[1]:.0f} Z={arm_target[2]:.0f}"

                                # Control arm
                                if arm_control:
                                    self.move_arm_to(arm_target)

                            # Gripper control based on pinch
                            finger_dist = self.get_finger_distance(hand_landmarks)
                            gripper_opening = np.clip(finger_dist * 500, 5, 70)  # 5-70mm
                            gripper_text = f"Gripper: {gripper_opening:.0f}mm"

                            if arm_control:
                                self.control_gripper(gripper_opening)

                # Display
                if display:
                    # Status overlay
                    cv2.putText(frame, status_text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    if gripper_text:
                        cv2.putText(frame, gripper_text, (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                    # Calibration indicator
                    if self.home_position is not None:
                        cv2.circle(frame, (width//2, height//2), 10, (0, 255, 0), 2)

                    # FPS
                    fps = frame_count / (time.time() - start_time)
                    cv2.putText(frame, f"FPS: {fps:.1f}", (width - 100, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                    cv2.imshow('Hand to Arm Control', frame)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("\nUser quit")
                        break

                time.sleep(0.01)  # Small delay to not overload arm

        except KeyboardInterrupt:
            print("\nInterrupted")

        finally:
            cap.release()
            hands.close()
            if display:
                cv2.destroyAllWindows()

            # Return arm to home
            if arm_control and self.arm_enabled:
                print("Returning arm to home position...")
                self.move_arm_to(self.arm_home)
                self.control_gripper(70)  # Open gripper

            print("Done!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Hand to Arm Control')
    parser.add_argument('--no-arm', action='store_true', help='Run without arm control (simulation)')
    parser.add_argument('--no-display', action='store_true', help='Run without display')
    parser.add_argument('--can', default='can0', help='CAN interface (default: can0)')
    parser.add_argument('--camera', type=int, default=6, help='Camera index (default: 6)')
    args = parser.parse_args()

    controller = HandArmController(
        can_interface=args.can,
        camera_index=args.camera
    )

    controller.run(
        display=not args.no_display,
        arm_control=not args.no_arm
    )


if __name__ == "__main__":
    main()
