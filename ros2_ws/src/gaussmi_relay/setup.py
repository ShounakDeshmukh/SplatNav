from setuptools import find_packages, setup


package_name = "gaussmi_relay"


setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=("test",)),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="GitHub Copilot",
    maintainer_email="sdeshmu4@example.com",
    description="Socket relay between ROS 2 Jazzy and ROS 1 GauSS-MI.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "ros2_side = gaussmi_relay.ros2_side:main",
        ],
    },
)
