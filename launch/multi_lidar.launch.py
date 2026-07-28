import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch_ros.actions import Node


def static_tf(name, child_frame):
    return Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name=name,
        arguments=[
            "--x", "0",
            "--y", "0",
            "--z", "0",
            "--roll", "0",
            "--pitch", "0",
            "--yaw", "0",
            "--frame-id", "base_link",
            "--child-frame-id", child_frame,
        ],
        output="screen",
    )


def generate_launch_description():
    foxglove_share = get_package_share_directory(
        "foxglove_bridge"
    )

    foxglove_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                foxglove_share,
                "launch",
                "foxglove_bridge_launch.xml",
            )
        ),
        launch_arguments={
            "port": "8765",
        }.items(),
    )

    lidar_manager = ExecuteProcess(
        cmd=[
            "ros2",
            "run",
            "multi_lidar_bringup",
            "multi_lidar_manager",
        ],
        output="screen",
        respawn=True,
        respawn_delay=3.0,
    )

    tf_gs2_1 = static_tf(
        "tf_base_to_gs2_1",
        "gs2_1_frame",
    )

    tf_gs2_2 = static_tf(
        "tf_base_to_gs2_2",
        "gs2_2_frame",
    )

    tf_tg30 = static_tf(
        "tf_base_to_tg30",
        "tg30_frame",
    )

    return LaunchDescription([
        lidar_manager,
        foxglove_launch,
        tf_gs2_1,
        tf_gs2_2,
        tf_tg30,
    ])
