from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import os

def generate_launch_description():
    # Get URDF file path - try multiple locations
    urdf_paths = [
        os.path.join(os.path.expanduser('~'), 'Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper.urdf'),
        os.path.join(os.path.expanduser('~'), 'Documents/Robotic AI/Robotic-AI/piper/gamepad/piper/piper_local.urdf'),
        os.path.join(os.path.expanduser('~'), 'Documents/Robotic AI/Robotic-AI/piper/handpose_det/models/modified_piper_without_camera.urdf'),
        os.path.join(os.path.expanduser('~'), 'Documents/Robotic AI/Robotic-AI/piper/handpose_det/models/modified_piper.urdf'),
    ]
    
    urdf_path = None
    for path in urdf_paths:
        if os.path.exists(path):
            urdf_path = path
            print(f"Using URDF: {urdf_path}")
            break
    
    if urdf_path is None:
        print("ERROR: No URDF file found in expected locations!")
        urdf_path = urdf_paths[0]  # Default to first path for error message
    
    # Read URDF file
    try:
        with open(urdf_path, 'r') as f:
            robot_description = f.read()
    except FileNotFoundError:
        print(f"Warning: URDF file not found at {urdf_path}")
        robot_description = ""
    
    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False,
        }]
    )
    
    return LaunchDescription([
        robot_state_publisher,
    ])
