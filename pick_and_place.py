#!/usr/bin/env python3
"""
Pick and Place with Object Detection
Combines camera-based object detection with Piper arm control
"""

import cv2
import numpy as np
import time
import sys

class PickAndPlace:
    def __init__(self, can_interface="can0"):
        self.can_interface = can_interface
        self.piper = None
        self.arm_enabled = False
        self.cap = None
        self.camera_index = None

        # Arm home position (mm)
        self.home_pos = [200.0, 0.0, 250.0, 0.0, 90.0, 0.0]  # X, Y, Z, RX, RY, RZ

        # Pick position offset (adjust based on camera-arm calibration)
        self.camera_offset = [50.0, 0.0, 150.0]  # X, Y, Z offset from camera to arm base

        # Heights for pick operation (mm)
        self.approach_height = 100.0  # Height above object to approach
        self.pick_height = 30.0       # Height to pick (lower to grab)
        self.lift_height = 150.0      # Height to lift after picking

        # Place position (mm)
        self.place_pos = [200.0, 150.0, 100.0]  # Where to place objects

        # Detection settings
        self.min_area = 1000
        self.max_area = 50000
        self.color_ranges = {
            'red': ([0, 100, 100], [10, 255, 255]),
            'red2': ([160, 100, 100], [180, 255, 255]),
            'blue': ([100, 100, 100], [130, 255, 255]),
            'green': ([40, 100, 100], [80, 255, 255]),
            'yellow': ([20, 100, 100], [40, 255, 255]),
            'white': ([0, 0, 200], [180, 30, 255]),  # Low saturation, high brightness
        }

        # Camera parameters
        self.fx, self.fy = 600, 600
        self.cx, self.cy = 320, 240
        self.estimated_depth = 300  # mm

    def connect_arm(self):
        """Connect to Piper arm"""
        try:
            from piper_sdk import C_PiperInterface_V2
            print(f"Connecting to Piper arm on {self.can_interface}...")

            self.piper = C_PiperInterface_V2(self.can_interface)
            self.piper.ConnectPort()

            print("Enabling arm...")
            timeout = time.time() + 10
            while not self.piper.EnablePiper():
                if time.time() > timeout:
                    print("ERROR: Timeout enabling arm")
                    return False
                time.sleep(0.01)

            self.arm_enabled = True
            print("Arm enabled!")
            return True

        except Exception as e:
            print(f"ERROR connecting to arm: {e}")
            return False

    def find_camera(self):
        """Find working camera"""
        import warnings
        import os
        # Suppress OpenCV warnings about missing cameras
        os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
        
        for i in range(10):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            cap.release()
                            return i
                        cap.release()
            except Exception:
                continue
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
        print(f"Camera connected at index {self.camera_index}")
        return True

    def move_arm(self, x, y, z, rx=0, ry=90, rz=0, speed=50):
        """Move arm to position (mm)"""
        if not self.arm_enabled:
            print(f"[SIM] Move to: X={x:.0f}, Y={y:.0f}, Z={z:.0f}")
            return

        factor = 1000
        self.piper.MotionCtrl_2(0x01, 0x00, speed, 0x00)
        self.piper.EndPoseCtrl(
            int(x * factor), int(y * factor), int(z * factor),
            int(rx * factor), int(ry * factor), int(rz * factor)
        )
        time.sleep(0.5)  # Wait for movement

    def control_gripper(self, opening_mm, speed=1000):
        """Control gripper (0=closed, 70=fully open)"""
        if not self.arm_enabled:
            print(f"[SIM] Gripper: {opening_mm:.0f}mm")
            return

        opening = int(np.clip(opening_mm, 0, 70) * 1000)
        self.piper.GripperCtrl(opening, speed, 0x01, 0)
        time.sleep(0.3)

    def go_home(self):
        """Move arm to home position"""
        print("Moving to home position...")
        self.move_arm(*self.home_pos[:3])
        self.control_gripper(70)  # Open gripper

    def detect_objects(self, frame, target_color=None):
        """Detect colored objects in frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        objects = []

        colors_to_check = [target_color] if target_color else self.color_ranges.keys()

        for color in colors_to_check:
            if color not in self.color_ranges or color == 'red2':
                continue

            lower, upper = self.color_ranges[color]
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))

            if color == 'red':
                lower2, upper2 = self.color_ranges['red2']
                mask2 = cv2.inRange(hsv, np.array(lower2), np.array(upper2))
                mask = cv2.bitwise_or(mask, mask2)
            elif color == 'white':
                # White detection: low saturation, high brightness
                # Additional filtering to avoid shadows and reflections
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Ensure brightness is high enough (avoid dark areas)
                brightness_mask = gray > 200
                mask = cv2.bitwise_and(mask, brightness_mask.astype(np.uint8) * 255)

            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if self.min_area < area < self.max_area:
                    rect = cv2.minAreaRect(contour)
                    center = rect[0]
                    angle = rect[2]

                    # Convert to 3D
                    x_3d = (center[0] - self.cx) * self.estimated_depth / self.fx
                    y_3d = (center[1] - self.cy) * self.estimated_depth / self.fy

                    objects.append({
                        'color': color,
                        'center_2d': (int(center[0]), int(center[1])),
                        'center_3d': (x_3d, y_3d, self.estimated_depth),
                        'angle': angle,
                        'area': area,
                        'contour': contour
                    })

        # Sort by area (largest first)
        objects.sort(key=lambda x: x['area'], reverse=True)
        return objects

    def camera_to_arm_coords(self, cam_x, cam_y, cam_z):
        """Convert camera coordinates to arm coordinates"""
        # This needs calibration for your specific setup
        # Basic transformation (adjust offsets based on your camera mount)
        arm_x = self.camera_offset[0] + cam_z * 0.5  # Forward
        arm_y = self.camera_offset[1] - cam_x * 0.5  # Left/Right
        arm_z = self.camera_offset[2] - cam_y * 0.3  # Height

        return arm_x, arm_y, arm_z

    def pick_object(self, obj):
        """Execute pick sequence for detected object"""
        cam_pos = obj['center_3d']
        arm_x, arm_y, arm_z = self.camera_to_arm_coords(*cam_pos)

        print(f"\nPicking {obj['color']} object at arm coords: ({arm_x:.0f}, {arm_y:.0f}, {arm_z:.0f})")

        # 1. Open gripper
        print("  Opening gripper...")
        self.control_gripper(70)
        time.sleep(0.3)

        # 2. Move above object
        print(f"  Moving above object...")
        self.move_arm(arm_x, arm_y, arm_z + self.approach_height)
        time.sleep(0.5)

        # 3. Lower to pick height
        print(f"  Lowering to pick...")
        self.move_arm(arm_x, arm_y, self.pick_height)
        time.sleep(0.5)

        # 4. Close gripper
        print("  Closing gripper...")
        self.control_gripper(10)  # Close to grip
        time.sleep(0.5)

        # 5. Lift
        print(f"  Lifting...")
        self.move_arm(arm_x, arm_y, self.lift_height)
        time.sleep(0.5)

        print("  Pick complete!")
        return True

    def place_object(self):
        """Execute place sequence"""
        print(f"\nPlacing object at ({self.place_pos[0]:.0f}, {self.place_pos[1]:.0f}, {self.place_pos[2]:.0f})")

        # 1. Move above place position
        print("  Moving above place position...")
        self.move_arm(self.place_pos[0], self.place_pos[1], self.lift_height)
        time.sleep(0.5)

        # 2. Lower
        print("  Lowering...")
        self.move_arm(self.place_pos[0], self.place_pos[1], self.place_pos[2])
        time.sleep(0.5)

        # 3. Open gripper
        print("  Releasing...")
        self.control_gripper(70)
        time.sleep(0.3)

        # 4. Lift away
        print("  Lifting away...")
        self.move_arm(self.place_pos[0], self.place_pos[1], self.lift_height)
        time.sleep(0.3)

        print("  Place complete!")

    def run(self, target_color=None, auto_pick=False):
        """Main pick and place loop"""
        print("=" * 60)
        print("PICK AND PLACE")
        print("=" * 60)

        # Connect to arm
        arm_ok = self.connect_arm()
        if not arm_ok:
            print("WARNING: Running in simulation mode (no arm)")

        # Connect to camera
        if not self.connect_camera():
            return

        # Go to home
        self.go_home()

        print("\n" + "=" * 60)
        print("CONTROLS:")
        print("  p - Pick nearest object")
        print("  d - Place object")
        print("  h - Go home")
        print("  r - Pick RED object")
        print("  b - Pick BLUE object")
        print("  g - Pick GREEN object")
        print("  y - Pick YELLOW object")
        print("  w - Pick WHITE object")
        print("  a - Toggle auto-pick mode")
        print("  q - Quit")
        print("=" * 60 + "\n")

        auto_mode = auto_pick
        last_pick_time = 0

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                # Detect objects
                objects = self.detect_objects(frame, target_color)

                # Draw detections
                output = frame.copy()
                for obj in objects:
                    cv2.drawContours(output, [obj['contour']], -1, (0, 255, 0), 2)
                    cx, cy = obj['center_2d']
                    cv2.circle(output, (cx, cy), 5, (0, 0, 255), -1)

                    label = f"{obj['color']} ({obj['center_3d'][0]:.0f}, {obj['center_3d'][1]:.0f})"
                    cv2.putText(output, label, (cx-50, cy-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

                # Status
                status = f"Objects: {len(objects)} | Auto: {'ON' if auto_mode else 'OFF'}"
                cv2.putText(output, status, (10, 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                if objects:
                    best = objects[0]
                    cv2.putText(output, f"Target: {best['color']}", (10, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                cv2.imshow('Pick and Place', output)

                # Auto pick mode
                if auto_mode and objects and (time.time() - last_pick_time > 5):
                    print("\n[AUTO] Picking detected object...")
                    self.pick_object(objects[0])
                    self.place_object()
                    self.go_home()
                    last_pick_time = time.time()

                # Handle key presses
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    break
                elif key == ord('p') and objects:
                    self.pick_object(objects[0])
                elif key == ord('d'):
                    self.place_object()
                elif key == ord('h'):
                    self.go_home()
                elif key == ord('a'):
                    auto_mode = not auto_mode
                    print(f"Auto mode: {'ON' if auto_mode else 'OFF'}")
                elif key == ord('r'):
                    red_objs = [o for o in objects if o['color'] == 'red']
                    if red_objs:
                        self.pick_object(red_objs[0])
                elif key == ord('b'):
                    blue_objs = [o for o in objects if o['color'] == 'blue']
                    if blue_objs:
                        self.pick_object(blue_objs[0])
                elif key == ord('g'):
                    green_objs = [o for o in objects if o['color'] == 'green']
                    if green_objs:
                        self.pick_object(green_objs[0])
                elif key == ord('y'):
                    yellow_objs = [o for o in objects if o['color'] == 'yellow']
                    if yellow_objs:
                        self.pick_object(yellow_objs[0])
                elif key == ord('w'):
                    white_objs = [o for o in objects if o['color'] == 'white']
                    if white_objs:
                        self.pick_object(white_objs[0])

        except KeyboardInterrupt:
            print("\nInterrupted")

        finally:
            print("\nReturning home...")
            self.go_home()
            self.cap.release()
            cv2.destroyAllWindows()
            print("Done!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pick and Place')
    parser.add_argument('--color', type=str, default=None,
                       help='Target color (red, blue, green, yellow, white)')
    parser.add_argument('--auto', action='store_true',
                       help='Enable auto-pick mode')
    parser.add_argument('--can', type=str, default='can0',
                       help='CAN interface')
    args = parser.parse_args()

    pp = PickAndPlace(can_interface=args.can)
    pp.run(target_color=args.color, auto_pick=args.auto)


if __name__ == "__main__":
    main()
