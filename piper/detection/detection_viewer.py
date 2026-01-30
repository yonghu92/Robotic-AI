#!/usr/bin/env python3
"""
Detection Viewer - Visualize object detections and tune color ranges

Shows:
- Live camera feed with detection overlays
- Detected objects list with 3D positions
- HSV color picker for tuning

Controls:
- Click on image to see HSV values at that point
- Press 1-5 to select color to tune (1=red, 2=green, 3=blue, 4=yellow, 5=orange)
- Press Q to quit
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np
import json


class DetectionViewer(Node):
    def __init__(self):
        super().__init__('detection_viewer')

        self.bridge = CvBridge()

        # Images
        self.color_image = None
        self.detection_image = None

        # Detected objects
        self.detected_objects = []
        self.base_frame_point = None

        # HSV at click point
        self.click_hsv = None

        # Subscribers
        self.color_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.color_callback, 10)
        self.det_sub = self.create_subscription(
            Image, '/detection_image', self.detection_callback, 10)
        self.objects_sub = self.create_subscription(
            String, '/detected_objects', self.objects_callback, 10)
        self.point_sub = self.create_subscription(
            PointStamped, '/object_point_base', self.point_callback, 10)

        self.get_logger().info('Detection Viewer started')

    def color_callback(self, msg):
        self.color_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def detection_callback(self, msg):
        self.detection_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def objects_callback(self, msg):
        try:
            self.detected_objects = json.loads(msg.data)
        except:
            self.detected_objects = []

    def point_callback(self, msg):
        self.base_frame_point = (msg.point.x, msg.point.y, msg.point.z)

    def mouse_callback(self, event, x, y, flags, param):
        """Get HSV value at clicked point"""
        if event == cv2.EVENT_LBUTTONDOWN and self.color_image is not None:
            hsv = cv2.cvtColor(self.color_image, cv2.COLOR_BGR2HSV)
            if 0 <= y < hsv.shape[0] and 0 <= x < hsv.shape[1]:
                self.click_hsv = hsv[y, x]
                print(f'HSV at ({x}, {y}): H={self.click_hsv[0]}, S={self.click_hsv[1]}, V={self.click_hsv[2]}')


def main():
    rclpy.init()
    node = DetectionViewer()

    print('\n' + '='*60)
    print('  DETECTION VIEWER')
    print('='*60)
    print('\nControls:')
    print('  Click on image: Show HSV values at that point')
    print('  Q: Quit')
    print('\nNote: Make sure object_detector.py is running!')
    print('='*60 + '\n')

    cv2.namedWindow('Detection View', cv2.WINDOW_NORMAL)
    cv2.setMouseCallback('Detection View', node.mouse_callback)

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)

            # Use detection image if available, otherwise raw image
            if node.detection_image is not None:
                vis = node.detection_image.copy()
            elif node.color_image is not None:
                vis = node.color_image.copy()
            else:
                continue

            h, w = vis.shape[:2]

            # Show base frame coordinates if available
            if node.base_frame_point is not None:
                p = node.base_frame_point
                text = f'Base: ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})m'
                cv2.putText(vis, text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Show HSV at click
            if node.click_hsv is not None:
                hsv = node.click_hsv
                text = f'HSV: ({hsv[0]}, {hsv[1]}, {hsv[2]})'
                cv2.putText(vis, text, (10, h-40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            # Show object list on the right
            if node.detected_objects:
                y_pos = 100
                cv2.putText(vis, 'Detected:', (w-200, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                for obj in node.detected_objects[:5]:  # Show max 5
                    y_pos += 25
                    pos = obj['position']
                    text = f"{obj['color']}: {pos[2]:.2f}m"
                    cv2.putText(vis, text, (w-200, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            cv2.putText(vis, 'Click: HSV | Q: Quit', (10, h-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            cv2.imshow('Detection View', vis)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break

    except KeyboardInterrupt:
        pass

    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
