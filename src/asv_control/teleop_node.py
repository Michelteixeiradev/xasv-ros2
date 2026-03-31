import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class TeleopNode(Node):
    def __init__(self):
        # 1. Dá um nome de batismo para este nó no ecossistema ROS2
        super().__init__('teleop_node')
        
        # 2. Cria o "alto-falante" (Publisher)
        # Ele vai gritar mensagens do tipo Twist (velocidade) no canal (tópico) chamado 'cmd_vel'
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # 3. Cria um cronômetro (Timer)
        # A cada 0.5 segundos, ele vai chamar a função 'timer_callback' logo abaixo
        timer_period = 0.5

        # Cria o timer que vai chamar a função timer_callback a cada 0.5 segundos
        # A estrutura desse comando é: self.create_timer(tempo_em_segundos, nome_da_funcao_a_ser_chamada)
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # Imprime uma mensagem no terminal para confirmar que o nó foi iniciado
        self.get_logger().info('Publicando velocidade...')

    def timer_callback(self):
        # 4. Cria a mensagem de movimento
        # O que passa dentro desses "()" é o tipo de mensagem que vai ser publicada
        # No caso, é a mensagem do tipo Twist que vem do pacote geometry_msgs
        msg = Twist()
        
        # 5. Define a velocidade: 1.0 metro por segundo para frente (eixo X)
        msg.linear.x = 1.0

        # 0.0 de rotação (não vai virar para os lados)
        msg.angular.z = 0.0
        
        # 6. Publica a mensagem no canal para o robô ouvir e andar
        self.publisher_.publish(msg)

def main(args=None):
    
    # Inicia o ROS2
    rclpy.init(args=args)
    
    # Cria o nosso cérebro
    teleop_node = TeleopNode()
    
    try:
        # Fica rodando em loop infinito até você mandar parar (Ctrl+C)
        rclpy.spin(teleop_node)
    except KeyboardInterrupt:
        pass
    finally:
        # Desliga tudo com segurança
        teleop_node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()