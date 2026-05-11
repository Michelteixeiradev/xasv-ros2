# Relatório de Progresso: Migração ROS 1 → ROS 2 do Projeto xasv-sim

> **Última atualização:** 2026-05-11  
> **Plano de referência:** [PLAN.md](./PLAN.md)  
> **Documentação completa:** [`docs/`](../docs/)

---

## Objetivo Geral

Criar uma base funcional em ROS 2 (Jazzy) para o projeto xasv-sim, migrando a simulação do ASV Migbot do ROS 1 / Gazebo Classic para ROS 2 / Gazebo Harmonic, com integração completa ao ArduPilot via AP_DDS.

---

## FASE 1: Base Mínima e Estrutura Arquitetural ✅

**Status:** Concluída.

- Workspace ROS 2 criado com 5 pacotes (`asv_bringup`, `asv_description`, `asv_gazebo`, `asv_control`, `asv_mavlink`).
- Modelo genérico `dummy_boat.urdf` e cenário `empty_ocean.sdf` validados.
- `sim.launch.py` funcionando com Gazebo Harmonic, `robot_state_publisher` e spawn automático.

---

## FASE 2: Controle Manual ROS 2 Nativo ✅

**Status:** Concluída.

- Plugin `VelocityControl` integrado ao URDF para escuta de `/cmd_vel`.
- `ros_gz_bridge` configurada no launch principal.
- Movimento validado via `teleop_twist_keyboard`.

---

## FASE 3: Integração MAVLink e Controle via QGC ✅

**Status:** Validada em 19/04/2026.

- Ponte `mavlink_bridge_node.py` (pacote `asv_mavlink`) implementada com `pymavlink`.
- Porta UDP 14555 dedicada para evitar conflito com QGroundControl (14550).
- Normalização PWM (1000-2000) → Twist (-1.0 a 1.0) implementada.
- Fluxo completo validado: Joystick QGC → ArduPilot SITL → Ponte Python → Gazebo.

**Sequência operacional:**
```
Gazebo: ros2 launch asv_bringup sim.launch.py
Ponte:  ros2 launch asv_mavlink mavlink_bridge.launch.py
SITL:   sim_vehicle.py -v Rover -f rover --console --map --out=udp:127.0.0.1:14555
QGC:    ~/QGroundControl-x86_64.AppImage
```

---

## FASE 4: Ambiente Customizado ✅

**Status:** Concluída.

- Mundo `madeira_river_simple.sdf` criado a partir do ambiente 3D original do ROS 1.
- Iluminação direcional, terreno estático, margens do rio e obstáculos (troncos/boias) configurados.
- Seleção dinâmica de mundos via argumento `world:=` no launch.

---

## FASE 5: Robô Customizado "Migbot" ✅

**Status:** Validada em 25/04/2026.

- Meshes 3D reais (`.dae`, texturas) transferidas e descompactadas.
- Pacote `asv_description` reestruturado para padrões ament/ROS 2.
- Plugins legados do Gazebo Classic removidos do `migbot.urdf.xacro`.
- `VelocityControl` provisório para teleoperação via `base_link`.
- Flutuabilidade (`Buoyancy` Plugin) integrada ao mundo.
- Barco autêntico flutuando no Rio Madeira e respondendo a `/cmd_vel`.

---

## FASE 6: Integração Complexa (Sensores e Física) ✅

**Status:** Concluída.

### 6A — Sensores
- IMU, GPS (NavSat) e Magnetômetro adicionados ao URDF.
- Bridges ROS 2 configuradas: `/imu`, `/navsat`, `/magnetometer`.

### 6B — Dinâmica Real
- `VelocityControl` removido (substituído por propulsão física).
- Flutuabilidade graduada (`graded_buoyancy`) implementada — calado estabilizado em ~11cm.
- 6 plugins `Thruster` individuais com controle por força (Newtons) ou velocidade angular.
- Plugin `Hydrodynamics` com coeficientes SNAME para arrasto realista na água (xU=-51.3, xUabsU=-72.4).

---

## FASE 7: Integração ArduPilot SITL + AP_DDS ✅

**Status:** Validada em 06/05/2026.  
**Documentação detalhada:** [FASE7_STATUS.md](../docs/FASE7_STATUS.md) | [FASE7_AP_DDS.md](../docs/FASE7_AP_DDS.md)

### Marcos Alcançados

1. **ArduPilotPlugin** instalado e configurado no URDF para integração JSON/FDM entre Gazebo e SITL.
2. **Motor Mixer Lua V5** implementado com `FRAME_CLASS=15` (Scripting Matrix), entrada híbrida AP/RC, funções de servo 94-99.
3. **AP_DDS validado** — `micro-ros-agent` expõe tópicos (`/ap/pose/filtered` a ~25 Hz, `/ap/twist/filtered` a ~23 Hz, `/ap/navsat` a ~4.5 Hz) e serviços (`/ap/arm_motors`, `/ap/mode_switch`, etc.).
4. **Bridge MAVLink → ROS 2** como backend oficial dos atuadores: `SERVO_OUTPUT_RAW` → `mavlink_bridge_node.py` → `cmd_vel` → `gz-sim-thruster-system`.
5. **Missão WP1→WP2** executada com sucesso em modo AUTO via QGroundControl.
6. **Sanity check automatizado:** `ros2 run asv_mavlink fase7_sanity_check` valida toda a cadeia.

### Causa Raiz do Problema de Propulsão (Resolvida)
O `gz-sim-thruster-system` com `use_angvel_cmd=true` **não lê a velocidade real da junta** — ele escuta o tópico `cmd_vel`. A ponte MAVLink foi reconectada para publicar nesses tópicos, restaurando o empuxo físico.

### Decisão Arquitetural
- **AP_DDS** → telemetria, serviços e comandos ROS 2 de alto nível.
- **MAVLink Bridge** → backend oficial dos atuadores (thrusters).

### Comando de Execução Validado
```bash
cd ~/ros2_asv_ws && source install/setup.bash
ros2 launch asv_bringup sim.launch.py ardupilot:=true
```

---

## FASE 8: Sensores Adicionais e IA 🔜

**Status:** Próxima fase.

### Escopo Planejado
- Adicionar LiDAR (Livox), Sonar (Ping360) e Câmera D435 ao URDF.
- Obstacle avoidance via `OA_TYPE`/`PRX_TYPE` no ArduPilot ou Nav2 ROS 2.
- Portar pipeline HuITL (coleta, treino, inferência) de `rospy` para `rclpy`.
- Inferência de Política de IA (PyTorch) via AP_DDS (`/ap/cmd_vel`).

### Problemas Conhecidos para Resolver
- Migbot colide em obstáculos do `madeira_river_simple` (sem obstacle avoidance).
- Tendência de navegação em arco (simetria lateral dos motores vs. CoM).
- Desalinhamento de georreferência entre `/ap/navsat` (SITL) e `/navsat` (Gazebo).

---

## Notas Técnicas

- A porta UDP 14555 via `--out` no MAVProxy é essencial para permitir QGC e nó ROS receberem dados simultaneamente.
- O uso da flag `-w` (wipe EEPROM) no `sim_vehicle.py` garante calibração limpa do AHRS a cada inicialização.
- O `micro-ros-agent` deve subir ANTES do SITL para evitar `DDS: No ping response` (timing: agent t=10s, SITL t=18s).
- O mixer Lua deve estar sincronizado em `~/ardupilot/scripts/` E `~/ardupilot/Rover/scripts/`.
