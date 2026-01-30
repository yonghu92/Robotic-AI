# Robotic Arm Continuous Trajectory Recording and Playback

## Summary
This document provides two Python scripts (`recordTrajectory_new` and `playTrajectory_new`) for recording and playing back continuous motion trajectories of the Piper robotic arm. Unlike point-based recording, this system captures time interval information during arm movement, enabling smoother and more natural motion reproduction.

## Features
- **Continuous Trajectory Recording** (`recordTrajectory_new.py`): Real-time recording of joint angles, gripper state, and time intervals during arm motion
- **Precise Trajectory Playback** (`playTrajectory_new.py`): Reproduces arm motion according to the recorded timing relationships
- **Speed Control**: Supports playback speed adjustment (0.1x-2x) for flexible playback rhythm
- **Safety Mechanisms**: Includes timeout detection, emergency stop recovery, and joint limit protection for safe operation

## Environment Setup
- **Operating System**: Ubuntu (Ubuntu 18.04 or higher recommended)
- **Python Environment**: Python 3.6 or higher
- **Install CAN Tools**

    ```bash
    sudo apt install can-utils ethtool
    ```

- **Install piper_sdk**:

    ```bash
    pip3 install piper_sdk
    ```

- **Reference Documentation**: https://github.com/agilexrobotics/piper_sdk/blob/master/README(ZH).MD

## Usage

### 1. Record Continuous Trajectory
```bash
python3 recordTrajectory_new.py
```
- Follow the prompts to enable teach mode after running
- Press Enter to start recording; trajectory points are automatically recorded as the arm moves
- After recording, data is automatically saved to `trajectory.csv`
- Recording duration can be set via the `record_time` parameter (0 = unlimited)

### 2. Play Continuous Trajectory
```bash
python3 playTrajectory_new.py
```
- Ensure the arm has exited teach mode
- Press Enter to start playback; the arm will reproduce the motion according to recorded timing
- Playback speed, repetitions, etc. can be adjusted via script parameters

## Parameter Reference (Adjustable in Scripts)

### recordTrajectory_new.py / recordTrajectory_new_en.py
- `have_gripper`: Enable gripper (default `True`)
- `record_time`: Maximum recording time in seconds (0 = unlimited)
- `timeout`: Teach mode detection timeout in seconds

### playTrajectory_new.py / playTrajectory_new_en.py
- `have_gripper`: Enable gripper (default `True`)
- `play_times`: Number of playback repetitions (0 = infinite loop)
- `play_interval`: Interval between playbacks in seconds
- `move_spd_rate_ctrl`: Movement speed percentage (recommended 10-100)
- `play_speed`: Playback speed multiplier (recommended range: 0.1-2)
- `timeout`: CAN mode switch timeout in seconds

## Detailed Steps
1. Power on the arm and connect the USB-to-CAN module to the computer (ensure only one CAN module is connected)

2. Open a terminal and activate the CAN module

    `sudo ip link set can0 up type can bitrate 1000000`

3. Clone the remote repository

    `git clone https://github.com/agilexrobotics/Agilex-College.git`

4. Navigate to the `recordAndPlayTraj` directory

    `cd Agilex-College/piper/recordAndPlayTraj/`

5. Run the recording program

    `python3 recordTrajectory_new.py`

6. Short-press the teach button to enter teach mode

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1755248995720-91c32fef-8189-48a9-9a1d-698dede6c9b5.png)

7. Position the arm at the initial position, press Enter in the terminal, then drag the arm to record the trajectory

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1752571795765-29a3bc22-5c15-47ec-9d03-09939eb74290.png)

8. After recording, short-press the teach button again to exit teach mode

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1755249001510-aa36e773-4b75-4e7e-85b6-f48a2d4f2950.png)

9. Pre-playback notice:
When exiting teach mode for the first time, a specific initialization process is required to switch from teach mode to CAN mode. Therefore, the playback program will automatically perform a reset operation, returning joints 2, 3, and 5 to safe positions (zero point) to prevent the arm from suddenly falling under gravity. In special cases, manual assistance may be needed to return joints 2, 3, and 5 to zero.

10. Run the playback program

    `python3 playTrajectory_new.py`

11. After successful enabling, press Enter in the terminal to play the trajectory

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1752572703619-b75279b1-b93e-41a0-930e-05af4088abd4.png)
