#!/usr/bin/env python3
"""
Generate a ChArUco calibration board for printing.
Print this at 100% scale (no scaling) on A4 paper.
"""

import cv2
import numpy as np

# ChArUco board parameters (must match hand_eye_calibration.py)
SQUARES_X = 5
SQUARES_Y = 7
SQUARE_SIZE = 0.04  # 4cm in meters
MARKER_SIZE = 0.03  # 3cm in meters

# Create ChArUco board
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
board = cv2.aruco.CharucoBoard(
    (SQUARES_X, SQUARES_Y),
    SQUARE_SIZE,
    MARKER_SIZE,
    dictionary
)

# Generate image (A4 at 300 DPI approximately)
# A4 = 210mm x 297mm, at 300 DPI = 2480 x 3508 pixels
# We'll use a slightly smaller size for margins
img_size = (2000, 2800)
board_image = board.generateImage(img_size)

# Save
output_path = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration/charuco_board_5x7.png'
cv2.imwrite(output_path, board_image)

print(f'ChArUco board saved to: {output_path}')
print(f'\nBoard parameters:')
print(f'  Squares: {SQUARES_X} x {SQUARES_Y}')
print(f'  Square size: {SQUARE_SIZE*100:.1f} cm')
print(f'  Marker size: {MARKER_SIZE*100:.1f} cm')
print(f'\nPRINTING INSTRUCTIONS:')
print('1. Print at 100% scale (no fit-to-page)')
print('2. Measure a square to verify it is 4cm x 4cm')
print('3. Mount on flat, rigid surface')
