# Plano de Migração: ROS1 para ROS2 (Atualizado)

## Objetivo Geral

Criar uma base funcional em ROS2 (Jazzy) para o projeto xasv-sim, focando no fluxo principal de simulação sem depender de hardware físico no momento.

## FASE 1: Base Mínima e Estrutura Arquitetural (Concluída)

- [x] Estruturação do workspace e pacotes principais (asv_bringup, asv_description, etc).
- [x] Criação do modelo dummy_boat.urdf e cenário empty_ocean.sdf.
- [x] Validação do spawn do robô no Gazebo Harmonic.

## FASE 2: Controle Manual ROS 2 Nativo (Concluída)

- [x] Integração do plugin VelocityControl no URDF.
- [x] Configuração da ros_gz_bridge para o tópico /cmd_vel.
- [x] Validação de movimento via teleop_twist_keyboard.

## FASE 3: Integração MAVLink e Controle via QGC (Concluída)

**Status:** Validada com sucesso em 19/04/2026.

### Escopo Realizado

- [x] Ponte de Comunicação: Implementação do nó mavlink_bridge_node.py (pacote asv_mavlink) utilizando pymavlink.
- [x] Arquitetura de Portas: Configuração de escuta na porta UDP 14555 para evitar conflitos com o QGroundControl (14550).
- [x] Tradução de Protocolo: Lógica de normalização de sinais PWM (1000-2000) do ArduPilot para mensagens Twist (-1.0 a 1.0) do ROS 2.
- [x] SITL ArduPilot: Configuração do ambiente de simulação com sim_vehicle.py no modo Rover/Boat.
- [x] Integração GCS: Validação completa do fluxo: Joystick QGC -> ArduPilot -> Ponte Python -> Gazebo.

### Sequência Operacional Validada

- Gazebo: `ros2 launch asv_bringup sim.launch.py`
- Ponte: `ros2 launch asv_mavlink mavlink_bridge.launch.py`
- ArduPilot: `sim_vehicle.py -v Rover -f rover --console --map --out=udp:127.0.0.1:14555`
- QGC: `~/QGroundControl-x86_64.AppImage`

## FASE 4: Integração de Sensores e Feedback de Autonomia (Próximos Passos)

### Escopo Técnico

- Fechamento de Malha (Feedback): Adicionar plugins de GPS e IMU ao dummy_boat.urdf para que o ArduPilot receba a posição real do Gazebo.
- Ponte de Telemetria: Implementar no nó de ponte o envio de pacotes MAVLink de volta para o SITL (permitindo navegação autônoma por Waypoints).
- Percepção Avançada:
  - Adicionar LiDAR Livox e Câmera RealSense D435 ao URDF.
  - Configurar ros_gz_bridge para transportar PointClouds e Imagens para o ROS 2.
- Visualização: Configuração do RViz2 para monitoramento dos sensores em tempo real.

## FASE 5: Migração da Política de Autonomia (IA)

### Escopo Previsto

- Migrar o nó huitl_policy_node de ROS 1 para ROS 2 (Python).
- Implementar a carga e inferência do modelo PyTorch (.pt) dentro do ambiente ROS 2 Jazzy.
- Transição para comandos de atitude/posição via MAVLink (SET_POSITION_TARGET_LOCAL_NED).
- Teste de ciclo fechado: Percepção (LiDAR/Câmera) -> Política IA -> Comando MAVLink -> Movimento.

## Notas de Implementação da Fase 3

- O uso da porta 14555 via parâmetro --out no MAVProxy foi essencial para permitir que o QGC e o nó ROS recebam dados simultaneamente.
- Foi necessário o uso do modo -f rover no SITL para garantir a estabilidade do heartbeat sem a dependência de plugins C++ nativos do Gazebo nesta etapa.
