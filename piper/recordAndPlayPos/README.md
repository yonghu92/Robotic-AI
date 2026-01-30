# Robotic Arm Fixed Position Recording and Playback

## Summary
This document provides two Python scripts (`recordPos.py` and `playPos.py`) for recording and playing back fixed positions of the Piper robotic arm. Through simple operations, users can record the arm's joint positions and gripper state, and play back these actions when needed.

## Features
- **Recording Function** (`recordPos.py`): Real-time recording of joint angles and gripper open/close state.
- **Playback Function** (`playPos.py`): Reads the recorded position file and controls the arm to reproduce the actions.
- **Safety Mechanisms**: Includes timeout detection, emergency stop recovery, and joint limit protection for safe operation.
- **Flexible Configuration**: Supports setting playback count, interval time, movement speed, and other parameters.

## Environment Setup
- **Operating System**: Ubuntu (Ubuntu 18.04 or higher recommended)
- **Python Environment**: Python 3.6 or higher
- **Install CAN Tools**

    ```bash
    sudo apt install can-utils ethtool
    ```

- **Install piper_sdk**: Version 1_0_0_beta includes the API

    ```bash
    git clone -b 1_0_0_beta https://github.com/agilexrobotics/piper_sdk.git
    cd piper_sdk
    pip3 install .
    ```

- **Reference Documentation**: https://github.com/agilexrobotics/piper_sdk/blob/1_0_0_beta/README(ZH).MD

## Usage

### 1. Record Fixed Positions
```bash
python3 recordPos.py
```
- Follow the prompts to enable teach mode after running.
- Press Enter to record current position, type `q` to exit recording.
- Positions are saved to `pos.csv` in the same directory.

### 2. Play Fixed Positions
```bash
python3 playPos.py
```
- Ensure the arm has exited teach mode.
- Press Enter to start playback; the arm will move through positions in recorded order.
- Playback count, interval time, etc. can be adjusted via script parameters.

## Parameter Reference (Adjustable in Scripts)
### recordPos.py / recordPos_en.py
- `have_gripper`: Enable gripper (default `True`)
- `timeout`: Teach mode detection timeout (seconds)

### playPos.py / playPos_en.py
- `have_gripper`: Enable gripper (default `True`)
- `play_times`: Number of playback repetitions (0 = infinite loop)
- `play_interval`: Interval between positions (negative value requires manual confirmation)
- `move_spd_rate_ctrl`: Movement speed percentage (recommended 10-100)
- `timeout`: CAN mode switch timeout (seconds)

## Detailed Steps
1. Power on the arm and connect the USB-to-CAN module to the computer (ensure only one CAN module is connected)

2. Open a terminal and activate the CAN module

    `sudo ip link set can0 up type can bitrate 1000000`

3. Clone the remote repository

    `git clone https://github.com/agilexrobotics/Agilex-College.git`

4. Navigate to the `recordAndPlayPos` directory

    `cd Agilex-College/piper/recordAndPlayPos/`

5. Run the recording program

    `python3 recordPos.py`

6. Short-press the teach button to enter teach mode

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1755248955456-fd0ddf6b-ef48-4f04-a13b-4352c8ab955a.png)

7. Position the arm, press Enter in the terminal to record the position, type 'q' to end recording
    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1752636233531-3e033cff-4df6-4b0c-81e8-0a2a85bddefc.png)

8. After recording, short-press the teach button again to exit teach mode

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1755248964459-86f52f95-f5e1-49d2-8f0a-9c556b1b795b.png)

9. Pre-playback notice: When exiting teach mode for the first time, a specific initialization process is required to switch from teach mode to CAN mode. Therefore, the playback program will automatically perform a reset operation, returning joints 2, 3, and 5 to safe positions (zero point) to prevent the arm from suddenly falling under gravity. In special cases, manual assistance may be needed to return joints 2, 3, and 5 to zero.

10. Run the playback program

    `python3 playPos.py`

11. After successful enabling, press Enter in the terminal to play the positions

    ![](https://cdn.nlark.com/yuque/0/2025/png/51616906/1752636446142-96b80428-877d-43f3-9f33-ae6eacdbaab7.png)
