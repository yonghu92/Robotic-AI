#!/usr/bin/env python3
"""
Object and Line Detection for Pick and Place
Uses RealSense camera to detect cubes, objects, and lines
Returns 3D positions for robotic arm pick and place operations
"""

import cv2
import numpy as np
import time
import sys

class ObjectDetector:
    def __init__(self, camera_index=None):
        self.camera_index = camera_index
        self.cap = None

        # Detection parameters
        self.min_area = 1000  # Minimum contour area for objects
        self.max_area = 50000  # Maximum contour area

        # Color ranges for detection (HSV)
        self.color_ranges = {
            'red': ([0, 100, 100], [10, 255, 255]),
            'red2': ([160, 100, 100], [180, 255, 255]),  # Red wraps around
            'blue': ([100, 100, 100], [130, 255, 255]),
            'green': ([40, 100, 100], [80, 255, 255]),
            'yellow': ([20, 100, 100], [40, 255, 255]),
            'orange': ([10, 100, 100], [20, 255, 255]),
        }

        # Camera parameters (approximate for RealSense 455)
        self.fx = 600  # Focal length x
        self.fy = 600  # Focal length y
        self.cx = 320  # Principal point x
        self.cy = 240  # Principal point y

        # Estimated depth (mm) - will be refined with actual depth sensor
        self.estimated_depth = 400  # Default depth estimate

    def find_camera(self):
        """Find working camera"""
        import warnings
        import os
        # Suppress OpenCV warnings about missing cameras
        os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
        
        print("Searching for camera...")
        for i in range(10):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        # Set timeout for read
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            print(f"  Found camera at index {i}")
                            cap.release()
                            return i
                        cap.release()
            except Exception:
                continue
        print("  No camera found!")
        return None

    def connect(self):
        """Connect to camera"""
        if self.camera_index is None:
            self.camera_index = self.find_camera()

        if self.camera_index is None:
            print("ERROR: No camera found")
            return False

        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(f"ERROR: Could not open camera at index {self.camera_index}")
                return False
            
            # Set properties with timeout
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to avoid lag
            
            # Test if we can actually read a frame
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                print(f"ERROR: Camera opened but cannot read frames")
                self.cap.release()
                return False
            
            return True
        except Exception as e:
            print(f"ERROR: Exception connecting to camera: {e}")
            return False

    def disconnect(self):
        """Disconnect camera"""
        if self.cap:
            self.cap.release()

    def detect_colored_objects(self, frame, colors=None):
        """Detect objects by color"""
        if colors is None:
            colors = ['red', 'blue', 'green', 'yellow']

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detected_objects = []

        for color in colors:
            if color not in self.color_ranges:
                continue

            lower, upper = self.color_ranges[color]
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))

            # Handle red color (wraps around)
            if color == 'red' and 'red2' in self.color_ranges:
                lower2, upper2 = self.color_ranges['red2']
                mask2 = cv2.inRange(hsv, np.array(lower2), np.array(upper2))
                mask = cv2.bitwise_or(mask, mask2)

            # Clean up mask
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if self.min_area < area < self.max_area:
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)

                    # Get rotated rectangle for orientation
                    rect = cv2.minAreaRect(contour)
                    center = rect[0]
                    size = rect[1]
                    angle = rect[2]

                    # Determine shape
                    shape = self.classify_shape(contour)

                    # Estimate 3D position
                    pos_3d = self.pixel_to_3d(center[0], center[1], self.estimated_depth)

                    detected_objects.append({
                        'color': color,
                        'shape': shape,
                        'center_2d': (int(center[0]), int(center[1])),
                        'center_3d': pos_3d,
                        'size': (int(size[0]), int(size[1])),
                        'angle': angle,
                        'area': area,
                        'contour': contour,
                        'bbox': (x, y, w, h)
                    })

        return detected_objects

    def classify_shape(self, contour):
        """Classify contour shape"""
        # Approximate contour
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

        num_vertices = len(approx)

        if num_vertices == 3:
            return "triangle"
        elif num_vertices == 4:
            # Check if square or rectangle
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            if 0.85 <= aspect_ratio <= 1.15:
                return "square"
            else:
                return "rectangle"
        elif num_vertices == 5:
            return "pentagon"
        elif num_vertices > 5:
            # Check circularity
            area = cv2.contourArea(contour)
            circularity = 4 * np.pi * area / (peri * peri)
            if circularity > 0.8:
                return "circle"
            else:
                return "polygon"

        return "unknown"

    def detect_lines(self, frame):
        """Detect lines using Hough transform"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Dilate edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Hough line detection
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=50,
            maxLineGap=10
        )

        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Calculate line properties
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                angle = np.degrees(np.arctan2(y2-y1, x2-x1))
                center = ((x1+x2)//2, (y1+y2)//2)

                detected_lines.append({
                    'start': (x1, y1),
                    'end': (x2, y2),
                    'center': center,
                    'length': length,
                    'angle': angle
                })

        return detected_lines

    def detect_edges_and_corners(self, frame):
        """Detect edges and corners for cube orientation"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Harris corner detection
        gray_float = np.float32(gray)
        corners = cv2.cornerHarris(gray_float, 2, 3, 0.04)
        corners = cv2.dilate(corners, None)

        # Get corner points
        threshold = 0.01 * corners.max()
        corner_points = np.where(corners > threshold)
        corner_coords = list(zip(corner_points[1], corner_points[0]))  # (x, y)

        return corner_coords

    def pixel_to_3d(self, u, v, depth_mm):
        """Convert pixel coordinates to 3D coordinates (mm)"""
        # Using pinhole camera model
        x = (u - self.cx) * depth_mm / self.fx
        y = (v - self.cy) * depth_mm / self.fy
        z = depth_mm

        return (x, y, z)

    def estimate_depth_from_size(self, known_size_mm, detected_size_pixels):
        """Estimate depth based on known object size"""
        if detected_size_pixels > 0:
            depth = (known_size_mm * self.fx) / detected_size_pixels
            return depth
        return self.estimated_depth

    def draw_detections(self, frame, objects, lines):
        """Draw detections on frame"""
        output = frame.copy()

        # Draw objects
        for obj in objects:
            # Draw contour
            cv2.drawContours(output, [obj['contour']], -1, (0, 255, 0), 2)

            # Draw bounding box
            x, y, w, h = obj['bbox']
            cv2.rectangle(output, (x, y), (x+w, y+h), (255, 0, 0), 2)

            # Draw center
            cx, cy = obj['center_2d']
            cv2.circle(output, (cx, cy), 5, (0, 0, 255), -1)

            # Draw rotated rectangle
            rect = cv2.minAreaRect(obj['contour'])
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            cv2.drawContours(output, [box], 0, (0, 255, 255), 2)

            # Label
            label = f"{obj['color']} {obj['shape']}"
            pos_3d = obj['center_3d']
            label2 = f"({pos_3d[0]:.0f}, {pos_3d[1]:.0f}, {pos_3d[2]:.0f})mm"

            cv2.putText(output, label, (x, y-25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(output, label2, (x, y-8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            cv2.putText(output, f"Angle: {obj['angle']:.1f}", (x, y+h+15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        # Draw lines
        for line in lines:
            cv2.line(output, line['start'], line['end'], (255, 0, 255), 2)
            cv2.circle(output, line['center'], 3, (255, 255, 0), -1)

        return output

    def run(self, display=True, cube_size_mm=40):
        """Run detection loop"""
        print("=" * 60)
        print("OBJECT & LINE DETECTION FOR PICK AND PLACE")
        print("=" * 60)

        if not self.connect():
            print("Failed to connect to camera")
            return

        print(f"Camera connected at index {self.camera_index}")
        print(f"Assuming cube size: {cube_size_mm}mm")
        print("\nDetecting: colored objects (red, blue, green, yellow) + lines")
        print("Press 'q' to quit, 's' to save frame, 'c' to calibrate depth")
        print("=" * 60 + "\n")

        frame_count = 0
        start_time = time.time()

        try:
            frame_timeout = 0
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    frame_timeout += 1
                    if frame_timeout > 30:
                        print("ERROR: Camera stopped providing frames. Check camera connection.")
                        break
                    time.sleep(0.1)
                    continue
                frame_timeout = 0  # Reset timeout on successful read

                frame_count += 1

                # Detect objects
                objects = self.detect_colored_objects(frame)

                # Update depth estimate based on detected object size
                for obj in objects:
                    if obj['shape'] in ['square', 'rectangle']:
                        max_dim = max(obj['size'])
                        if max_dim > 20:
                            self.estimated_depth = self.estimate_depth_from_size(
                                cube_size_mm, max_dim
                            )
                            # Update 3D position with new depth
                            obj['center_3d'] = self.pixel_to_3d(
                                obj['center_2d'][0],
                                obj['center_2d'][1],
                                self.estimated_depth
                            )

                # Detect lines
                lines = self.detect_lines(frame)

                # Print detections periodically
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed

                    if objects:
                        print(f"[{elapsed:.1f}s] FPS: {fps:.1f} | Found {len(objects)} objects, {len(lines)} lines")
                        for obj in objects:
                            pos = obj['center_3d']
                            print(f"  - {obj['color']} {obj['shape']}: "
                                  f"pos=({pos[0]:.0f}, {pos[1]:.0f}, {pos[2]:.0f})mm, "
                                  f"angle={obj['angle']:.1f}deg")

                if display:
                    # Draw detections
                    output = self.draw_detections(frame, objects, lines)

                    # Add info overlay
                    cv2.putText(output, f"Objects: {len(objects)} | Lines: {len(lines)}",
                               (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(output, f"Est. Depth: {self.estimated_depth:.0f}mm",
                               (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

                    cv2.imshow('Object Detection - Pick & Place', output)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("\nUser quit")
                        break
                    elif key == ord('s'):
                        filename = f'/tmp/detection_{int(time.time())}.jpg'
                        cv2.imwrite(filename, output)
                        print(f"Saved: {filename}")
                    elif key == ord('c'):
                        # Manual depth calibration
                        self.estimated_depth = float(input("Enter depth (mm): "))

        except KeyboardInterrupt:
            print("\nInterrupted")

        finally:
            self.disconnect()
            if display:
                cv2.destroyAllWindows()

            print("\nDone!")

    def get_best_pick_target(self, objects, preferred_color=None, preferred_shape=None):
        """Get the best object to pick based on criteria"""
        if not objects:
            return None

        candidates = objects

        # Filter by color
        if preferred_color:
            candidates = [o for o in candidates if o['color'] == preferred_color]

        # Filter by shape
        if preferred_shape:
            candidates = [o for o in candidates if o['shape'] == preferred_shape]

        if not candidates:
            candidates = objects

        # Return object closest to center of frame
        frame_center = (320, 240)
        candidates.sort(key=lambda o:
            (o['center_2d'][0] - frame_center[0])**2 +
            (o['center_2d'][1] - frame_center[1])**2
        )

        return candidates[0]


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Object Detection for Pick & Place')
    parser.add_argument('--no-display', action='store_true', help='Run without display')
    parser.add_argument('--cube-size', type=int, default=40, help='Cube size in mm (default: 40)')
    parser.add_argument('--camera', type=int, default=None, help='Camera index')
    args = parser.parse_args()

    detector = ObjectDetector(camera_index=args.camera)
    detector.run(display=not args.no_display, cube_size_mm=args.cube_size)


if __name__ == "__main__":
    main()
