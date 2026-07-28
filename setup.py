from glob import glob
from setuptools import find_packages, setup


package_name = "multi_lidar_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
        (
            "share/" + package_name + "/launch",
            glob("launch/*.launch.py"),
        ),
        (
            "share/" + package_name + "/config",
            glob("config/*.yaml"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="yeonwoo",
    maintainer_email="yeonwoo@example.com",
    description=(
        "Automatic discovery and startup for GS2 and TG30 LiDAR sensors"
    ),
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            (
                "device_discovery = "
                "multi_lidar_bringup.device_discovery:main"
            ),
            (
                "multi_lidar_manager = "
                "multi_lidar_bringup.manager:main"
            ),
        ],
    },
)
