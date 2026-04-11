import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Pegando os caminhos das pastas onde instalamos as coisas
    pkg_asv_gazebo = get_package_share_directory('asv_gazebo')
    pkg_asv_description = get_package_share_directory('asv_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # 2. Definindo os arquivos exatos que queremos usar
    # Mude esta linha:
    world_file = os.path.join(pkg_asv_gazebo, 'worlds', 'madeira_river.sdf')
    urdf_file = os.path.join(pkg_asv_description, 'urdf', 'dummy_boat.urdf')

    # Lendo o arquivo URDF como texto para mandar para os nós
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    # 3. AÇÃO: Iniciar o simulador Gazebo com o nosso oceano
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_file}'}.items()
    )

    # 4. AÇÃO: Iniciar o robot_state_publisher (Obrigatório em ROS2)
    # Ele pega o texto do URDF e calcula as transformações (TF) do robô
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_desc}]
    )

    # 5. AÇÃO: Fazer o "spawn" (surgimento) do barco dentro do Gazebo
    # Nós soltamos ele em z=0.5 (meio metro de altura) para ele cair na água
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'dummy_boat',
                   '-string', robot_desc,
                   '-x', '0.0',
                   '-y', '0.0',
                   '-z', '0.5'],
        output='screen'
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'],
        output='screen'
    )
    # O Maestro retorna a lista de tarefas para o sistema executar
    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_entity,
        bridge
    ])