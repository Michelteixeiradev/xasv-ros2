#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from pymavlink import mavutil

class MavlinkBridge(Node):
    def __init__(self):
        super().__init__('mavlink_bridge_node')
        
        # Cria o publicador no tópico que o Gazebo escuta
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # Conecta ao ArduPilot SITL via porta UDP padrão do MAVProxy/SITL
        self.get_logger().info("Aguardando conexão MAVLink na porta 14550...")
        self.master = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
        
        # Timer rodando a 20Hz (0.05s) para checar novas mensagens
        self.timer = self.create_timer(0.05, self.timer_callback)

    def timer_callback(self):
        # Escuta especificamente a mensagem de saída dos motores/servos do ArduPilot
        msg = self.master.recv_match(type='SERVO_OUTPUT_RAW', blocking=False)
        
        if not msg:
            return

        # No ArduPilot Rover padrão:
        # Canal 3 = Aceleração (Throttle)
        # Canal 1 = Direção (Steering)
        # O sinal PWM varia de 1000 (Ré/Esquerda) a 2000 (Frente/Direita), com 1500 no neutro.
        throttle_pwm = msg.servo3_raw
        steering_pwm = msg.servo1_raw

        twist = Twist()
        
        # Normalização matemática básica: (Valor - Neutro) / Amplitude
        # Transforma o range [1000, 2000] em [-1.0, 1.0]
        twist.linear.x = (throttle_pwm - 1500.0) / 500.0
        
        # Para a rotação (angular.z), virar para a direita (PWM > 1500) 
        # significa um giro negativo no eixo Z do plano cartesiano do ROS.
        twist.angular.z = -(steering_pwm - 1500.0) / 500.0 

        # Publica o comando para o barco no Gazebo
        self.publisher_.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = MavlinkBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
    