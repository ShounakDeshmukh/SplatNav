from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('spin_robot_node')
    nav2_share = get_package_share_directory('nav2_bringup')

    params_file = os.path.join(pkg_share, 'config', 'nav2_nbv_params.yaml')
    nav2_bringup = os.path.join(nav2_share, 'launch', 'bringup_launch.py')

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_bringup),
        launch_arguments={
            'namespace': '',
            'slam': 'True',
            'map': '',
            'use_sim_time': 'True',
            'params_file': params_file,
            'autostart': 'True',
            'use_composition': 'False',
            'use_intra_process_comms': 'False',
            'use_respawn': 'False',
            'use_localization': 'True',
            'use_keepout_zones': 'False',
            'use_speed_zones': 'False',
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

    return LaunchDescription([nav2, bridge])