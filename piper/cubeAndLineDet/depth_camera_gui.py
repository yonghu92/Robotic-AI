#!/usr/bin/env python3
"""
RealSense Depth Camera GUI Viewer
A simple GUI application to view depth camera feed with controls
"""

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image as PILImage, ImageTk
import threading
import time

class DepthCameraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RealSense Depth Camera Viewer")
        self.root.geometry("1200x800")
        
        # ROS 2 setup
        if not rclpy.ok():
            rclpy.init()
        
        self.node = DepthViewerNode()
        self.bridge = CvBridge()
        
        # Image storage
        self.depth_image = None
        self.color_image = None
        self.depth_vis = None
        
        # GUI setup
        self.setup_gui()
        
        # Start ROS 2 spinner in background
        self.spinner_thread = threading.Thread(target=self.spin_ros, daemon=True)
        self.spinner_thread.start()
        
        # Start update loop
        self.update_images()
    
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Status: Connecting to camera...", 
                                     font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # Colormap selection
        ttk.Label(control_frame, text="Colormap:").grid(row=0, column=1, padx=5)
        self.colormap_var = tk.StringVar(value="JET")
        colormap_combo = ttk.Combobox(control_frame, textvariable=self.colormap_var,
                                      values=["JET", "HOT", "COOL", "RAINBOW", "TURBO", "VIRIDIS"],
                                      state="readonly", width=10)
        colormap_combo.grid(row=0, column=2, padx=5)
        colormap_combo.bind("<<ComboboxSelected>>", self.on_colormap_change)
        
        # Depth range controls
        ttk.Label(control_frame, text="Min Depth (mm):").grid(row=1, column=0, padx=5, pady=5)
        self.min_depth_var = tk.IntVar(value=0)
        min_depth_scale = ttk.Scale(control_frame, from_=0, to=5000, 
                                    variable=self.min_depth_var, orient=tk.HORIZONTAL, length=200)
        min_depth_scale.grid(row=1, column=1, padx=5)
        self.min_depth_label = ttk.Label(control_frame, text="0")
        self.min_depth_label.grid(row=1, column=2, padx=5)
        min_depth_scale.configure(command=lambda v: self.min_depth_label.config(text=f"{int(float(v))}"))
        
        ttk.Label(control_frame, text="Max Depth (mm):").grid(row=2, column=0, padx=5, pady=5)
        self.max_depth_var = tk.IntVar(value=8000)
        max_depth_scale = ttk.Scale(control_frame, from_=1000, to=10000, 
                                    variable=self.max_depth_var, orient=tk.HORIZONTAL, length=200)
        max_depth_scale.grid(row=2, column=1, padx=5)
        self.max_depth_label = ttk.Label(control_frame, text="8000")
        self.max_depth_label.grid(row=2, column=2, padx=5)
        max_depth_scale.configure(command=lambda v: self.max_depth_label.config(text=f"{int(float(v))}"))
        
        # Image display frames
        # Color image
        color_frame = ttk.LabelFrame(main_frame, text="Color Image", padding="5")
        color_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.color_label = ttk.Label(color_frame, text="Waiting for color image...")
        self.color_label.pack()
        
        # Depth image
        depth_frame = ttk.LabelFrame(main_frame, text="Depth Visualization", padding="5")
        depth_frame.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.depth_label = ttk.Label(depth_frame, text="Waiting for depth image...")
        self.depth_label.pack()
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Depth Statistics", padding="10")
        stats_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=6, width=80, font=('Courier', 9))
        self.stats_text.pack()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def on_colormap_change(self, event=None):
        """Handle colormap change"""
        pass  # Will be used in update
    
    def get_colormap(self):
        """Get OpenCV colormap from selection"""
        colormap_map = {
            "JET": cv2.COLORMAP_JET,
            "HOT": cv2.COLORMAP_HOT,
            "COOL": cv2.COLORMAP_COOL,
            "RAINBOW": cv2.COLORMAP_RAINBOW,
            "TURBO": cv2.COLORMAP_TURBO,
            "VIRIDIS": cv2.COLORMAP_VIRIDIS
        }
        return colormap_map.get(self.colormap_var.get(), cv2.COLORMAP_JET)
    
    def spin_ros(self):
        """Spin ROS 2 node in background thread"""
        while rclpy.ok():
            rclpy.spin_once(self.node, timeout_sec=0.1)
            time.sleep(0.01)
    
    def update_images(self):
        """Update GUI with latest images"""
        # Get latest images from node
        if self.node.depth_received and self.node.depth_image is not None:
            self.depth_image = self.node.depth_image.copy()
            self.update_depth_display()
            self.update_status("Connected - Receiving depth data")
        else:
            self.update_status("Waiting for depth data...")
        
        if self.node.color_received and self.node.color_image is not None:
            self.color_image = self.node.color_image.copy()
            self.update_color_display()
        
        # Schedule next update
        self.root.after(50, self.update_images)  # ~20 FPS
    
    def update_depth_display(self):
        """Update depth visualization"""
        if self.depth_image is None:
            return
        
        # Get depth range from sliders
        min_depth = self.min_depth_var.get()
        max_depth = self.max_depth_var.get()
        
        # Clip depth to range
        depth_clipped = np.clip(self.depth_image, min_depth, max_depth)
        
        # Normalize to 0-255
        if max_depth > min_depth:
            depth_normalized = ((depth_clipped - min_depth) / (max_depth - min_depth) * 255).astype(np.uint8)
        else:
            depth_normalized = np.zeros_like(depth_clipped, dtype=np.uint8)
        
        # Apply colormap
        colormap = self.get_colormap()
        depth_colored = cv2.applyColorMap(depth_normalized, colormap)
        
        # Resize for display (max 400x300)
        display_size = (400, 300)
        depth_resized = cv2.resize(depth_colored, display_size)
        
        # Convert to PhotoImage
        depth_rgb = cv2.cvtColor(depth_resized, cv2.COLOR_BGR2RGB)
        depth_pil = PILImage.fromarray(depth_rgb)
        depth_photo = ImageTk.PhotoImage(image=depth_pil)
        
        # Update label
        self.depth_label.configure(image=depth_photo, text="")
        self.depth_label.image = depth_photo  # Keep a reference
        
        # Update statistics
        self.update_statistics()
    
    def update_color_display(self):
        """Update color image display"""
        if self.color_image is None:
            return
        
        # Resize for display
        display_size = (400, 300)
        color_resized = cv2.resize(self.color_image, display_size)
        
        # Convert to PhotoImage
        color_rgb = cv2.cvtColor(color_resized, cv2.COLOR_BGR2RGB)
        color_pil = PILImage.fromarray(color_rgb)
        color_photo = ImageTk.PhotoImage(image=color_pil)
        
        # Update label
        self.color_label.configure(image=color_photo, text="")
        self.color_label.image = color_photo  # Keep a reference
    
    def update_statistics(self):
        """Update depth statistics display"""
        if self.depth_image is None:
            return
        
        valid_depth = self.depth_image[self.depth_image > 0]
        
        stats = f"""Depth Statistics:
  Image Size: {self.depth_image.shape[1]}x{self.depth_image.shape[0]}
  Valid Pixels: {np.count_nonzero(self.depth_image)} / {self.depth_image.size} ({100*np.count_nonzero(self.depth_image)/self.depth_image.size:.1f}%)
  Min Depth: {self.depth_image.min()} mm
  Max Depth: {self.depth_image.max()} mm"""
        
        if len(valid_depth) > 0:
            stats += f"""
  Mean Depth: {valid_depth.mean():.1f} mm
  Median Depth: {np.median(valid_depth):.1f} mm
  Std Dev: {valid_depth.std():.1f} mm"""
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=f"Status: {message}")
    
    def on_closing(self):
        """Handle window closing"""
        self.node.destroy_node()
        rclpy.shutdown()
        self.root.destroy()

class DepthViewerNode(Node):
    def __init__(self):
        super().__init__('depth_camera_gui_node')
        
        self.bridge = CvBridge()
        self.depth_image = None
        self.color_image = None
        self.depth_received = False
        self.color_received = False
        
        # Subscribers
        self.depth_sub = self.create_subscription(
            Image,
            '/camera/camera/depth/image_rect_raw',
            self.depth_callback,
            10
        )
        
        self.color_sub = self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.color_callback,
            10
        )
        
        self.get_logger().info('Depth Camera GUI Node started')
    
    def depth_callback(self, msg):
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='16UC1')
            self.depth_received = True
        except Exception as e:
            self.get_logger().error(f'Error processing depth: {e}')
    
    def color_callback(self, msg):
        try:
            self.color_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.color_received = True
        except Exception as e:
            self.get_logger().error(f'Error processing color: {e}')

def main():
    print("=" * 60)
    print("RealSense Depth Camera GUI Viewer")
    print("=" * 60)
    print("\nMake sure camera is running:")
    print("  ros2 launch realsense2_camera rs_launch.py")
    print("\nStarting GUI...")
    
    root = tk.Tk()
    app = DepthCameraGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        app.on_closing()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
