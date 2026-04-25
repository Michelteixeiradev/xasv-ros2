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

## FASE 4: Ambiente Customizado (Concluída)

**Status:** Validada com sucesso.

### Escopo Realizado

- [x] Criação do mundo base `madeira_river_simple.sdf` portado do ambiente 3D original.
- [x] Configuração de iluminação direcional, terreno estático sem atrito aquático, margens do rio e obstáculos (troncos/boias).
- [x] Adição do plugin `SceneBroadcaster` e adaptação do `sim.launch.py` para carregamento de múltiplos ambientes via argumento `world:=`.

## FASE 5: Robô Customizado "migbot" (Concluída)

**Status:** Validada com sucesso em 25/04/2026.

### Escopo Realizado

- [x] Transferência e descompactação das malhas 3D reais (arquivos `.dae`, texturas e colisões).
- [x] Reestruturação do pacote `asv_description` para padrões ament/ROS 2.
- [x] Limpeza profunda de plugins legados incompatíveis no `migbot2.urdf.xacro`.
- [x] Injeção de `VelocityControl` para permitir teleoperação provisória baseada no `base_link`.
- [x] Inserção de Flutuabilidade (`Buoyancy` Plugin) no `madeira_river_simple.sdf` para interação física do casco na água.
- [x] Lançamento coordenado e spawn em posição segura do rio (`Y=25.0`), flutuando sem fricção com o fundo.

## FASE 6: Integração Complexa (Próximos Passos)

### Escopo Técnico

- Adição dos modelos de motores e hidrodinâmica avançada do Gazebo Harmonic para substituir o `VelocityControl`.
- Configuração dos sensores do robô (LiDAR Livox, Ping360, GPS e IMU) com os plugins de sensores do Harmonic e bridges.
- Interligar o fluxo ArduPilot -> ROS -> Motores do Gazebo (SITL real controlando as hélices).
- Preparar integração final da Política Neural HUITL do MAVLink para as trajetórias autônomas.

## Notas de Implementação da Fase 3

- O uso da porta 14555 via parâmetro --out no MAVProxy foi essencial para permitir que o QGC e o nó ROS recebam dados simultaneamente.
- Foi necessário o uso do modo -f rover no SITL para garantir a estabilidade do heartbeat sem a dependência de plugins C++ nativos do Gazebo nesta etapa.
