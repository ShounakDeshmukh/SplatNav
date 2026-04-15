from glob import glob

from setuptools import find_packages, setup

package_name = 'spin_robot_node'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.launch.py')),
        (f'share/{package_name}/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='Simple Python ROS 2 controller that publishes twist commands.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'spin_robot_node = spin_robot_node.spin_robot_node:main',
        ],
    },
)
