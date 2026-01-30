#!/usr/bin/env python3
"""
Simple RealSense Camera Viewer
Shows color and depth streams
"""

import cv2
import sys

def find_camera():
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

def main():
    camera_index = find_camera()
    if camera_index is None:
        print("ERROR: No camera found")
        return
    
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("ERROR: Could not open camera")
        return
    
    print("Camera viewer started. Press 'q' to quit")
    print("Press 's' to save current frame")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                break
            
            frame_count += 1
            
            # Add info overlay
            cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit, 's' to save", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow('RealSense Camera Viewer', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f'/tmp/camera_frame_{frame_count}.jpg'
                cv2.imwrite(filename, frame)
                print(f"Saved: {filename}")
    
    except KeyboardInterrupt:
        print("\nInterrupted")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released")

if __name__ == "__main__":
    main()
