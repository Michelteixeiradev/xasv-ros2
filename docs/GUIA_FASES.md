# Guia de Fases de Implementação: ROS1 para ROS2

Este documento contém as fases de implementação definidas para a reestruturação da simulação do projeto ASV para ROS2, servindo como referência de roteiro.

## Fase 0 - Leitura e entendimento
Objetivo: entender o processo antes de implementar.
- Ler documentação existente (README, ARCHITECTURE, XITL).
- Inspecionar launch files e URDFs antigos.
- Identificar o que é genérico e o que é específico do projeto.

## Fase 1 - Base mínima em ROS2
Objetivo: ter um projeto ROS2 funcional, ainda genérico.
- Criar workspace ROS2 e pacotes (asv_bringup, asv_description, asv_gazebo, asv_control).
- Criar URDF genérico e mundo genérico.
- Escrever `sim.launch.py` (Gazebo, robot_state_publisher, spawn).
- Validar TF e spawn.

## Fase 2 - Controle por operador
Objetivo: reproduzir o conceito de teleoperação do ROS1 no padrão ROS2.
- Adicionar pacote joy e teleop_twist_joy (ou custom).
- Publicar comando de velocidade/wrench.
- Validar resposta no Gazebo.

## Fase 3 - Integração com autopiloto externo
Objetivo: validar a camada de comunicação externa.
- Subir simulador em ROS2 e ArduPilot SITL externo.
- Integrar MAVROS ou ponte equivalente.
- Conectar QGroundControl e testar missão simples.

## Fase 4 - Ambiente customizado
Objetivo: trocar o mundo genérico por um mundo mais próximo do projeto.
- Criar ou importar SDF de ambiente (`madeira_river_simple`).
- Validar carregamento no Gazebo Harmonic.
- Inserir no `launch.py`.
- Validar spawn conjunto (robô + mundo) e ajustar poses.

## Fase 5 - Robô customizado
Objetivo: trocar o robô genérico pelo robô do projeto (`migbot`).
- Portar URDF/Xacro para ROS2.
- Identificar meshes e inércias.
- Testar robô sem plugins customizados.
- Adicionar sensores e controles graduais.

## Fase 6 - Plugins e compatibilização
Objetivo: reintroduzir partes específicas com risco controlado.
- Portar `gazebo_usv_dynamics_plugin`, `buoyancy_gazebo_plugin`, etc.
- Adicionar sensores específicos (LiDAR, Ping360).
- Validar isoladamente e depois integrar.

## Fase 7 - Integração ArduPilot SITL Avançada
Objetivo: controlar o Migbot no Gazebo Harmonic com ArduPilot Rover SITL e QGroundControl, preparando a migração para AP_DDS.
- **Status atual:** Fase 7 fechada com MANUAL/AUTO via QGroundControl, AP_DDS validado e MAVLink mantido como fallback oficial dos atuadores. Em 2026-05-06 foi aplicado fix de race no auto-start do `micro_ros_agent` (`respawn=True`, agent t=10s antes de SITL t=18s) e missão WP1→WP2 foi confirmada em AUTO sem warning `DDS: No ping response`.
- **7A:** Instalar `ardupilot_gazebo` plugin e preparar ArduPilot Rover SITL. `ardupilot_gazebo` está funcional; `ardurover` foi recompilado com `--enable-DDS` usando patches locais de compatibilidade do AP_DDS.
- **7B:** Configurar `ArduPilotPlugin` no `migbot.urdf.xacro` para integração JSON/FDM entre Gazebo e SITL.
- **7C:** Implementar script Lua de Motor Mixer V5 (`FRAME_CLASS=15`) para os 6 motores assimétricos, com entrada híbrida AP/RC.
- **7D:** Inicializar e validar `micro-ros-agent` para expor tópicos `/ap/*` nativos no ROS 2. Concluído: `/ap/pose/filtered`, `/ap/twist/filtered`, `/ap/navsat`, `/ap/cmd_vel` e serviços `/ap/*` observados.
- **7E:** Validar missões autônomas (waypoints) via QGroundControl. Concluído com a bridge MAVLink publicando `/model/migbot/joint/Engine_helice_N/cmd_vel`.
- **Validação automatizada:** `ros2 run asv_mavlink fase7_sanity_check` confirma `SERVO_OUTPUT_RAW -> cmd_vel -> force -> pose`.
- **Nota crítica:** o `gz-sim-thruster-system` com `use_angvel_cmd=true` escuta `cmd_vel`; hélice girando pela junta não garante empuxo. A bridge `asv_mavlink` continua sendo o backend oficial dos atuadores, mesmo com AP_DDS validado.
- Documentação detalhada: `docs/FASE7_AP_DDS.md` e `docs/FASE7_STATUS.md`.

## Fase 8 - Sensores Adicionais e IA
Objetivo: completar o stack de sensores e integrar política neural de desvio de obstáculos.
- Adicionar LiDAR (Livox), Sonar (Ping360) e Câmera D435 ao URDF com bridges ROS 2.
- **Obstacle avoidance:** problema observado no fim da Fase 7 — Migbot navega WP1→WP2 mas colide em obstáculos do `madeira_river_simple`. Avaliar `OA_TYPE` (BendyRuler/Dijkstra) + `PRX_TYPE` no ArduPilot com sensor virtual no Gazebo, ou Nav2 ROS 2 sobre `/ap/cmd_vel`.
- Portar pipeline HuITL (coleta, treino, inferência) de `rospy` para `rclpy`.
- Executar inferência de Política de IA (PyTorch) publicando comandos de alto nível via AP_DDS (`/ap/cmd_vel` ou serviços `/ap/*`), mantendo caminho MAVLink/ROS 2 como fallback operacional dos thrusters.
