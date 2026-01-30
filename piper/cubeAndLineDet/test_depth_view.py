#!/usr/bin/env python3
"""
Standalone script to test and view RealSense depth camera
This is more stable than Jupyter notebook if kernel crashes occur
"""

import sys
import warnings
warnings.filterwarnings('ignore')

# Check NumPy version first
try:
    import numpy as np
    if np.__version__.startswith('2.'):
        print("⚠ WARNING: NumPy 2.x detected. This may cause issues.")
        print("  Downgrading NumPy...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy<2.0", "--force-reinstall", "--quiet"])
        print("  Please restart Python and run again")
        sys.exit(1)
except ImportError:
    pass

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import time

class DepthViewer(Node):
    def __init__(self, depth_topic='/camera/camera/depth/image_rect_raw', 
                 color_topic='/camera/camera/color/image_raw'):
        super().__init__('depth_viewer_test')
        
        self.bridge = CvBridge()
        self.depth_image = None
        self.color_image = None
        self.depth_received = False
        self.color_received = False
        
        # Subscribers
        self.depth_sub = self.create_subscription(
            Image,
            depth_topic,
            self.depth_callback,
            10
        )
        
        self.color_sub = self.create_subscription(
            Image,
            color_topic,
            self.color_callback,
            10
        )
        
        self.get_logger().info(f'Subscribed to depth topic: {depth_topic}')
        self.get_logger().info(f'Subscribed to color topic: {color_topic}')
    
    def depth_callback(self, msg):
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='16UC1')
            self.depth_received = True
        except Exception as e:
            self.get_logger().error(f'Error processing depth image: {e}')
    
    def color_callback(self, msg):
        try:
            self.color_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.color_received = True
        except Exception as e:
            self.get_logger().error(f'Error processing color image: {e}')
    
    def get_depth_visualization(self):
        """Convert depth image to colorized visualization"""
        if self.depth_image is None:
            return None
        
        depth_normalized = cv2.normalize(
            self.depth_image.astype(np.float32),
            None,
            0, 255,
            cv2.NORM_MINMAX
        ).astype(np.uint8)
        
        depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
        return depth_colored

def main():
    print("=" * 60)
    print("RealSense Depth Camera Viewer")
    print("=" * 60)
    
    # Initialize ROS 2
    if not rclpy.ok():
        rclpy.init()
    
    # Create node
    node = DepthViewer()
    
    print("\nWaiting for depth data (max 15 seconds)...")
    print("Make sure camera is running: ros2 launch realsense2_camera rs_launch.py")
    
    start_time = time.time()
    timeout = 15.0
    
    while time.time() - start_time < timeout:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.depth_received:
            print(f"\n✓ Depth image received! Shape: {node.depth_image.shape}")
            break
        print(".", end="", flush=True)
        time.sleep(0.5)
    
    if not node.depth_received:
        print("\n⚠ No depth data received!")
        print("\nTroubleshooting:")
        print("  1. Check if camera is running: ros2 node list | grep camera")
        print("  2. Check topics: ros2 topic list | grep depth")
        print("  3. Start camera: ros2 launch realsense2_camera rs_launch.py")
        node.destroy_node()
        rclpy.shutdown()
        return
    
    # Wait for color too
    print("\nWaiting for color image...")
    start_time = time.time()
    while time.time() - start_time < 5.0:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.color_received:
            print("✓ Color image received!")
            break
        time.sleep(0.1)
    
    # Display images
    print("\nDisplaying images...")
    print("Press 'q' to quit")
    
    depth_vis = node.get_depth_visualization()
    
    while True:
        # Get latest images
        rclpy.spin_once(node, timeout_sec=0.1)
        
        if node.depth_received and node.depth_image is not None:
            depth_vis = node.get_depth_visualization()
            cv2.imshow('Depth Visualization', depth_vis)
        
        if node.color_received and node.color_image is not None:
            cv2.imshow('Color Image', node.color_image)
        
        # Show overlay if both available
        if node.depth_received and node.color_received:
            if node.color_image.shape[:2] != depth_vis.shape[:2]:
                depth_resized = cv2.resize(depth_vis, 
                                         (node.color_image.shape[1], node.color_image.shape[0]))
            else:
                depth_resized = depth_vis
            overlay = cv2.addWeighted(node.color_image, 0.6, depth_resized, 0.4, 0)
            cv2.imshow('Color + Depth Overlay', overlay)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()
    print("\n✓ Done!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        cv2.destroyAllWindows()
        rclpy.shutdown()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        rclpy.shutdown()
