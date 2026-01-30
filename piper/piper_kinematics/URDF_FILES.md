# Available Piper URDF Files

## Found URDF Files:

1. **`piper/gamepad/piper/piper.urdf`** (14KB) - Main URDF file
   - Location: `~/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf`
   - Has `base_footprint` and `base_link`
   - Full robot model

2. **`piper/gamepad/piper/piper_local.urdf`** (13KB)
   - Location: `~/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper_local.urdf`
   - Similar to main URDF

3. **`piper/handpose_det/models/modified_piper_without_camera.urdf`** (14KB)
   - Location: `~/Documents/Robotic AI/Robotic-AI/piper/handpose_det/models/modified_piper_without_camera.urdf`
   - Modified version without camera
   - Uses `dummy_link` as root

4. **`piper/handpose_det/models/modified_piper.urdf`** (13KB)
   - Location: `~/Documents/Robotic AI/Robotic-AI/piper/handpose_det/models/modified_piper.urdf`
   - Modified version with camera

## Which One to Use?

The launch files (`piper_ik_with_robot.launch.py` and `display_robot.launch.py`) will automatically try all of them in order and use the first one that exists.

**Recommended:** `piper.urdf` (the main one) - this is tried first.

## Usage

The launch files will automatically find and use the URDF:

```bash
ros2 launch piper_kinematics piper_ik_with_robot.launch.py
```

It will print which URDF file it's using:
```
Using URDF: /home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf
```

## Manual Override

If you want to use a specific URDF, edit the launch file and change the order in `urdf_paths` list, or set `urdf_path` directly.
