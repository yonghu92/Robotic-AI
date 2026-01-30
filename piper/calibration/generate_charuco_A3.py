#!/usr/bin/env python3
"""
Generate ChArUco calibration boards for A3 and A4 paper.
Print at 100% scale (no scaling).
"""

import cv2
import numpy as np
import os

output_dir = '/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/calibration'

# A3 Board (297mm x 420mm) - RECOMMENDED
# Using 6x8 squares with 5cm squares
A3_SQUARES_X = 6
A3_SQUARES_Y = 8
A3_SQUARE_SIZE = 0.05  # 5cm squares
A3_MARKER_SIZE = 0.038  # 3.8cm markers

# A4 Board (210mm x 297mm)
# Using 6x9 squares with 3.0cm squares (user's printed board)
A4_SQUARES_X = 6
A4_SQUARES_Y = 9
A4_SQUARE_SIZE = 0.03   # 3.0cm squares
A4_MARKER_SIZE = 0.023  # 2.3cm markers (77% of square size)

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

def generate_board(squares_x, squares_y, square_size, marker_size, paper_name, dpi=300):
    board = cv2.aruco.CharucoBoard(
        (squares_x, squares_y),
        square_size,
        marker_size,
        dictionary
    )

    # Calculate image size based on paper size at given DPI
    if paper_name == 'A3':
        # A3 = 297mm x 420mm, leave 10mm margin each side
        width_mm = 277
        height_mm = 400
    else:  # A4
        # A4 = 210mm x 297mm, leave 10mm margin each side
        width_mm = 190
        height_mm = 277

    width_px = int(width_mm * dpi / 25.4)
    height_px = int(height_mm * dpi / 25.4)

    board_image = board.generateImage((width_px, height_px))

    return board_image, board

# Generate A3 board
print("Generating A3 ChArUco board...")
a3_image, a3_board = generate_board(A3_SQUARES_X, A3_SQUARES_Y, A3_SQUARE_SIZE, A3_MARKER_SIZE, 'A3')
a3_path = os.path.join(output_dir, 'charuco_board_A3.png')
cv2.imwrite(a3_path, a3_image)

# Generate A4 board
print("Generating A4 ChArUco board...")
a4_image, a4_board = generate_board(A4_SQUARES_X, A4_SQUARES_Y, A4_SQUARE_SIZE, A4_MARKER_SIZE, 'A4')
a4_path = os.path.join(output_dir, 'charuco_board_A4.png')
cv2.imwrite(a4_path, a4_image)

# Save configuration file
config = f"""# ChArUco Board Calibration Parameters
# Use these values in hand_eye_calibration.py

# A3 Board (RECOMMENDED - larger = more accurate)
A3:
  squares_x: {A3_SQUARES_X}
  squares_y: {A3_SQUARES_Y}
  square_size_meters: {A3_SQUARE_SIZE}
  marker_size_meters: {A3_MARKER_SIZE}
  file: charuco_board_A3.png

# A4 Board
A4:
  squares_x: {A4_SQUARES_X}
  squares_y: {A4_SQUARES_Y}
  square_size_meters: {A4_SQUARE_SIZE}
  marker_size_meters: {A4_MARKER_SIZE}
  file: charuco_board_A4.png

# PRINTING INSTRUCTIONS:
# 1. Print at 100% scale (NO fit-to-page, NO scaling)
# 2. After printing, measure a square with ruler:
#    - A3: should be 5.0 cm x 5.0 cm
#    - A4: should be 3.0 cm x 3.0 cm
# 3. If size is wrong, adjust printer settings and reprint
# 4. Mount on flat, rigid surface (cardboard, foam board)
# 5. For 2-board setup: place both boards in workspace for better coverage
"""

config_path = os.path.join(output_dir, 'charuco_config.yaml')
with open(config_path, 'w') as f:
    f.write(config)

print(f"""
{'='*60}
  CHARUCO BOARDS GENERATED
{'='*60}

A3 Board (RECOMMENDED):
  File: {a3_path}
  Squares: {A3_SQUARES_X} x {A3_SQUARES_Y}
  Square size: {A3_SQUARE_SIZE*100:.1f} cm

A4 Board:
  File: {a4_path}
  Squares: {A4_SQUARES_X} x {A4_SQUARES_Y}
  Square size: {A4_SQUARE_SIZE*100:.1f} cm

Config: {config_path}

PRINTING INSTRUCTIONS:
1. Open the PNG file
2. Print at 100% scale (NO fit-to-page)
3. Measure a square - it should match the size above
4. Mount on cardboard or rigid surface
{'='*60}
""")
