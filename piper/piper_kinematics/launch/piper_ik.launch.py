from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Declare launch arguments
    max_iterations_arg = DeclareLaunchArgument(
        'max_iterations',
        default_value='50',
        description='Maximum iterations for IK solver'
    )
    
    damping_factor_arg = DeclareLaunchArgument(
        'damping_factor',
        default_value='0.1',
        description='Damping factor for IK solver'
    )
    
    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='30',
        description='Publish rate in Hz'
    )
    
    use_analytic_ik_arg = DeclareLaunchArgument(
        'use_analytic_ik',
        default_value='false',
        description='Use analytical IK solver'
    )

    # IK Node (C++ - needs conversion)
    # piper_ik_node = Node(
    #     package='piper_kinematics',
    #     executable='piper_ik_node',
    #     name='piper_ik_node',
    #     output='screen',
    #     parameters=[{
    #         'max_iterations': LaunchConfiguration('max_iterations'),
    #         'damping_factor': LaunchConfiguration('damping_factor'),
    #         'publish_rate': LaunchConfiguration('publish_rate'),
    #         'use_analytic_ik': LaunchConfiguration('use_analytic_ik'),
    #     }]
    # )

    # Interactive pose marker node (Python - converted)
    interactive_pose_marker_node = Node(
        package='piper_kinematics',
        executable='interactive_pose_marker.py',
        name='interactive_pose_marker_node',
        output='screen',
        parameters=[{
            'marker_name': 'target_pose',
            'reference_frame': 'base_link',
            'initial_position': [0.5, 0.0, 0.5],
            'marker_scale': 0.2,
            'pose_topic': '/target_pose',
        }]
    )

    return LaunchDescription([
        max_iterations_arg,
        damping_factor_arg,
        publish_rate_arg,
        use_analytic_ik_arg,
        # piper_ik_node,  # Uncomment when C++ code is converted
        interactive_pose_marker_node,
    ])
