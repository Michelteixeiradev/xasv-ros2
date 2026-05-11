# Plano de Migração: ROS 1 para ROS 2

## Objetivo Geral
Criar uma base funcional em ROS 2 (Jazzy) para o projeto xasv-sim, focando no fluxo principal de simulação sem depender de hardware físico no momento.

---

## FASE 1: Base Mínima e Estrutura Arquitetural ✅

### Arquitetura de Pacotes Criada (`ros2_asv_ws/src/`)
- `asv_bringup`: Maestro da simulação.
- `asv_description`: Modelo URDF básico (`dummy_boat.urdf`).
- `asv_gazebo`: Cenário genérico em SDF (`empty_ocean.sdf`).
- `asv_control`: Infraestrutura Python e nó inicial (`teleop_node.py`).
- `asv_mavlink`: Estrutura para ponte de comunicação.
- `asv_missions`: Estrutura para rotas (`sample_mission.plan`).

### Critérios de Aceite
- [x] O workspace compila sem erros (Ubuntu 24.04).
- [x] O simulador Gazebo abre através do `sim.launch.py`.
- [x] O robô genérico aparece no mundo virtual.

---

## FASE 2: Controle Manual ✅

- [x] Plugin `VelocityControl` adicionado ao modelo URDF.
- [x] Ponte `ros_gz_bridge` configurada no launch principal.
- [x] Controle via teclado utilizando `teleop_twist_keyboard`.
- [x] Resposta de movimento do barco validada no Gazebo.

---

## FASE 3: Integração MAVLink e Autonomia Básica ✅

**Validada em 19/04/2026.**

- [x] Implementação do `mavlink_bridge_node.py` (pacote `asv_mavlink`) utilizando `pymavlink`.
- [x] Configuração de escuta na porta UDP 14555 para evitar conflitos com QGC (14550).
- [x] Normalização de sinais PWM (1000-2000) do ArduPilot para mensagens Twist (-1.0 a 1.0).
- [x] SITL ArduPilot com `sim_vehicle.py` no modo Rover/Boat.
- [x] Validação do fluxo: Joystick QGC → ArduPilot → Ponte Python → Gazebo.

---

## FASE 4: Ambiente Customizado ✅

- [x] Mundo `madeira_river_simple.sdf` portado do ambiente 3D original.
- [x] Iluminação, terreno, margens do rio e obstáculos configurados.
- [x] Plugin `SceneBroadcaster` e seleção dinâmica de mundos via `world:=`.

---

## FASE 5: Robô Customizado "migbot" ✅

**Validada em 25/04/2026.**

- [x] Meshes 3D reais (`.dae`, texturas e colisões) transferidas.
- [x] Pacote `asv_description` reestruturado para ament/ROS 2.
- [x] Plugins legados incompatíveis limpos do `migbot.urdf.xacro`.
- [x] `VelocityControl` provisório para teleoperação.
- [x] Flutuabilidade (`Buoyancy` Plugin) no `madeira_river_simple.sdf`.
- [x] Spawn em posição segura no rio, barco flutuando e respondendo a `/cmd_vel`.

---

## FASE 6: Integração Complexa (Sensores e Física) ✅

### 6A — Sensores
- [x] IMU, GPS e Magnetômetro no URDF com bridges ROS 2.

### 6B — Dinâmica Real
- [x] Remoção do `VelocityControl` (cinemático).
- [x] Flutuabilidade graduada (`graded_buoyancy`) para estabilizar calado (~11cm).
- [x] 6 plugins `Thruster` individuais, controlados por força em Newtons.
- [x] Plugin `Hydrodynamics` com coeficientes SNAME para arrasto realista.

---

## FASE 7: Integração ArduPilot SITL Avançada via AP_DDS ✅

**Validada em 06/05/2026.** Documentação: [FASE7_STATUS.md](../docs/FASE7_STATUS.md)

### 7A — Dependências e Compilação
- [x] Plugin `ardupilot_gazebo` instalado e funcional.
- [x] `ardurover` recompilado com `--enable-DDS` e patches locais de compatibilidade.

### 7B — ArduPilotPlugin no URDF
- [x] `ArduPilotPlugin` configurado com `type=VELOCITY`, `multiplier=100`.
- [x] Transformações de orientação ajustadas (`modelXYZToAirplaneXForwardZDown`).
- [x] Sensores Gazebo alimentando o SITL via JSON/FDM.

### 7C — Motor Mixer Lua (V5)
- [x] `FRAME_CLASS=15` (Scripting Matrix), funções 94-99 (Script1-Script6).
- [x] Mixer híbrido: `vehicle:get_control_output()` para AUTO/GUIDED, `rc:get_pwm()` para MANUAL.
- [x] Servos dummy (SERVO7=Throttle, SERVO8=Steering) para satisfazer PreArm do Rover.

### 7D — AP_DDS (micro-ros-agent)
- [x] Tópicos validados: `/ap/pose/filtered`, `/ap/twist/filtered`, `/ap/navsat`, `/ap/cmd_vel`.
- [x] Serviços validados: `/ap/arm_motors`, `/ap/mode_switch`, `/ap/prearm_check`.
- [x] Taxas: ~25 Hz pose, ~23 Hz twist, ~4.5 Hz navsat.

### 7E — Validação End-to-End com QGroundControl
- [x] Missão WP1→WP2 executada em AUTO via QGC.
- [x] Bridge MAVLink → ROS 2 como backend oficial dos atuadores.
- [x] Sanity check automatizado: `ros2 run asv_mavlink fase7_sanity_check`.
- [x] Fix de race condition no auto-start (`respawn=True`, timing reordenado).

### Causa raiz resolvida
O `gz-sim-thruster-system` com `use_angvel_cmd=true` NÃO lê a velocidade real da junta. Ele escuta o tópico `cmd_vel`. A solução validada usa `mavlink_bridge_node.py` para publicar `SERVO_OUTPUT_RAW` → `cmd_vel` → `Thruster` → empuxo físico.

---

## FASE 8: Sensores Adicionais e IA 🔜

### Escopo Previsto
- [ ] LiDAR (Livox), Sonar (Ping360) e Câmera D435 no URDF com bridges ROS 2.
- [ ] Obstacle avoidance: `OA_TYPE`/`PRX_TYPE` no ArduPilot com sensor virtual, ou Nav2 ROS 2 sobre `/ap/cmd_vel`.
- [ ] Portar pipeline HuITL (coleta, treino, inferência) de `rospy` para `rclpy`.
- [ ] Inferência de Política de IA (PyTorch) publicando via AP_DDS (`/ap/cmd_vel`).
- [ ] Tuning de navegação: `CRUISE_SPEED`, `WP_RADIUS`, `TURN_RADIUS`, `ATC_*`.
- [ ] Correção de tendência em arco (simetria lateral dos motores vs. CoM).
- [ ] Alinhamento de georreferência Gazebo vs. SITL.