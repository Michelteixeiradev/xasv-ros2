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
        self.get_logger().info("Aguardando conexão MAVLink na porta 14555...")
        self.master = mavutil.mavlink_connection('udpin:0.0.0.0:14555')
        
        # Timer rodando a 20Hz (0.05s) para checar novas mensagens
        self.timer = self.create_timer(0.05, self.timer_callback)

    def timer_callback(self):
        # Escuta especificamente a mensagem de saída dos motores/servos do ArduPilot
        msg = self.master.recv_match(type='SERVO_OUTPUT_RAW', blocking=False)
        
        if not msg:
            return

        throttle_pwm = msg.servo3_raw
        steering_pwm = msg.servo1_raw

        # --- ADICIONE ESTA LINHA AQUI PARA VER A MÁGICA ---
        self.get_logger().info(f"Recebendo PWM -> Aceleração: {throttle_pwm} | Leme: {steering_pwm}")

        twist = Twist()
        twist.linear.x = (throttle_pwm - 1500.0) / 500.0
        twist.angular.z = -(steering_pwm - 1500.0) / 500.0 

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
    