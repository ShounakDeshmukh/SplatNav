from __future__ import annotations

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description() -> LaunchDescription:
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('clearpath_nav2_demos'),
                'launch',
                'nav2.launch.py',
            ])
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'setup_path': '/root/clearpath',
        }.items(),
    )

    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('clearpath_nav2_demos'),
                'launch',
                'slam.launch.py',
            ])
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'setup_path': '/root/clearpath',
        }.items(),
    )

    bridge = Node(
        package='spin_robot_node',
        executable='nbv_nav2_bridge',
        name='nbv_nav2_bridge',
        output='screen',
        parameters=[{
            'nbv_topic': '/gaussmi/nbv_pose',
            'goal_frame': 'map',
            'navigate_action': '/navigate_to_pose',
        }],
    )

    return LaunchDescription([nav2_launch, slam_launch, bridge])
