#!/usr/bin/env python3
"""
Hand Pose Detection Test for RealSense 455D Camera
Tests MediaPipe hand detection and landmark tracking
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

def find_working_camera():
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

def detect_gesture(hand_landmarks):
    """Simple gesture detection based on finger positions"""
    # Get finger tip and MCP (knuckle) landmarks
    tips = [8, 12, 16, 20]  # Index, Middle, Ring, Pinky tips
    mcps = [5, 9, 13, 17]   # Index, Middle, Ring, Pinky MCPs

    fingers_up = []

    # Check thumb (special case - use x coordinate)
    thumb_tip = hand_landmarks.landmark[4]
    thumb_ip = hand_landmarks.landmark[3]
    thumb_up = thumb_tip.x < thumb_ip.x  # For right hand

    # Check other fingers (use y coordinate)
    for tip, mcp in zip(tips, mcps):
        tip_y = hand_landmarks.landmark[tip].y
        mcp_y = hand_landmarks.landmark[mcp].y
        fingers_up.append(tip_y < mcp_y)

    total_fingers = sum(fingers_up) + (1 if thumb_up else 0)

    # Gesture recognition
    if total_fingers == 5:
        return "OPEN_HAND", total_fingers
    elif total_fingers == 0:
        return "FIST", total_fingers
    elif fingers_up[0] and fingers_up[1] and not fingers_up[2] and not fingers_up[3]:
        return "VICTORY", total_fingers
    elif fingers_up[0] and not any(fingers_up[1:]):
        return "POINTING", total_fingers
    elif thumb_up and fingers_up[0] and not any(fingers_up[1:]):
        return "OK", total_fingers
    else:
        return f"FINGERS: {total_fingers}", total_fingers

def run_hand_detection(camera_index=None, display=True, duration=None):
    """
    Run hand pose detection

    Args:
        camera_index: Camera device index (auto-detect if None)
        display: Whether to display video window (set False for headless)
        duration: Run for N seconds then exit (None for continuous)
    """
    if camera_index is None:
        camera_index = find_working_camera()
        if camera_index is None:
            print("ERROR: No working camera found!")
            return False

    print(f"\nOpening camera {camera_index}...")
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {camera_index}")
        return False

    # Set resolution (RealSense typically supports 640x480 or 1280x720)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Camera opened: {width}x{height} @ {fps}fps")

    # Initialize MediaPipe Hands
    print("\nInitializing MediaPipe Hand Detection...")
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    print("\n" + "=" * 50)
    print("HAND POSE DETECTION RUNNING")
    print("=" * 50)
    if display:
        print("Press 'q' to quit")
    print("")

    frame_count = 0
    start_time = time.time()
    last_print_time = start_time
    detections = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Failed to read frame")
                break

            frame_count += 1

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process frame with MediaPipe
            results = hands.process(rgb_frame)

            current_time = time.time()
            elapsed = current_time - start_time

            # Check if hands detected
            if results.multi_hand_landmarks:
                detections += 1
                for idx, (hand_landmarks, handedness) in enumerate(
                    zip(results.multi_hand_landmarks, results.multi_handedness)
                ):
                    # Get hand label (Left/Right)
                    hand_label = handedness.classification[0].label
                    confidence = handedness.classification[0].score

                    # Detect gesture
                    gesture, fingers = detect_gesture(hand_landmarks)

                    # Get wrist position
                    wrist = hand_landmarks.landmark[0]
                    wrist_x = int(wrist.x * width)
                    wrist_y = int(wrist.y * height)

                    # Print detection info (every 0.5 seconds)
                    if current_time - last_print_time > 0.5:
                        print(f"[{elapsed:.1f}s] {hand_label} hand detected: "
                              f"Gesture={gesture}, Wrist=({wrist_x},{wrist_y}), "
                              f"Confidence={confidence:.2f}")
                        last_print_time = current_time

                    if display:
                        # Draw hand landmarks on frame
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )

                        # Add text overlay
                        cv2.putText(frame, f"{hand_label}: {gesture}",
                                   (10, 30 + idx * 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if display:
                # Add FPS counter
                fps_actual = frame_count / elapsed if elapsed > 0 else 0
                cv2.putText(frame, f"FPS: {fps_actual:.1f}",
                           (width - 100, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                # Show frame
                cv2.imshow('Hand Pose Detection - RealSense 455D', frame)

                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nUser quit")
                    break

            # Check duration limit
            if duration and elapsed >= duration:
                print(f"\nDuration limit ({duration}s) reached")
                break

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        # Cleanup
        cap.release()
        hands.close()
        if display:
            cv2.destroyAllWindows()

        # Print summary
        elapsed = time.time() - start_time
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total frames processed: {frame_count}")
        print(f"Total time: {elapsed:.1f} seconds")
        print(f"Average FPS: {frame_count/elapsed:.1f}" if elapsed > 0 else "N/A")
        print(f"Frames with hand detections: {detections}")
        print(f"Detection rate: {100*detections/frame_count:.1f}%" if frame_count > 0 else "N/A")

    return True

def run_headless_test(duration=5):
    """Run a headless test (no display window) for specified duration"""
    print("Running headless hand detection test...")
    return run_hand_detection(display=False, duration=duration)

if __name__ == "__main__":
    print("=" * 50)
    print("Hand Pose Detection Test")
    print("RealSense 455D + MediaPipe")
    print("=" * 50)
    print(f"\nOpenCV version: {cv2.__version__}")
    print(f"MediaPipe version: {mp.__version__}")

    # Check command line args
    headless = "--headless" in sys.argv or "-H" in sys.argv

    if headless:
        print("\nRunning in HEADLESS mode (no display)")
        success = run_headless_test(duration=10)
    else:
        print("\nRunning with display window")
        print("(Use --headless or -H for no window)")
        success = run_hand_detection()

    sys.exit(0 if success else 1)
