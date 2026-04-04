from launch import LaunchDescription
from launch.actions import LogInfo

def generate_launch_description():
    return LaunchDescription([
        LogInfo(msg="Iniciando a ponte MAVLink (Placeholder para Fase 3)"),
        # Futuramente, o no do MAVROS ou ponte MAVLink entrara aqui
    ])