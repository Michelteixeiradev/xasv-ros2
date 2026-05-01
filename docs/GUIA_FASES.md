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

## Fase 7 - Integração ArduPilot SITL Avançada via AP_DDS
Objetivo: substituir a ponte pymavlink provisória por integração nativa ArduPilot ↔ Gazebo ↔ ROS 2.
- **7A:** Instalar `ardupilot_gazebo` plugin e compilar ArduPilot Rover SITL com `--enable-dds`.
- **7B:** Configurar `ArduPilotPlugin` no `migbot.urdf.xacro` (6 canais PWM → Newtons nos thrusters).
- **7C:** Implementar script Lua de Motor Mixer (`FRAME_CLASS=15`) para os 6 motores assimétricos.
- **7D:** Inicializar `micro-ros-agent` para expor tópicos `/ap/*` nativos no ROS 2 (latência ~2ms).
- **7E:** Validar missões autônomas (waypoints) via QGroundControl no mundo `madeira_river_simple`.
- Documentação detalhada: `docs/FASE7_AP_DDS.md`.

## Fase 8 - Sensores Adicionais e IA
Objetivo: completar o stack de sensores e integrar política neural de desvio de obstáculos.
- Adicionar LiDAR (Livox), Sonar (Ping360) e Câmera D435 ao URDF com bridges ROS 2.
- Portar pipeline HuITL (coleta, treino, inferência) de `rospy` para `rclpy`.
- Executar inferência de Política de IA (PyTorch) publicando diretamente em `/ap/cmd_vel` via AP_DDS.
