#!/usr/bin/env python3
"""Sanity check end-to-end da Fase 7.

Verifica a cadeia:
SERVO_OUTPUT_RAW -> /cmd_vel -> /force -> /model/migbot/pose
"""

import math
import sys
import time

import rclpy
from geometry_msgs.msg import PoseArray
from pymavlink import mavutil
from rclpy.node import Node
from std_msgs.msg import Float64


MOTOR_COUNT = 6


def _distance_xy(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _pose_xy(msg, spawn_x, spawn_y):
    candidates = [pose for pose in msg.poses if pose.position.x or pose.position.y]
    floating = [pose for pose in candidates if pose.position.z > 0.2]
    search_space = floating or candidates
    if not search_space:
        return None
    pose = min(
        search_space,
        key=lambda item: math.hypot(item.position.x - spawn_x, item.position.y - spawn_y),
    )
    return (pose.position.x, pose.position.y)


class Fase7SanityCheck(Node):
    def __init__(self):
        super().__init__('fase7_sanity_check')
        self.declare_parameter('connection', 'udpin:0.0.0.0:14550')
        self.declare_parameter('timeout_sec', 35.0)
        self.declare_parameter('throttle_pwm', 1900)
        self.declare_parameter('cmd_vel_min_abs', 5.0)
        self.declare_parameter('force_min_abs', 1.0)
        self.declare_parameter('pose_min_delta_m', 0.05)
        self.declare_parameter('spawn_x', 100.0)
        self.declare_parameter('spawn_y', 20.0)

        self.cmd_vel = [None] * MOTOR_COUNT
        self.force = [None] * MOTOR_COUNT
        self.pose_xy = None

        for i in range(MOTOR_COUNT):
            self.create_subscription(
                Float64,
                f'/model/migbot/joint/Engine_helice_{i + 1}/cmd_vel',
                self._cmd_vel_cb(i),
                10,
            )
            self.create_subscription(
                Float64,
                f'/model/migbot/joint/Engine_helice_{i + 1}/force',
                self._force_cb(i),
                10,
            )

        self.create_subscription(PoseArray, '/model/migbot/pose', self._pose_cb, 10)

    def _cmd_vel_cb(self, index):
        def callback(msg):
            self.cmd_vel[index] = msg.data

        return callback

    def _force_cb(self, index):
        def callback(msg):
            self.force[index] = msg.data

        return callback

    def _pose_cb(self, msg):
        pose = _pose_xy(
            msg,
            float(self.get_parameter('spawn_x').value),
            float(self.get_parameter('spawn_y').value),
        )
        if pose is not None:
            self.pose_xy = pose

    def _spin_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)

    def _connect_mavlink(self):
        conn = self.get_parameter('connection').value
        self.get_logger().info(f'Conectando MAVLink em {conn}...')
        master = mavutil.mavlink_connection(conn)
        master.wait_heartbeat(timeout=15)
        self.get_logger().info(
            f'Heartbeat OK: sys={master.target_system} comp={master.target_component}'
        )
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_SERVO_OUTPUT_RAW,
            20000,
            0,
            0,
            0,
            0,
            0,
        )
        return master

    def _set_manual_mode(self, master):
        modes = master.mode_mapping() or {}
        if 'MANUAL' not in modes:
            self.get_logger().warning('Modo MANUAL nao encontrado no mapping MAVLink; seguindo sem trocar modo.')
            return
        master.mav.set_mode_send(
            master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            modes['MANUAL'],
        )

    def _arm(self, master):
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
        )

    def _send_rc_override(self, master, throttle_pwm):
        channels = [
            1500,
            1500,
            int(throttle_pwm),
            1500,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
            65535,
        ]
        master.mav.rc_channels_override_send(master.target_system, master.target_component, *channels)

    def _release_rc_override(self, master):
        master.mav.rc_channels_override_send(
            master.target_system,
            master.target_component,
            *([0] * 18),
        )

    def _latest_servo_output(self, master):
        msg = master.recv_match(type='SERVO_OUTPUT_RAW', blocking=False)
        if msg is None:
            return None
        return [
            msg.servo1_raw,
            msg.servo2_raw,
            msg.servo3_raw,
            msg.servo4_raw,
            msg.servo5_raw,
            msg.servo6_raw,
        ]

    def run(self):
        timeout = float(self.get_parameter('timeout_sec').value)
        throttle_pwm = int(self.get_parameter('throttle_pwm').value)
        cmd_vel_min_abs = float(self.get_parameter('cmd_vel_min_abs').value)
        force_min_abs = float(self.get_parameter('force_min_abs').value)
        pose_min_delta_m = float(self.get_parameter('pose_min_delta_m').value)

        master = self._connect_mavlink()
        self._spin_for(2.0)
        initial_pose = self.pose_xy

        self._set_manual_mode(master)
        self._arm(master)
        self.get_logger().info(f'Aplicando RC throttle {throttle_pwm} e observando a cadeia da Fase 7...')

        start = time.monotonic()
        servo_seen = False
        cmd_seen = False
        force_seen = False
        pose_seen = False
        last_servos = None

        try:
            while time.monotonic() - start < timeout and rclpy.ok():
                self._send_rc_override(master, throttle_pwm)
                self._spin_for(0.2)

                servos = self._latest_servo_output(master)
                if servos is not None:
                    last_servos = servos
                    servo_seen = any(abs(pwm - 1500) >= 50 for pwm in servos if pwm > 0)

                cmd_seen = any(value is not None and abs(value) >= cmd_vel_min_abs for value in self.cmd_vel)
                force_seen = any(value is not None and abs(value) >= force_min_abs for value in self.force)
                if initial_pose is not None and self.pose_xy is not None:
                    pose_seen = _distance_xy(initial_pose, self.pose_xy) >= pose_min_delta_m

                if servo_seen and cmd_seen and force_seen and pose_seen:
                    self.get_logger().info('OK: SERVO_OUTPUT_RAW, cmd_vel, force e pose mudaram.')
                    return 0
        finally:
            self._release_rc_override(master)

        failures = []
        if not servo_seen:
            failures.append(f'SERVO_OUTPUT_RAW nao saiu do neutro. Ultimo valor: {last_servos}')
        if not cmd_seen:
            failures.append(f'/cmd_vel dos thrusters nao passou de {cmd_vel_min_abs} rad/s. Ultimo: {self.cmd_vel}')
        if not force_seen:
            failures.append(f'/force dos thrusters nao passou de {force_min_abs} N. Ultimo: {self.force}')
        if not pose_seen:
            failures.append(
                f'pose nao moveu {pose_min_delta_m} m. Inicial: {initial_pose}, atual: {self.pose_xy}'
            )
        self.get_logger().error('Falha no sanity check da Fase 7:\n- ' + '\n- '.join(failures))
        return 1


def main(args=None):
    rclpy.init(args=args)
    node = Fase7SanityCheck()
    try:
        return_code = node.run()
    except Exception as exc:  # noqa: BLE001 - executavel de diagnostico deve imprimir a causa raiz.
        node.get_logger().error(f'Erro executando sanity check da Fase 7: {exc}')
        return_code = 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(return_code)


if __name__ == '__main__':
    main()
