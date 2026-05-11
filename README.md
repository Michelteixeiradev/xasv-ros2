# xasv-ros2 — Simulação ASV em ROS 2 Jazzy + Gazebo Harmonic

Migração do projeto **xasv-sim** (ROS 1 / Gazebo Classic) para **ROS 2 Jazzy** com **Gazebo Harmonic**, mantendo a arquitetura **X-in-the-Loop (XITL)** para simulação e navegação autônoma de um veículo de superfície autônomo (ASV) chamado **Migbot**.

---

## Visão Geral

O Migbot é um catamarã de 142 kg com 6 hélices (3 bombordo, 3 estibordo) simulado em um cenário realista do **Rio Madeira**. A stack integra:

- **Gazebo Harmonic** — física (DART), flutuabilidade, hidrodinâmica SNAME e thrusters
- **ArduPilot Rover SITL** — piloto automático com mixer Lua customizado
- **AP_DDS** — comunicação nativa ArduPilot ↔ ROS 2 via Micro-XRCE-DDS
- **MAVLink Bridge** — ponte de atuadores (SERVO_OUTPUT_RAW → cmd_vel dos thrusters)
- **QGroundControl** — planejamento de missões e monitoramento

## Arquitetura de Runtime

```text
QGroundControl ──MAVLink──► ArduPilot Rover SITL ──JSON/FDM──► ArduPilotPlugin (Gazebo)
                                    │                                    │
                                    │ SERVO_OUTPUT_RAW                   │ Sensores (IMU/GPS/Mag)
                                    ▼                                    │
                           mavlink_bridge_node.py                        │
                                    │                                    │
                                    ▼                                    │
                           /Engine_helice_N/cmd_vel ──► gz-sim-thruster ──► Empuxo físico
                                    
ArduPilot ──AP_DDS──► micro-ros-agent ──► /ap/pose, /ap/twist, /ap/navsat, /ap/cmd_vel
```

## Pacotes ROS 2

| Pacote | Descrição |
|--------|-----------|
| `asv_bringup` | Launch principal (`sim.launch.py`), orquestra todos os componentes |
| `asv_description` | URDF/Xacro do Migbot, meshes 3D, plugins Gazebo |
| `asv_gazebo` | Mundos SDF (`madeira_river_simple.sdf`) |
| `asv_control` | Infraestrutura de controle e teleoperação |
| `asv_mavlink` | Bridge MAVLink → ROS 2, sanity check automatizado |

## Início Rápido

### Pré-requisitos
- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- ArduPilot SITL compilado com `--enable-DDS`
- `ardupilot_gazebo` instalado
- `micro-ros-agent` compilado em `~/micro_ros_ws`
- QGroundControl

### Compilar
```bash
cd ~/ros2_asv_ws
colcon build
source install/setup.bash
```

### Executar (launch único)
```bash
ros2 launch asv_bringup sim.launch.py ardupilot:=true
```

### Executar Missão
1. Abrir QGroundControl (`~/QGroundControl-x86_64.AppImage`)
2. Criar waypoints no mapa do rio
3. Fazer upload da missão
4. Armar o veículo
5. Mudar para modo AUTO e iniciar

### Validação
```bash
ros2 run asv_mavlink fase7_sanity_check
# Esperado: OK: SERVO_OUTPUT_RAW, cmd_vel, force e pose mudaram.
```

## Fases de Desenvolvimento

| Fase | Descrição | Status |
|------|-----------|--------|
| 1 | Base mínima ROS 2 | ✅ Concluída |
| 2 | Controle manual (teleop) | ✅ Concluída |
| 3 | Integração MAVLink + QGC | ✅ Concluída |
| 4 | Ambiente customizado (Rio Madeira) | ✅ Concluída |
| 5 | Robô customizado (Migbot) | ✅ Concluída |
| 6 | Sensores + Física realista | ✅ Concluída |
| 7 | ArduPilot SITL + AP_DDS | ✅ Concluída |
| 8 | Sensores adicionais + IA | 🔜 Próxima |

## Documentação

Toda a documentação técnica está em [`docs/`](docs/):

| Documento | Conteúdo |
|-----------|----------|
| [GUIA_FASES.md](docs/GUIA_FASES.md) | Roteiro completo das fases de migração |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura XITL e fluxo de dados |
| [FASE7_AP_DDS.md](docs/FASE7_AP_DDS.md) | Plano detalhado da integração ArduPilot |
| [FASE7_STATUS.md](docs/FASE7_STATUS.md) | Status atual, troubleshooting e reprodução |
| [MOTOR_MIXER_DOSSIER.md](docs/MOTOR_MIXER_DOSSIER.md) | Dossiê técnico do problema de propulsão |
| [SPAWN_TROUBLESHOOTING.md](docs/SPAWN_TROUBLESHOOTING.md) | Soluções para problemas de spawn/flutuação |
| [BUOYANCY_FIX.md](docs/BUOYANCY_FIX.md) | Correções de flutuabilidade |
| [PLUGINS.md](docs/PLUGINS.md) | Referência de plugins Gazebo utilizados |
| [3DMODELLING.md](docs/3DMODELLING.md) | Processo de modelagem 3D do Migbot |
| [ROS1_TO_ROS2_ASV_MIGRATION_GUIDE.md](docs/ROS1_TO_ROS2_ASV_MIGRATION_GUIDE.md) | Guia completo de migração ROS 1 → ROS 2 |
| [XITL.md](docs/XITL.md) | Detalhamento da arquitetura X-in-the-Loop |
| [branches_mapping.md](docs/branches_mapping.md) | Mapeamento de branches do Git |

## Licença

Projeto acadêmico — Universidade Federal de Rondônia (UNIR).