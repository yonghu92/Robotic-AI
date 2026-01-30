#!/usr/bin/env python3
"""Quick test to check if ArUco/ChArUco board is being detected."""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class BoardTest(Node):
    def __init__(self):
        super().__init__('board_test')
        self.bridge = CvBridge()
        self.image = None

        # Try multiple ArUco dictionaries
        self.dictionaries = {
            'DICT_4X4_50': cv2.aruco.DICT_4X4_50,
            'DICT_4X4_100': cv2.aruco.DICT_4X4_100,
            'DICT_5X5_50': cv2.aruco.DICT_5X5_50,
            'DICT_6X6_50': cv2.aruco.DICT_6X6_50,
        }

        self.create_subscription(Image, '/camera/camera/color/image_raw', self.cb, 10)

    def cb(self, msg):
        self.image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

def main():
    rclpy.init()
    node = BoardTest()

    print('Testing ArUco marker detection...')
    print('Press Q to quit\n')

    cv2.namedWindow('Board Detection Test', cv2.WINDOW_NORMAL)

    # Wait for image (30 seconds)
    print('Waiting for camera image (up to 30s)...')
    for i in range(600):
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.image is not None:
            print('Camera image received!')
            break
        if i % 100 == 0:
            print(f'  Still waiting... ({i//20}s)')

    if node.image is None:
        print('No camera image!')
        return

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            if node.image is None:
                continue

            vis = node.image.copy()
            gray = cv2.cvtColor(vis, cv2.COLOR_BGR2GRAY)

            # Try DICT_4X4_50 (the one used in charuco_board_A4.png)
            dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

            # Create detector with adjusted parameters for better detection
            detector_params = cv2.aruco.DetectorParameters()
            detector_params.adaptiveThreshWinSizeMin = 3
            detector_params.adaptiveThreshWinSizeMax = 23
            detector_params.adaptiveThreshWinSizeStep = 10
            detector_params.minMarkerPerimeterRate = 0.01  # Smaller markers
            detector_params.maxMarkerPerimeterRate = 4.0

            detector = cv2.aruco.ArucoDetector(dictionary, detector_params)
            corners, ids, rejected = detector.detectMarkers(gray)

            total_markers = len(ids) if ids is not None else 0
            detected_dict = 'DICT_4X4_50'

            if ids is not None and len(ids) > 0:
                cv2.aruco.drawDetectedMarkers(vis, corners, ids)

            # Show rejected candidates count
            rejected_count = len(rejected) if rejected else 0

            # Show status
            if total_markers > 0:
                status = f'DETECTED: {total_markers} markers'
                color = (0, 255, 0)
            else:
                status = f'NO MARKERS (rejected candidates: {rejected_count})'
                color = (0, 0, 255)

            cv2.putText(vis, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(vis, 'Q=quit, S=save frame', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
            cv2.putText(vis, f'Image: {vis.shape[1]}x{vis.shape[0]}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            cv2.putText(vis, 'Make sure board is well-lit and visible', (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)

            cv2.imshow('Board Detection Test', vis)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite('/tmp/camera_frame.png', node.image)
                print('Saved frame to /tmp/camera_frame.png')

    finally:
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
