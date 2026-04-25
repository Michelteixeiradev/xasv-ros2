import os
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import subprocess


def _launch_setup(context, *args, **kwargs):
    pkg_asv_gazebo = get_package_share_directory('asv_gazebo')
    pkg_asv_description = get_package_share_directory('asv_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_name = LaunchConfiguration('world').perform(context)
    headless = LaunchConfiguration('headless').perform(context).lower() in ('1', 'true', 'yes', 'on')

    world_file = world_name
    if not os.path.isabs(world_name):
        world_file = os.path.join(pkg_asv_gazebo, 'worlds', world_name)

    xacro_file = os.path.join(pkg_asv_description, 'urdf', 'migbot.urdf.xacro')
    robot_desc = subprocess.check_output(['xacro', xacro_file]).decode('utf-8')

    gz_args = f'-r {world_file}'
    if headless:
        gz_args = f'-s {gz_args}'

    # Variáveis de Ambiente para Estabilidade na VM
    set_libgl = SetEnvironmentVariable(name='LIBGL_ALWAYS_SOFTWARE', value='1')
    set_render = SetEnvironmentVariable(name='GZ_RENDERING_ENGINE_GUESS', value='ogre')

    resource_path = os.pathsep.join([
        pkg_asv_gazebo,
        os.path.join(pkg_asv_gazebo, 'models'),
        os.path.join(pkg_asv_gazebo, 'worlds'),
        os.path.join(get_package_prefix('asv_description'), 'share'),
    ])
    set_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[resource_path, os.pathsep, EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value='')]
    )

    # 1. Motor do simulador
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args}.items()
    )

    # 2. Publicador do estado do robô (para o RViz)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_desc}]
    )

    # 3. Spawn do barco no rio (x=100, y=20 é o centro do mapa madeira_river_simple)
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'migbot', '-string', robot_desc,
                   '-x', '100.0', '-y', '20.0', '-z', '0.3'],
        output='screen'
    )

    # 4. Ponte ROS <-> Gazebo (Controle + Sensores)
    world_base = os.path.splitext(os.path.basename(world_name))[0]

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Controle de Movimento (ROS -> Gazebo)
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            # Telemetria de Posição (Gazebo -> ROS)
            f'/world/{world_base}/pose/info@geometry_msgs/msg/PoseArray[gz.msgs.Pose_V',
            # Sensores (Gazebo -> ROS)
            f'/world/{world_base}/model/migbot/link/imu_link/sensor/imu_sensor/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
            f'/world/{world_base}/model/migbot/link/gps_link/sensor/navsat_sensor/navsat@sensor_msgs/msg/NavSatFix[gz.msgs.NavSat',
            f'/world/{world_base}/model/migbot/link/mag_link/sensor/magnetometer_sensor/magnetometer@sensor_msgs/msg/MagneticField[gz.msgs.Magnetometer',
        ],
        remappings=[
            (f'/world/{world_base}/pose/info', '/model/migbot/pose'),
            (f'/world/{world_base}/model/migbot/link/imu_link/sensor/imu_sensor/imu', '/imu'),
            (f'/world/{world_base}/model/migbot/link/gps_link/sensor/navsat_sensor/navsat', '/navsat'),
            (f'/world/{world_base}/model/migbot/link/mag_link/sensor/magnetometer_sensor/magnetometer', '/magnetometer'),
        ],
        output='screen'
    )

    return [
        set_libgl,
        set_render,
        set_resource_path,
        gazebo,
        robot_state_publisher,
        spawn_entity,
        bridge,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='madeira_river_simple.sdf'),
        DeclareLaunchArgument('headless', default_value='false'),
        OpaqueFunction(function=_launch_setup),
    ])