from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Este é o comando que aciona o nosso script Python
        Node(
            package='asv_mavlink',
            executable='mavlink_bridge_node.py',
            name='mavlink_bridge_node',
            output='screen'
        )
    ])