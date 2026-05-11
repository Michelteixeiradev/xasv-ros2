#!/usr/bin/env python3
"""
Ponte entre o ArduPilot SITL (Rover) e os 6 thrusters do migbot no Gazebo.
Le SERVO_OUTPUT_RAW (PWMs servo1..6 = saidas do mixer Lua) via MAVLink TCP
e publica velocidade angular (rad/s) em
/model/migbot/joint/Engine_helice_X/cmd_vel, que e consumida pelo
gz-sim-thruster-system com use_angvel_cmd=true.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from pymavlink import mavutil

# Mapeia PWM -> velocidade angular alvo. PWM 1500 = 0 rad/s,
# PWM 2000 = +OMEGA_MAX, PWM 1000 = -OMEGA_MAX. Combinado com
# thrust_coefficient=0.05 e propeller_diameter=0.2, OMEGA_MAX=80 rad/s
# gera ~200 N de empuxo por motor.
OMEGA_MAX = 80.0


def pwm_to_omega(pwm: int) -> float:
    if pwm <= 0:
        return 0.0
    return ((pwm - 1500.0) / 500.0) * OMEGA_MAX


class MavlinkBridge(Node):
    def __init__(self):
        super().__init__('mavlink_bridge_node')

        # Um publicador por motor.
        self.pubs = [
            self.create_publisher(
                Float64,
                f'/model/migbot/joint/Engine_helice_{i}/cmd_vel',
                10,
            )
            for i in range(1, 7)
        ]

        # MAVProxy faz "--out udp:127.0.0.1:14555" para alimentar essa bridge.
        self.declare_parameter('connection', 'udpin:0.0.0.0:14555')
        conn = self.get_parameter('connection').value
        self.get_logger().info(f'Conectando MAVLink em {conn}...')
        self.master = mavutil.mavlink_connection(conn)
        self.master.wait_heartbeat(timeout=15)
        self.get_logger().info(
            f'Heartbeat OK: sys={self.master.target_system} comp={self.master.target_component}'
        )

        # Pede SERVO_OUTPUT_RAW a 50 Hz.
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_SERVO_OUTPUT_RAW,
            20000,  # microsegundos -> 50 Hz
            0, 0, 0, 0, 0,
        )

        self.timer = self.create_timer(0.02, self._tick)

    def _tick(self):
        msg = self.master.recv_match(type='SERVO_OUTPUT_RAW', blocking=False)
        if msg is None:
            return
        pwms = [msg.servo1_raw, msg.servo2_raw, msg.servo3_raw,
                msg.servo4_raw, msg.servo5_raw, msg.servo6_raw]
        for i, pwm in enumerate(pwms):
            out = Float64()
            out.data = pwm_to_omega(pwm)
            self.pubs[i].publish(out)


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
