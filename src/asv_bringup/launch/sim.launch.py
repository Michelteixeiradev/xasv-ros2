import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def _launch_setup(context, *args, **kwargs):
    pkg_asv_gazebo = get_package_share_directory('asv_gazebo')
    pkg_asv_description = get_package_share_directory('asv_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_name = LaunchConfiguration('world').perform(context)
    headless = LaunchConfiguration('headless').perform(context).lower() in ('1', 'true', 'yes', 'on')

    world_file = world_name
    if not os.path.isabs(world_name):
        world_file = os.path.join(pkg_asv_gazebo, 'worlds', world_name)

    urdf_file = os.path.join(pkg_asv_description, 'urdf', 'dummy_boat.urdf')

    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    gz_args = f'-r {world_file}'
    if headless:
        gz_args = f'-s {gz_args}'

    # Variáveis de Ambiente para Estabilidade na VM (Salvando a performance)
    set_libgl = SetEnvironmentVariable(name='LIBGL_ALWAYS_SOFTWARE', value='1')
    set_render = SetEnvironmentVariable(name='GZ_RENDERING_ENGINE_GUESS', value='ogre')

    resource_path = os.pathsep.join([
        pkg_asv_gazebo,
        os.path.join(pkg_asv_gazebo, 'models'),
        os.path.join(pkg_asv_gazebo, 'worlds'),
    ])

    set_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[
            resource_path,
            os.pathsep,
            EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value=''),
        ],
    )

    # 1. O motor do simulador
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': gz_args}.items()
    )

    # 2. Publicador do estado do robô (para o RViz ver)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_desc}]
    )

    # 3. Spawn do barco no mundo
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'dummy_boat',
                   '-string', robot_desc,
                   '-x', '0.0',
                   '-y', '0.0',
                   '-z', '1.5'], 
        output='screen'
    )

    # 4. A PONTE (O que você validou hoje!)
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Comando de Movimento (ROS -> Gazebo)
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            # Telemetria de Posição (Gazebo -> ROS)
            '/world/empty_ocean/pose/info@geometry_msgs/msg/PoseArray[gz.msgs.Pose_V'
        ],
        remappings=[
            ('/world/empty_ocean/pose/info', '/model/dummy_boat/pose'),
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
        bridge
    ]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value='empty_ocean.sdf',
            description='World file name in asv_gazebo/worlds or an absolute path.',
        ),
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='Run Gazebo server only (-s) if true.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])