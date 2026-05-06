from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'asv_mavlink'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Ensina onde estão os arquivos de launch
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Michel Kleyton',
    maintainer_email='michel@email.com',
    description='Pacote de integracao com MAVLink e ArduPilot SITL',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Mapeia o seu script Python para ser um executável do ROS 2
            'mavlink_bridge_node.py = asv_mavlink.mavlink_bridge_node:main',
            'fase7_sanity_check = asv_mavlink.fase7_sanity_check:main',
        ],
    },
)
