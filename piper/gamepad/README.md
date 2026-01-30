# Gamepad Teleoperation for Robotic Arm — Intuitive Control Experience

## Summary

This project enables intuitive robotic arm control using a game controller. With a standard gamepad, you can control the PiPER robotic arm in a visual environment, providing precise and intuitive control.

## Tags
PiPER Robotic Arm, Gamepad Teleoperation, Joint Control, Pose Control, Gripper Control, Forward/Inverse Kinematics

## Repository

- **Navigation Repository**: https://github.com/agilexrobotics/Agilex-College
- **Project Repository**: https://github.com/kehuanjack/Gamepad_PiPER

## Demo Video

[![](https://i.ytimg.com/an_webp/smTTbOfdTlk/mqdefault_6s.webp?du=3000&sqp=CJXS7McG&rs=AOn4CLBfiWjTsfz7kRpplE8f4Wx6WtDRlg)](https://youtu.be/smTTbOfdTlk)

## Environment Setup
- **Operating System**: Ubuntu 20.04 or higher

- **Python Environment**: Python 3.9 or higher, Anaconda or Miniconda recommended

- Clone the project and navigate to the project root:

   ```bash
   git clone https://github.com/kehuanjack/Gamepad_PiPER.git
   cd Gamepad_PiPER
   ```

- Install common dependencies and kinematics module dependencies (choose one of four options, pytracik recommended):

   - Based on [pinocchio](https://github.com/stack-of-tasks/pinocchio) library (Python == 3.9, requires [piper_ros](https://github.com/agilexrobotics/piper_ros) installation and sourcing the arm's ROS workspace, otherwise mesh files won't be found):

      ```bash
      conda create -n test_pinocchio python=3.9.* -y
      conda activate test_pinocchio
      pip3 install -r requirements_common.txt --upgrade
      conda install pinocchio=3.6.0 -c conda-forge
      pip install meshcat
      pip install casadi
      ```

      Select `from src.gamepad_pin import RoboticArmController` in `main.py` and `main_virtual.py`

   - Based on [PyRoKi](https://github.com/chungmin99/pyroki) library (Python >= 3.10):

      ```bash
      conda create -n test_pyroki python=3.10.* -y
      conda activate test_pyroki
      pip3 install -r requirements_common.txt --upgrade
      pip3 install pyroki@git+https://github.com/chungmin99/pyroki.git@f234516
      ```

      Select `from src.gamepad_limit import RoboticArmController` or `from src.gamepad_no_limit import RoboticArmController` in `main.py` and `main_virtual.py`

   - Based on [cuRobo](https://github.com/NVlabs/curobo) library (Python >= 3.8, CUDA 11.8 recommended):

      ```bash
      conda create -n test_curobo python=3.10.* -y
      conda activate test_curobo
      pip3 install -r requirements_common.txt --upgrade
      sudo apt install git-lfs && cd ../
      git clone https://github.com/NVlabs/curobo.git && cd curobo
      pip3 install "numpy<2.0" "torch==2.0.0" pytest lark
      pip3 install -e . --no-build-isolation
      python3 -m pytest .
      cd ../Gamepad_PiPER
      ```

      Select `from src.gamepad_curobo import RoboticArmController` in `main.py` and `main_virtual.py`

   - Based on [pytracik](https://github.com/chenhaox/pytracik) library (Python >= 3.10):

      ```bash
      conda create -n test_tracik python=3.10.* -y
      conda activate test_tracik
      pip3 install -r requirements_common.txt --upgrade
      git clone https://github.com/chenhaox/pytracik.git
      cd pytracik
      pip install -r requirements.txt
      sudo apt install g++ libboost-all-dev libeigen3-dev liborocos-kdl-dev libnlopt-dev libnlopt-cxx-dev
      python setup_linux.py install --user
      ```

      Select `from src.gamepad_trac_ik import RoboticArmController` in `main.py` and `main_virtual.py`

## Execution Steps

1. **Connect the arm and activate the CAN module**: `sudo ip link set can0 up type can bitrate 1000000`

2. **Connect the gamepad**: Connect the controller to the computer via USB or Bluetooth

3. **Start the control service**: Run `python3 main.py` or `python3 main_virtual.py` in the project directory. It's recommended to run `main_virtual.py` first to test with the virtual arm

4. **Verify gamepad connection**: After the program starts, check the console output to confirm the gamepad is correctly recognized

5. **Web visualization**: Open a browser and go to `http://localhost:8080` to visualize the arm state

6. **Start controlling**: Operate the arm according to the button mapping below

## Gamepad Control Guide

### Button Function Mapping

| Button | Short Press | Long Press |
|--------|-------------|------------|
| **HOME** | Connect/disconnect arm | None |
| **START** | Toggle high-level control mode (Joint/Pose) | Toggle low-level control mode (Joint/Pose) |
| **BACK** | Toggle low-level command mode (Position-Velocity 0x00/Fast Response 0xAD) | None |
| **Y** | Return to home position | None |
| **A** | Save current position | Clear current saved position |
| **B** | Restore previous saved position | None |
| **X** | Toggle position playback order | Clear all saved positions |
| **LB** | Increase speed factor (high-level) | Decrease speed factor (high-level) |
| **RB** | Increase movement speed (low-level) | Decrease movement speed (low-level) |

### Joystick and Trigger Functions

| Control Element | Joint Mode Function | Pose Mode Function |
|-----------------|---------------------|-------------------|
| **Left Stick** | J1 (Base rotation): Left/Right<br/>J2 (Upper arm): Up/Down | End-effector X/Y axis movement |
| **Right Stick** | J3 (Forearm): Up/Down<br/>J6 (Wrist rotation): Left/Right | End-effector Z axis movement and Z-axis rotation |
| **D-Pad** | J4 (Wrist yaw): Left/Right<br/>J5 (Wrist pitch): Up/Down | End-effector X/Y axis rotation |
| **Left Trigger (LT)** | Close gripper | Close gripper |
| **Right Trigger (RT)** | Open gripper | Open gripper |

### Special Features

1. **Gripper Control**:
   - Gripper opening range: 0-100%
   - Quick toggle: When gripper is fully closed (0%) or fully open (100%), quickly pressing and releasing the trigger toggles the state

2. **Speed Control**:
   - Speed factors: 0.25x, 0.5x, 1.0x, 2.0x, 3.0x, 4.0x, 5.0x (toggle with LB)
   - Movement speed: 10%-100% (toggle with RB)

3. **Position Memory**:
   - Can save multiple position points
   - Supports forward and reverse playback

## Safety Notes

- It's recommended to run `main_virtual.py` first to test with the virtual arm
- First-time users should start with low speed mode and increase speed after familiarization
- Maintain a safe distance while the arm is operating. Do not approach the moving arm
- Numerical solutions may cause large joint movements near singularities. Maintain safe distance
- Fast response mode (0xAD) is dangerous. Use with caution and maintain safe distance
- If using the pinocchio library, you must source the arm's ROS workspace first, otherwise mesh files won't be found

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=kehuanjack/Gamepad_PiPER&type=date&legend=top-left)](https://www.star-history.com/#kehuanjack/Gamepad_PiPER&type=date&legend=top-left)
