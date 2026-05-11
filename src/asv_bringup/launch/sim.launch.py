import os
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import subprocess


def _launch_setup(context, *args, **kwargs):
    pkg_asv_gazebo = get_package_share_directory('asv_gazebo')
    pkg_asv_description = get_package_share_directory('asv_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_name = LaunchConfiguration('world').perform(context)
    headless = LaunchConfiguration('headless').perform(context).lower() in ('1', 'true', 'yes', 'on')
    ardupilot = LaunchConfiguration('ardupilot')
    use_mavlink_bridge = LaunchConfiguration('use_mavlink_bridge')

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
    ardupilot_gazebo_dir = os.path.expanduser('~/ardupilot_gazebo')
    resource_path = os.pathsep.join([
        resource_path,
        os.path.join(ardupilot_gazebo_dir, 'models'),
        os.path.join(ardupilot_gazebo_dir, 'worlds'),
    ])
    set_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[resource_path, os.pathsep, EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value='')]
    )

    # ArduPilotPlugin (build do ardupilot_gazebo) — necessario para a Fase 7B carregar o plugin no URDF.
    set_plugin_path = SetEnvironmentVariable(
        name='GZ_SIM_SYSTEM_PLUGIN_PATH',
        value=[os.path.join(ardupilot_gazebo_dir, 'build'), os.pathsep,
               EnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH', default_value='')]
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
    # NOTE: -R 3.14159 (roll 180°) força o casco pra baixo. O CAD foi exportado
    # com hélices em Z=+0.66 (acima do casco), o que invertia o equilíbrio
    # natural do Gazebo e fazia o barco nascer de cabeça pra baixo.
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'migbot', '-string', robot_desc,
                   '-x', '100.0', '-y', '20.0', '-z', '0.3',
                   '-R', '3.14159'],
        output='screen'
    )

    # 4. Ponte ROS <-> Gazebo (Controle + Sensores)
    world_base = os.path.splitext(os.path.basename(world_name))[0]

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Motores / Thrusters (ROS -> Gazebo)
            '/model/migbot/joint/Engine_helice_1/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_2/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_3/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_4/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_5/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_6/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double',
            # Feedback dos thrusters (Gazebo -> ROS), usado pelo sanity check da Fase 7.
            '/model/migbot/joint/Engine_helice_1/force@std_msgs/msg/Float64[gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_2/force@std_msgs/msg/Float64[gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_3/force@std_msgs/msg/Float64[gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_4/force@std_msgs/msg/Float64[gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_5/force@std_msgs/msg/Float64[gz.msgs.Double',
            '/model/migbot/joint/Engine_helice_6/force@std_msgs/msg/Float64[gz.msgs.Double',
            # Telemetria de Posição (Gazebo -> ROS)
            f'/world/{world_base}/pose/info@geometry_msgs/msg/PoseArray[gz.msgs.Pose_V',
            # Sensores (Gazebo -> ROS) - Mantidos para comparação com AP_DDS
            f'/world/{world_base}/model/migbot/link/base_link/sensor/imu_sensor/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
            f'/world/{world_base}/model/migbot/link/base_link/sensor/navsat_sensor/navsat@sensor_msgs/msg/NavSatFix[gz.msgs.NavSat',
            f'/world/{world_base}/model/migbot/link/base_link/sensor/magnetometer_sensor/magnetometer@sensor_msgs/msg/MagneticField[gz.msgs.Magnetometer',
        ],
        remappings=[
            (f'/world/{world_base}/pose/info', '/model/migbot/pose'),
            (f'/world/{world_base}/model/migbot/link/base_link/sensor/imu_sensor/imu', '/imu'),
            (f'/world/{world_base}/model/migbot/link/base_link/sensor/navsat_sensor/navsat', '/navsat'),
            (f'/world/{world_base}/model/migbot/link/base_link/sensor/magnetometer_sensor/magnetometer', '/magnetometer'),
        ],
        output='screen'
    )

    # 5. micro-ros-agent (AP_DDS)
    # Usa bash -c para garantir que o workspace do micro_ros_agent seja sourced
    micro_ros_agent_cmd = ['bash', '-c', 'source ~/micro_ros_ws/install/setup.bash && ros2 run micro_ros_agent micro_ros_agent udp4 -p 2019']
    
    micro_ros_agent = ExecuteProcess(
        cmd=micro_ros_agent_cmd,
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        condition=IfCondition(ardupilot)
    )

    # O Thruster do Gazebo nao observa a velocidade real da junta quando
    # use_angvel_cmd=true; ele escuta /model/.../cmd_vel. Esta ponte le os
    # SERVO_OUTPUT_RAW do ArduPilot e publica esses comandos de velocidade.
    mavlink_bridge = Node(
        package='asv_mavlink',
        executable='mavlink_bridge_node.py',
        name='mavlink_bridge_node',
        output='screen',
        parameters=[{'connection': 'udpin:0.0.0.0:14555'}],
        condition=IfCondition(PythonExpression([
            "'", ardupilot, "'.lower() in ['1', 'true', 'yes', 'on'] and '",
            use_mavlink_bridge, "'.lower() in ['1', 'true', 'yes', 'on']"
        ]))
    )

    # 6. ArduPilot SITL com suporte DDS
    # --no-rebuild: usa o binario ja compilado em ~/ardupilot/build/sitl/bin/ardurover.
    # Evita travar no waf por incompatibilidade do microxrceddsgen instalado.
    sitl_param_file = os.path.expanduser('~/ros2_asv_ws/xasv-ros2/config/migbot_sitl.param')
    sitl_cmd = [
        'python3', os.path.expanduser('~/ardupilot/Tools/autotest/sim_vehicle.py'),
        '-v', 'Rover', '-f', 'JSON', '-w', '--console', '--map', '--enable-DDS', '--no-rebuild',
        '--add-param-file', sitl_param_file,
        '-l', '-8.798638,-63.952087,58,0',
        '--out=udp:127.0.0.1:14550',
        '--out=udp:127.0.0.1:14555'
    ]
    
    # Garantir que o microxrceddsgen esteja no PATH
    sitl_env = os.environ.copy()
    sitl_env['PATH'] = os.path.expanduser('~/Micro-XRCE-DDS-Gen/scripts') + os.pathsep + sitl_env.get('PATH', '')

    sitl_process = ExecuteProcess(
        cmd=sitl_cmd,
        cwd=os.path.expanduser('~/ardupilot'),
        env=sitl_env,
        output='screen',
        condition=IfCondition(ardupilot)
    )

    # Ordem de subida:
    # - Gazebo/ArduPilotPlugin: t=0 (precisa estar pronto antes do SITL no socket JSON 9002).
    # - micro-ros-agent: t=10s (precisa estar listening em udp4:2019 ANTES do SITL pingar,
    #   senao SITL solta "DDS: No ping response, exiting" e desiste).
    # - SITL: t=18s (Gazebo + agent ja prontos).
    # - MAVLink bridge: t=28s (espera SITL abrir saida UDP 14555).
    delayed_micro_ros_agent = TimerAction(period=10.0, actions=[micro_ros_agent])
    delayed_sitl = TimerAction(period=18.0, actions=[sitl_process])
    delayed_mavlink_bridge = TimerAction(period=28.0, actions=[mavlink_bridge])

    return [
        set_libgl,
        set_render,
        set_resource_path,
        set_plugin_path,
        gazebo,
        robot_state_publisher,
        spawn_entity,
        bridge,
        delayed_micro_ros_agent,
        delayed_sitl,
        delayed_mavlink_bridge,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='madeira_river_simple.sdf'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('ardupilot', default_value='false', description='Lancar ArduPilot SITL e micro-ros-agent'),
        DeclareLaunchArgument(
            'use_mavlink_bridge',
            default_value='true',
            description='Lancar a bridge MAVLink -> ROS 2 -> cmd_vel dos thrusters',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
