The overall X-in-the-Loop architecture implemented by xasv-sim is shown in
Figure&nbsp;1.

<p align="center">
  <img src="figs/xitl_architecture.png" alt="xasv-sim X-in-the-Loop architecture" width="600"/>
</p>

## Current ROS 2 / Gazebo Harmonic State

The current validated Phase 7 stack runs Migbot in Gazebo Harmonic with
ArduPilot Rover SITL, QGroundControl, AP_DDS and a MAVLink actuator fallback.

Validated runtime flow:

```text
QGroundControl
  -> MAVLink
  -> ArduPilot Rover SITL
  -> Lua mixer V5
  -> SERVO_OUTPUT_RAW
  -> asv_mavlink/mavlink_bridge_node.py
  -> /model/migbot/joint/Engine_helice_N/cmd_vel
  -> gz-sim-thruster-system
  -> physical thrust in Gazebo
```

AP_DDS is also active:

```text
ArduPilot Rover SITL
  -> micro-ros-agent udp4:2019
  -> /ap/pose/filtered, /ap/twist/filtered, /ap/navsat, /ap/cmd_vel, /ap/*
```

Important actuator decision: AP_DDS is validated for telemetry, services and
high-level ROS 2 commands, but MAVLink remains the official actuator fallback.
The Gazebo `Thruster` system with `use_angvel_cmd=true` consumes
`/model/migbot/joint/Engine_helice_N/cmd_vel`; propeller joint rotation alone
does not prove physical thrust.

The Phase 7 sanity command is:

```bash
ros2 run asv_mavlink fase7_sanity_check
```

It validates `SERVO_OUTPUT_RAW -> cmd_vel -> force -> pose`.

## XITL Overview

At the core of the stack, ArduPilot runs either

- in **SITL**, as a software process on the host machine, or  
- in **HITL**, on a physical ArduPilot-compatible board (tested on a Pixhawk 4 using the `ardupilot_hitl` setup).

- **QGroundControl (QGC)** connects to ArduPilot via MAVLINK for mission upload, parameter tuning and real-time monitoring.

- In the current ROS 2 stack, **AP_DDS** exposes native `/ap/*` topics and services, while `asv_mavlink` bridges MAVLink `SERVO_OUTPUT_RAW` to Gazebo thruster `cmd_vel`.
- Legacy/MAVROS-based flows may still be useful as historical reference, but they are not the validated Phase 7 actuator path.

On the simulation side, **Gazebo** hosts the ASV and the river world:

- The `ArduPilotPlugin` from `ardupilot_gazebo` connects Gazebo Harmonic and ArduPilot SITL through JSON/FDM.
- Additional simulated sensors (IMU, GPS, MAG, BAR, CAM, SON, LID) are
  attached to the ASV model inside Gazebo.
- ROS communicates with Gazebo through `ros_gz_bridge`, enabling access to `cmd_vel`, thruster `force`, pose and simulated sensor topics.

Human interaction and teleoperation are also integrated:

- AP_DDS exposes `/ap/joy` and `/ap/cmd_vel` for ROS 2 command experiments, while QGC/MAVLink remains the validated human mission-control path.
- QGrondControl (QGC) provides a graphical interface for the operator to monitor the mission and issue high-level commands.

The coloured regions in Figure&nbsp;1 highlight the different X-in-the-Loop
modes supported by the stack:

- **MITL** – Model-in-the-Loop, where modules in ROS can act in the control loop.
- **SITL** – ArduPilot running in software, coupled to Gazebo.
- **HITL** – ArduPilot running on hardware, keeping the same MAVLINK
  interfaces.
- **RITL** – Render-in-the-Loop, where Gazebo’s rendering pipeline is used
  for dataset generation and appearance variation.
- **HuITL** – Human-in-the-Loop, where a human operator interacts via
  joystick and QGC.
- **XITL** – the combined architecture, where these loops can be enabled or
  disabled according to the experiment.

This architecture allows experiments ranging from pure MITL to mixed XITL
setups, with optional human and learning components in the loop, all running
inside a realistic ROS + Gazebo river environment.
