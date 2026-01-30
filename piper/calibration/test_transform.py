#!/usr/bin/env python3
"""
Test script for coordinate transform accuracy.

This script:
1. Shows camera view with crosshair at center
2. When you click, it gets the depth at that pixel
3. Transforms the 3D point to arm base coordinates
4. Optionally moves the arm to that point to verify accuracy

Usage:
1. Run the coordinate transform node
2. Run this test script
3. Click on objects in the camera view
4. Check if the arm reaches the correct position
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped, PoseStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
import sys

sys.path.insert(0, '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk')


class TransformTester(Node):
    def __init__(self):
        super().__init__('transform_tester')

        self.bridge = CvBridge()

        # Camera data
        self.color_image = None
        self.depth_image = None
        self.camera_info = None

        # Mouse click position
        self.click_x = None
        self.click_y = None

        # Subscribers
        self.color_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.color_callback, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/depth/image_rect_raw', self.depth_callback, 10)
        self.info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info', self.info_callback, 10)

        # Subscribe to transformed points
        self.transformed_sub = self.create_subscription(
            PointStamped, '/object_point_base', self.transformed_callback, 10)

        # Publisher for points in camera frame
        self.point_pub = self.create_publisher(PointStamped, '/object_point_camera', 10)

        # Store last transformed point
        self.last_transformed_point = None

        self.get_logger().info('Transform Tester started')
        self.get_logger().info('Click on an object to get its 3D position')

    def color_callback(self, msg):
        self.color_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_callback(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, 'passthrough')

    def info_callback(self, msg):
        if self.camera_info is None:
            self.camera_info = msg
            self.get_logger().info('Camera info received')

    def transformed_callback(self, msg):
        self.last_transformed_point = msg
        self.get_logger().info(
            f'Transformed point in BASE frame: '
            f'x={msg.point.x:.3f}, y={msg.point.y:.3f}, z={msg.point.z:.3f} meters'
        )

    def pixel_to_3d(self, u, v, depth):
        """Convert pixel coordinates + depth to 3D point in camera frame"""
        if self.camera_info is None:
            return None

        # Camera intrinsics
        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        # Convert to 3D (depth is in millimeters for RealSense)
        z = depth / 1000.0  # Convert to meters
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        return np.array([x, y, z])

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.click_x = x
            self.click_y = y

            if self.depth_image is not None and self.camera_info is not None:
                # Get depth at clicked point (average small region for stability)
                region_size = 5
                y1 = max(0, y - region_size)
                y2 = min(self.depth_image.shape[0], y + region_size)
                x1 = max(0, x - region_size)
                x2 = min(self.depth_image.shape[1], x + region_size)

                depth_region = self.depth_image[y1:y2, x1:x2]
                valid_depths = depth_region[depth_region > 0]

                if len(valid_depths) > 0:
                    depth = np.median(valid_depths)

                    # Convert to 3D
                    point_3d = self.pixel_to_3d(x, y, depth)

                    if point_3d is not None:
                        self.get_logger().info(
                            f'Clicked at pixel ({x}, {y}), depth={depth:.0f}mm'
                        )
                        self.get_logger().info(
                            f'3D point in CAMERA frame: '
                            f'x={point_3d[0]:.3f}, y={point_3d[1]:.3f}, z={point_3d[2]:.3f} meters'
                        )

                        # Publish point for transformation
                        msg = PointStamped()
                        msg.header.stamp = self.get_clock().now().to_msg()
                        msg.header.frame_id = 'camera_color_optical_frame'
                        msg.point.x = float(point_3d[0])
                        msg.point.y = float(point_3d[1])
                        msg.point.z = float(point_3d[2])
                        self.point_pub.publish(msg)
                else:
                    self.get_logger().warn(f'No valid depth at ({x}, {y})')


def main():
    rclpy.init()
    node = TransformTester()

    print('\n' + '='*60)
    print('  TRANSFORM ACCURACY TESTER')
    print('='*60)
    print('\nInstructions:')
    print('1. Make sure coordinate_transform_node.py is running')
    print('2. Click on objects in the camera view')
    print('3. See the 3D position in CAMERA frame and BASE frame')
    print('4. Verify by moving arm to the position')
    print('\nPress Q to quit')
    print('='*60 + '\n')

    cv2.namedWindow('Transform Test', cv2.WINDOW_NORMAL)
    cv2.setMouseCallback('Transform Test', node.mouse_callback)

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)

            if node.color_image is not None:
                vis_image = node.color_image.copy()

                # Draw crosshair at center
                h, w = vis_image.shape[:2]
                cv2.line(vis_image, (w//2-20, h//2), (w//2+20, h//2), (0, 255, 0), 1)
                cv2.line(vis_image, (w//2, h//2-20), (w//2, h//2+20), (0, 255, 0), 1)

                # Draw click position
                if node.click_x is not None:
                    cv2.circle(vis_image, (node.click_x, node.click_y), 5, (0, 0, 255), -1)
                    cv2.circle(vis_image, (node.click_x, node.click_y), 10, (0, 0, 255), 2)

                # Show last transformed point
                if node.last_transformed_point is not None:
                    p = node.last_transformed_point.point
                    text = f'Base frame: ({p.x:.3f}, {p.y:.3f}, {p.z:.3f})m'
                    cv2.putText(vis_image, text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.putText(vis_image, 'Click on object | Q: Quit', (10, h-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow('Transform Test', vis_image)

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
