import os
from launch import LaunchDescription # Importa a classe LaunchDescription, que faz parte do ecossistema ROS 2
from launch.actions import ExecuteProcess # Importa a ação ExecuteProcess, que permite executar processos externos  
from launch_ros.actions import Node # Importa a ação Node, que permite executar nós ROS 2

def generate_launch_description(): # Função que gera a descrição do lançamento
    gazebo = ExecuteProcess( # Executa o simulador Gazebo
        cmd=['gz', 'sim', '-r', 'empty.sdf'], # Comando para executar o simulador Gazebo
        output='screen' # Saída do simulador Gazebo
    )
    return LaunchDescription([
        gazebo
    ])