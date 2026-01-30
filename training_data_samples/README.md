# Training Data Samples - Pick and Place Red Cube

This folder contains sample images from the imitation learning dataset collected for training the Piper robotic arm to perform pick-and-place tasks with a red cube.

## Dataset Overview

- **Task:** Pick and place red cube
- **Robot:** Piper 6-DOF Arm
- **Camera:** Wrist-mounted RGB camera (640x480)
- **Recording FPS:** 30 Hz
- **Total Frames:** 3,582 frames
- **Episodes:** 1 demonstration episode

## Data Structure

Each frame contains:
- **action** (7 values): Joint commands for 6 joints + gripper
- **observation.state** (7 values): Current joint positions + gripper state
- **observation.images.wrist**: RGB image from wrist camera
- **timestamp**: Time since episode start

## Sample Images

The images in this folder show the progression of a pick-and-place episode:

| Frame | Description |
|-------|-------------|
| `episode1_START_frame_000000.png` | Initial position |
| `episode1_frame_000100.png` | Approaching cube |
| `episode1_frame_000200.png` | Near cube |
| `episode1_frame_000300.png` | Grasping |
| `episode1_frame_000400.png` | Lifting |
| `episode1_frame_000500.png` | Moving |
| `episode1_frame_000600.png` | Transporting |
| `episode1_frame_000700.png` | Approaching target |
| `episode1_frame_000800.png` | Placing |
| `episode1_frame_000900.png` | Releasing |
| `episode1_END_frame_000966.png` | Final position |

## Training Framework

This data was collected using [LeRobot](https://github.com/huggingface/lerobot) framework for imitation learning, training an ACT (Action Chunking Transformer) policy.

## Full Dataset

The complete dataset (787 MB) includes all frames and is stored locally. Contact for access to full dataset.
