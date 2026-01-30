#!/usr/bin/env python3
"""
Color-based Object Detection Node for Piper Arm

Detects colored objects using HSV color filtering and computes their
3D positions using depth data and camera intrinsics.

Subscribes to:
  - /camera/camera/color/image_raw: RGB image
  - /camera/camera/depth/image_rect_raw: Depth image
  - /camera/camera/color/camera_info: Camera intrinsics

Publishes:
  - /detected_objects: List of detected objects with positions
  - /object_point_camera: Single object point for transform node
  - /detection_image: Annotated image showing detections
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np
import json
import yaml
import os


class ObjectDetector(Node):
    def __init__(self):
        super().__init__('object_detector')

        self.bridge = CvBridge()

        # Camera data
        self.color_image = None
        self.depth_image = None
        self.camera_matrix = None

        # Load calibrated color ranges
        self.color_ranges = self.load_color_calibration()

        # Detection parameters
        self.min_area = 500  # Minimum contour area in pixels
        self.max_area = 50000  # Maximum contour area

        # Subscribers
        self.color_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.color_callback, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/depth/image_rect_raw', self.depth_callback, 10)
        self.info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info', self.info_callback, 10)

        # Publishers
        self.point_pub = self.create_publisher(PointStamped, '/object_point_camera', 10)
        self.image_pub = self.create_publisher(Image, '/detection_image', 10)
        self.objects_pub = self.create_publisher(String, '/detected_objects', 10)

        # Detection timer (10 Hz)
        self.timer = self.create_timer(0.1, self.detect_objects)

        # Currently selected target (for picking)
        self.target_color = None
        self.last_detection = None

        self.get_logger().info('Object Detector started')
        self.get_logger().info('Detecting colors: ' + ', '.join(self.color_ranges.keys()))

    def load_color_calibration(self):
        """Load color ranges from calibration file"""
        calibration_path = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/detection/color_calibration.yaml'

        if os.path.exists(calibration_path):
            with open(calibration_path, 'r') as f:
                data = yaml.safe_load(f)

            color_ranges = {}
            for color_name, values in data['color_ranges'].items():
                color_ranges[color_name] = {
                    'lower': np.array(values['lower']),
                    'upper': np.array(values['upper']),
                    'bgr': tuple(values['bgr'])
                }

            self.get_logger().info(f'Loaded calibrated colors: {list(color_ranges.keys())}')
            return color_ranges
        else:
            self.get_logger().warn('No color calibration found, using defaults')
            # Fallback defaults
            return {
                'red': {
                    'lower': np.array([0, 100, 100]),
                    'upper': np.array([10, 255, 255]),
                    'bgr': (0, 0, 255)
                },
                'green': {
                    'lower': np.array([35, 100, 100]),
                    'upper': np.array([85, 255, 255]),
                    'bgr': (0, 255, 0)
                },
                'blue': {
                    'lower': np.array([100, 100, 100]),
                    'upper': np.array([130, 255, 255]),
                    'bgr': (255, 0, 0)
                }
            }

    def color_callback(self, msg):
        self.color_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_callback(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, 'passthrough')

    def info_callback(self, msg):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.get_logger().info('Camera intrinsics received')

    def pixel_to_3d(self, u, v, depth):
        """Convert pixel + depth to 3D point in camera frame"""
        if self.camera_matrix is None:
            return None

        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        z = depth / 1000.0  # mm to meters
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        return np.array([x, y, z])

    def get_depth_at_point(self, u, v, region_size=5):
        """Get median depth in a small region around the point"""
        if self.depth_image is None:
            return None

        h, w = self.depth_image.shape
        y1 = max(0, v - region_size)
        y2 = min(h, v + region_size)
        x1 = max(0, u - region_size)
        x2 = min(w, u + region_size)

        region = self.depth_image[y1:y2, x1:x2]
        valid = region[region > 0]

        if len(valid) > 0:
            return np.median(valid)
        return None

    def detect_color(self, hsv_image, color_name):
        """Detect objects of a specific color"""
        color_info = self.color_ranges[color_name]

        # Use calibrated lower/upper ranges
        mask = cv2.inRange(hsv_image, color_info['lower'], color_info['upper'])

        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area < area < self.max_area:
                # Get bounding box and center
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2

                # Get depth
                depth = self.get_depth_at_point(cx, cy)

                if depth is not None and depth > 100:  # At least 10cm away
                    # Get 3D position
                    point_3d = self.pixel_to_3d(cx, cy, depth)

                    if point_3d is not None:
                        detections.append({
                            'color': color_name,
                            'pixel': (cx, cy),
                            'bbox': (x, y, w, h),
                            'area': area,
                            'depth_mm': depth,
                            'position_3d': point_3d.tolist(),
                            'contour': contour
                        })

        return detections

    def detect_objects(self):
        """Main detection loop"""
        if self.color_image is None or self.depth_image is None:
            return

        # Convert to HSV
        hsv = cv2.cvtColor(self.color_image, cv2.COLOR_BGR2HSV)

        # Detect all colors
        all_detections = []
        for color_name in self.color_ranges.keys():
            detections = self.detect_color(hsv, color_name)
            all_detections.extend(detections)

        # Create visualization
        vis_image = self.color_image.copy()

        for det in all_detections:
            color_bgr = self.color_ranges[det['color']]['bgr']
            x, y, w, h = det['bbox']
            cx, cy = det['pixel']

            # Draw bounding box
            cv2.rectangle(vis_image, (x, y), (x+w, y+h), color_bgr, 2)

            # Draw center point
            cv2.circle(vis_image, (cx, cy), 5, color_bgr, -1)

            # Label with color and distance
            pos = det['position_3d']
            label = f"{det['color']}: {pos[2]:.2f}m"
            cv2.putText(vis_image, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)

        # Show detection count
        cv2.putText(vis_image, f"Objects: {len(all_detections)}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Publish visualization
        self.image_pub.publish(self.bridge.cv2_to_imgmsg(vis_image, 'bgr8'))

        # Publish detected objects as JSON
        objects_data = []
        for det in all_detections:
            objects_data.append({
                'color': det['color'],
                'position': det['position_3d'],
                'depth_mm': det['depth_mm'],
                'pixel': det['pixel']
            })

        msg = String()
        msg.data = json.dumps(objects_data)
        self.objects_pub.publish(msg)

        # If we have a target color, publish its position
        if self.target_color and all_detections:
            target_dets = [d for d in all_detections if d['color'] == self.target_color]
            if target_dets:
                # Pick the closest one
                target = min(target_dets, key=lambda d: d['position_3d'][2])
                self.publish_target_point(target)
        elif all_detections:
            # No specific target, publish closest object
            closest = min(all_detections, key=lambda d: d['position_3d'][2])
            self.publish_target_point(closest)
            self.last_detection = closest

    def publish_target_point(self, detection):
        """Publish detected object position for transform node"""
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_color_optical_frame'
        msg.point.x = float(detection['position_3d'][0])
        msg.point.y = float(detection['position_3d'][1])
        msg.point.z = float(detection['position_3d'][2])

        self.point_pub.publish(msg)

    def set_target_color(self, color):
        """Set which color to track for picking"""
        if color in self.color_ranges or color is None:
            self.target_color = color
            self.get_logger().info(f'Target color set to: {color}')
        else:
            self.get_logger().warn(f'Unknown color: {color}')


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetector()

    print('\n' + '='*60)
    print('  OBJECT DETECTOR')
    print('='*60)
    print(f'\nDetecting colors: {", ".join(node.color_ranges.keys())}')
    print('Publishing to:')
    print('  /detected_objects - JSON list of all detections')
    print('  /object_point_camera - Closest object position')
    print('  /detection_image - Annotated visualization')
    print('='*60 + '\n')

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
