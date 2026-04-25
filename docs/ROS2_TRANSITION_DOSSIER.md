# XASV-SIM - Dossie Tecnico para Migracao ROS1 -> ROS2

## 1) Objetivo deste documento

Este documento resume o projeto inteiro xasv-sim com foco pratico em migracao para ROS2.
O objetivo e servir como contexto confiavel para outra IA implementar a migracao sem desviar da arquitetura real.

Escopo deste dossie:
- Inventario de pacotes, nos, launch files, plugins, scripts e testes.
- Interfaces observaveis (topicos, mensagens, parametros, fluxos).
- Dependencias externas e acoplamentos mais sensiveis.
- Riscos tecnicos priorizados e plano de migracao em fases com checkpoints.

Limites:
- Nao foi feita execucao de build/test neste levantamento.
- Nao foram analisados artefatos binarios grandes (bags/modelos) internamente.

---

## 2) Snapshot do repositorio

Top-level principal:
- `README.md`
- `install_deps.sh`
- `docs/`
- `ardupilot_hitl/`
- `ardupilot_sitl/`
- `migbot_allocation/`
- `robots/migbot_description/`
- `robots/migbot_gazebo/`
- `teleop_wrench_keyboard/`
- `xasv_sim/`

Pacotes ROS detectados via `package.xml`:
1. `xasv_sim`
2. `ardupilot_hitl`
3. `migbot_allocation`
4. `robots/migbot_description` (pacote `migbot_description`)
5. `robots/migbot_gazebo` (pacote `migbot_gazebo`)
6. `teleop_wrench_keyboard`

---

## 3) Arquitetura funcional (alto nivel)

Conforme `README.md` e `docs/ARCHITECTURE.md`, o stack combina:
- Gazebo Classic 11 como simulador de mundo/robot.
- ArduPilot Rover em SITL (processo local) ou HITL (placa real Pixhawk).
- MAVROS como ponte MAVLink <-> ROS.
- Plugins Gazebo customizados para dinamica naval, vento, boiancia, ondas, interface com ArduPilot e obstaculos dinamicos.
- Fluxos XITL: MITL, SITL, HITL, RITL e HuITL.

Fluxo resumido:
1. Gazebo roda mundo + modelo ASV.
2. Plugins fornecem dinamica/sensores e interface com ArduPilot.
3. MAVROS expoe estado/comandos no ROS.
4. Nos ROS (teleop, alocacao, IA) atuam por topicos MAVROS e/ou controladores do robo.
5. Scripts de teste orquestram cenarios MITL/SITL/HITL.

---

## 4) Pacotes e responsabilidades

## 4.1) `xasv_sim` (core)

Fontes principais:
- `xasv_sim/CMakeLists.txt`
- `xasv_sim/package.xml`
- `xasv_sim/launch/`
- `xasv_sim/plugins/`
- `xasv_sim/scripts/`
- `xasv_sim/worlds/`, `xasv_sim/models/`, `xasv_sim/data/`, `xasv_sim/tests/`

Papel:
- Pacote principal do simulador.
- Compila bibliotecas/plugins Gazebo (inclui geracao protobuf).
- Reune launches para simulacao, pre-treino HuITL e politica IA.
- Contem scripts de dados/treino/inferencia e testes fim-a-fim.

Dependencias declaradas no `package.xml`:
- `gazebo_plugins`, `xacro`, `roscpp`.

Observacao:
- O `CMakeLists.txt` e bem mais complexo que o `package.xml` e depende tambem de Gazebo, Protobuf, Eigen3 e Boost.

## 4.2) `ardupilot_hitl`

Fontes:
- `ardupilot_hitl/CMakeLists.txt`
- `ardupilot_hitl/src/rx_data.cpp`
- `ardupilot_hitl/src/tx_data.cpp`
- `ardupilot_hitl/launch/apm.launch`
- `ardupilot_hitl/launch/link.launch`

Papel:
- Bridge HITL entre FCU real (via MAVROS) e simulacao Gazebo.
- `rx_data_node`: recebe `mavros_msgs/RCOut` e envia comandos por UDP para Gazebo.
- `tx_data_node`: agrega sensores ROS (`/imu`, `/magnetic`, `/fix`, `/fix_velocity`) e publica `mavros_msgs/GazeboMavlink` em `/mavros/gazebo/sensors`.

Dependencias declaradas:
- `roscpp`, `mavros_msgs`.

## 4.3) `migbot_allocation`

Fonte:
- `migbot_allocation/src/migbot_allocation.cpp`

Papel:
- Conversao de comando `geometry_msgs/Wrench` para 6 comandos de propulsor.
- Subscricao em topico relativo `Wrench`.
- Publica em:
  - `Engine_helice_1_effort_controller/command`
  - `Engine_helice_2_effort_controller/command`
  - `Engine_helice_3_effort_controller/command`
  - `Engine_helice_4_effort_controller/command`
  - `Engine_helice_5_effort_controller/command`
  - `Engine_helice_6_effort_controller/command`

## 4.4) `migbot_description`

Fontes:
- `robots/migbot_description/package.xml`
- `robots/migbot_description/urdf/`

Papel:
- URDF/Xacro e malhas do robo.
- Dependencias de runtime para publicacao de estado e plugins Gazebo padrao.

## 4.5) `migbot_gazebo`

Fontes:
- `robots/migbot_gazebo/package.xml`
- `robots/migbot_gazebo/launch/`
- `robots/migbot_gazebo/urdf/`, `models/`, `worlds/`

Papel:
- Configuracoes de simulacao Gazebo e launches de teste.

## 4.6) `teleop_wrench_keyboard`

Fonte:
- `teleop_wrench_keyboard/teleop_wrench_keyboard.py`

Papel:
- Teleoperacao por teclado publicando `geometry_msgs/Wrench` (ou `WrenchStamped`).
- Topico de publicacao relativo: `Wrench`.

---

## 5) Nos executaveis e interfaces

## 5.1) C++

1. `migbot_allocation_node` (`migbot_allocation/src/migbot_allocation.cpp`)
- Sub: `Wrench` (`geometry_msgs/Wrench`)
- Pubs: 6 topicos `.../effort_controller/command` (`std_msgs/Float64`)
- Loop: 100 Hz
- Parametros privados: `~L`, `~Pwmmin`, `~Pwmmax`

2. `rx_data_node` (`ardupilot_hitl/src/rx_data.cpp`)
- Sub esperado: `mavros_msgs/RCOut`
- Socket UDP HITL (padrao localhost: 9003 in / 9002 out)
- Traduz PWM de servo para velocidade de motor normalizada
- Controle de timing/sync interno para acompanhar taxa da simulacao

3. `tx_data_node` (`ardupilot_hitl/src/tx_data.cpp`)
- Subs:
  - `/imu` (`sensor_msgs/Imu`)
  - `/magnetic` (`geometry_msgs/Vector3Stamped`)
  - `/fix` (`sensor_msgs/NavSatFix`)
  - `/fix_velocity` (`geometry_msgs/Vector3Stamped`)
- Pub:
  - `/mavros/gazebo/sensors` (`mavros_msgs/GazeboMavlink`)
- Rate: 10 Hz

## 5.2) Python

4. `teleop_wrench_keyboard.py`
- Pub: `Wrench` (`geometry_msgs/Wrench` por padrao)
- Parametros: `~force`, `~torque`, `~repeat_rate`, `~key_timeout`, `~stamped`, `~frame_id`

5. `huitl_pretrain_pointcloud_node.py`
- Objetivo: coletar dataset supervisionado humano.
- Subs:
  - `/livox/pcl` (`sensor_msgs/PointCloud`)
  - `/mavros/local_position/pose`
  - `/mavros/local_position/velocity_local`
  - `/mavros/state`
  - `/mavros/global_position/global`
  - `/mavros/setpoint_raw/target_global`
  - `/mavros/rc/in`
  - `/xasv/pretrain_stop`
- Pub: `~phase` (`std_msgs/String`)
- Saida CSV com colunas:
  - `t`, `phase`
  - `min_front`, `min_left`, `min_right`
  - `speed`, `yaw`
  - `dist_to_wp`, `bearing_to_wp`
  - `rc_throttle_norm`, `rc_yaw_norm`

6. `xasv_huitl_policy_node.py`
- Objetivo: inferencia de politica MLP e envio de RC override.
- Carrega modelo `.pt` (default configuravel; launch aponta para `xasv_sim/data/xasv_huitl_policy/trained_rc_policy.pt`).
- Subs:
  - `/livox/pcl`
  - `/mavros/local_position/pose`
  - `/mavros/local_position/velocity_local`
  - `/mavros/state`
  - `/mavros/global_position/global`
  - `/mavros/setpoint_raw/target_global`
  - `/xasv/collision_flag`
- Pub:
  - `/mavros/rc/override` (`mavros_msgs/OverrideRCIn`)
- Regra de atuacao:
  - atua em `AUTO/GUIDED`, com gating de obstaculo frontal por LiDAR.
  - caso contrario, limpa override.

7. `train_supervised.py`
- Treina MLP supervisionada usando CSVs do pre-treino.
- Features (7D):
  - `min_front`, `min_left`, `min_right`, `speed`, `yaw`, `dist_to_wp`, `bearing_to_wp`
- Targets (2D):
  - `rc_throttle_norm`, `rc_yaw_norm`
- Salva checkpoint em `xasv_sim/data/xasv_huitl_policy/trained_rc_policy.pt` (default).

8. `rosgps2mission.py`
- Converte trajetoria GPS de rosbag para missao ArduPilot.
- Formatos: `waypoint` (QGC WPL 110) ou `plan` (JSON QGC).

---

## 6) Launch files e encadeamento

Launches detectados:
- `xasv_sim/launch/xasv_sim.launch`
- `xasv_sim/launch/apm.launch`
- `xasv_sim/launch/huitl_pre_train.launch`
- `xasv_sim/launch/xasv_huitl_policy_node.launch`
- `xasv_sim/launch/perception_test.launch`
- `xasv_sim/launch/robot_test.launch`
- `xasv_sim/launch/robot_test_ros.launch`
- `xasv_sim/launch/robot_test_ardupilot.launch`
- `ardupilot_hitl/launch/apm.launch`
- `ardupilot_hitl/launch/link.launch`
- `robots/migbot_gazebo/launch/*.launch`

Fluxo principal de simulacao (`xasv_sim/launch/xasv_sim.launch`):
- Inclui `gazebo_ros/empty_world.launch` com mundo em `xasv_sim/worlds`.
- Gera `robot_description` via xacro (`migbot_gazebo.urdf.xacro`) com flags de sensores e modo ArduPilot.
- Faz spawn do robo no Gazebo.
- Inicia `robot_state_publisher` e TFs estaticos.
- Se `ardupilot=false`: inicia controladores de esforco e `controller_spawner`.
- Se `ardupilot=true`: espera fluxo de controle via ArduPilot/plugin.

Fluxo HuITL pre-treino (`xasv_sim/launch/huitl_pre_train.launch`):
- Sobe MAVROS via `mavros/launch/node.launch` (perfil APM).
- Sobe `huitl_pretrain_pointcloud_node.py` para coleta CSV.

Fluxo HuITL politica (`xasv_sim/launch/xasv_huitl_policy_node.launch`):
- Sobe MAVROS (APM).
- Sobe `xasv_huitl_policy_node.py` com parametros de gating/escala/arquivo de modelo.

Fluxo HITL dedicado (`ardupilot_hitl/launch`):
- `apm.launch`: MAVROS.
- `link.launch`: `tx_data_node` + `rx_data_node`.

---

## 7) Plugins Gazebo e assets de simulacao

## 7.1) Compilacao de plugins (`xasv_sim/CMakeLists.txt`)

Bibliotecas principais compiladas:
- `gazebo_plugin_msgs` (protobuf gerado de `xasv_sim/plugins/msg/*.proto`)
- `Hydrodynamics`
- `gazebo_motor_model`
- `gazebo_usv_dynamics_plugin`
- `buoyancy_gazebo_plugin`
- `waypoint_markers`
- `follow_plugin`
- `gazebo_wind_plugin`
- `ArduPilotPlugin`
- `TrunkScaler`
- `BuoySpawner`
- `WorldGpsAlignMavlink`
- `WavefieldModelPlugin`
- `WavefieldVisualPlugin`

Mensagens proto locais:
- `xasv_sim/plugins/msg/CommandMotorSpeed.proto`
- `xasv_sim/plugins/msg/MotorSpeed.proto`
- `xasv_sim/plugins/msg/Wind.proto`
- `xasv_sim/plugins/msg/Float.proto`

Fontes importantes:
- `xasv_sim/plugins/src/ArduPilotPlugin.cc`
- `xasv_sim/plugins/include/ArduPilotPlugin.hh`
- `xasv_sim/plugins/src/gazebo_motor_model.cpp`
- `xasv_sim/plugins/src/gazebo_usv_dynamics_plugin.cpp`
- `xasv_sim/plugins/src/gazebo_wind_plugin.cpp`
- `xasv_sim/plugins/src/Wavefield*.cc`
- `xasv_sim/plugins/src/BuoySpawner.cc`
- `xasv_sim/plugins/src/TrunkScaler.cc`

## 7.2) Modelos e mundos

Modelos em `xasv_sim/models/` incluem:
- `ocean_waves/` (shaders Gerstner)
- `SAE_HYDRO_V0/`
- `branche1_buoy/`
- `trunk2_buoy/`

Mundos em `xasv_sim/worlds/` incluem:
- `madeira_river.world`
- `madeira_river_ritl.world`
- `madeira_river_TRY_AUTO_ALIGN.world`
- `Huitl_OA.world`
- `empty_river.world`

---

## 8) Pipeline IA/HuITL (dados -> treino -> politica)

Fase A - Coleta humana:
- Rodar simulacao + MAVROS + `huitl_pretrain_pointcloud_node.py`.
- Humano controla (RC), node registra sensores + acao humana no CSV.

Fase B - Treino supervisionado:
- Rodar `train_supervised.py --csv ...`.
- Gera modelo `trained_rc_policy.pt` com MLP 7->2.

Fase C - Inferencia online:
- Rodar `xasv_huitl_policy_node.py`.
- Em obstaculo frontal, aplica `RC override` em throttle/yaw.
- Sem obstaculo, remove override e devolve controle ao autopiloto.

Pontos criticos de reproduzibilidade:
- O vetor de features deve manter a mesma ordem/semantica no treino e na inferencia.
- Parametros de gating (`safe_dist`, `front_points_min`, `min_valid_range`) mudam comportamento drasticamente.

---

## 9) Testes e scripts operacionais

Scripts em `xasv_sim/tests/`:

1. `mitl_test.sh`
- Sobe simulacao (`ardupilot=false`), alocacao e teleop.
- Grava rosbag de topicos chave.
- Gera missao `.plan` via `rosgps2mission.py`.

2. `sitl_test.sh`
- Sobe simulacao (`ardupilot=true`).
- Sobe ArduPilot Rover SITL (`ardurover`, `--model gazebo-rover`).
- Checa saude de sensores e EKF/AHRS via pymavlink.
- Abre MAVProxy.

3. `hitl_test.sh`
- Sobe simulacao.
- Aguarda board Pixhawk.
- Sobe MAVProxy com serial + UDP outs.
- Sobe `ardupilot_hitl apm.launch` e `link.launch`.

Esses scripts sao referencia de validacao de regressao para a migracao ROS2.

---

## 10) Dependencias externas identificadas

## 10.1) Sistema/ROS (observado no repo)

De `install_deps.sh` e docs:
- ROS Noetic
- Gazebo Classic 11
- `ros-noetic-hector-gazebo-plugins`
- `ros-noetic-robot-localization`
- `ros-noetic-ros-control`
- `ros-noetic-ros-controllers`
- `ros-noetic-gazebo-ros`
- `ros-noetic-gazebo-plugins`
- `ros-noetic-realsense2-description`
- `libignition-math4-dev`
- `python3-pip`

## 10.2) Python
- `torch`
- `pymavlink`
- `MAVProxy`
- `bluerobotics-ping`

## 10.3) Repos/forks externos
- `livox_laser_simulation` (clonado no setup)
- `ping360_gazebo` (submodules)
- ArduPilot Rover (SITL e branch HITL custom mencionada no README)

---

## 11) Acoplamentos fortes e pontos de quebra na migracao

Prioridade ALTA:
1. Gazebo Classic plugins (`gazebo::`) -> Gazebo moderno (`gz-sim`/Ignition APIs).
2. Integacao ArduPilotPlugin + protocolo UDP + sincronismo de tempo.
3. MAVROS no ROS2 (mudancas de pacotes, plugins e interfaces).
4. Dependencia protobuf compilada com includes Gazebo Classic (`gazebo/msgs/proto`).

Prioridade MEDIA:
5. Port de nos C++ ROS (`roscpp`) para `rclcpp`.
6. Port de nos Python `rospy` para `rclpy`.
7. Launch XML ROS1 para launch Python ROS2.
8. Namespace/remap/parametros entre ROS1 e ROS2.
9. `ros_control`/controllers no fluxo MITL (avaliar `ros2_control`).

Prioridade BAIXA:
10. Scripts shell de orquestracao (principalmente ajustes de comandos/paths).
11. Ajustes de pacotes de descricao (xacro, state publishers).
12. Documentacao e automacao de setup.

---

## 12) Mapeamento ROS1 -> ROS2 por componente

## 12.1) Build system
- `catkin` -> `ament_cmake`/`ament_python`.
- Reescrever `CMakeLists.txt` de cada pacote.
- Atualizar `package.xml` para formato ROS2 com dependencias corretas.

## 12.2) Nodes C++
- `ros::NodeHandle`, `Publisher`, `Subscriber`, `spinOnce` -> equivalentes `rclcpp`.
- Revisar QoS de topicos sensiveis (estado/sensores/comandos).

## 12.3) Nodes Python
- `rospy` -> `rclpy`.
- Ajustar mecanismo de parametros, timers e shutdown hooks.

## 12.4) Launch
- Converter arquivos `.launch` para launch Python ROS2.
- Preservar argumentos e semantica condicional (`if/unless`).

## 12.5) Gazebo
- Decidir alvo:
  - Opcao A: manter Gazebo Classic (ponte temporaria).
  - Opcao B: migrar para gz-sim Garden/Harmonic (recomendado longo prazo).
- Se Opcao B, reescrever plugins e revisar pipeline de mensagens/protobuf.

## 12.6) MAVROS/MAVLink
- Validar paridade funcional do MAVROS ROS2 para:
  - estado de voo
  - RC in/out/override
  - setpoints globais
  - parametros
- Revalidar flows SITL e HITL com logs de latencia e estabilidade.

---

## 13) Plano de migracao recomendado (faseado)

Fase 1 - Baseline e congelamento
- Branch dedicada ROS2.
- Congelar cenarios de referencia e outputs esperados (MITL/SITL/HITL).
- Registrar metricas baseline (topicos, taxas, latencia, comportamento).

Checkpoint:
- Checklist de reproducao ROS1 validado em pelo menos 1 run por modo.

Fase 2 - Port de pacotes simples
- Migrar `teleop_wrench_keyboard`, `migbot_description`, `migbot_gazebo`.
- Criar launches ROS2 equivalentes minimos.

Checkpoint:
- Spawn do robo no Gazebo + teleop no ROS2.

Fase 3 - Port de `migbot_allocation`
- Migrar node C++ e validar saidas de 6 motores.

Checkpoint:
- Teste MITL basico funcionando no ROS2 (sem ArduPilot ainda).

Fase 4 - Port dos scripts IA
- Migrar `huitl_pretrain_pointcloud_node.py` e `xasv_huitl_policy_node.py` para `rclpy`.
- Manter formato de CSV e checkpoint.

Checkpoint:
- Coleta de novo CSV e inferencia da politica em loop.

Fase 5 - MAVROS ROS2
- Migrar launches de MAVROS e integrar topicos necessarios.
- Ajustar nomes/tipos de mensagem onde houver diferenca.

Checkpoint:
- Topicos de estado e RC override com comportamento equivalente ao ROS1.

Fase 6 - `ardupilot_hitl`
- Port de `rx_data_node` e `tx_data_node` para `rclcpp`.
- Validacao de bridge UDP + sensores em tempo real.

Checkpoint:
- HITL com Pixhawk recebendo sensores simulados e enviando comandos.

Fase 7 - Plugins Gazebo (trilha critica)
- Estrategia incremental:
  - primeiro plugins indispensaveis (ArduPilotPlugin, motor, dinamica, boiancia)
  - depois plugins de ambiente (wind/wave/spawner/scaler/alignment)

Checkpoint:
- SITL com dinamica coerente e sem regressao grave de comportamento.

Fase 8 - Regressao de sistema e hardening
- Reexecutar `mitl_test`, `sitl_test`, `hitl_test` (versoes ROS2).
- Instrumentar logs, tratar travamentos e latencias.
- Atualizar docs finais.

Checkpoint:
- Suite de smoke/regressao em ROS2 aprovada.

---

## 14) Requisitos para evitar delirios de implementacao (guardrails para outra IA)

1. Nao simplificar arquitetura removendo ArduPilotPlugin ou bridge HITL.
2. Nao trocar arbitrariamente tipos de mensagens MAVROS sem mapear paridade real.
3. Nao alterar ordem das features de treino/inferencia da MLP.
4. Nao assumir que Gazebo Classic plugins compilam em gz-sim sem reescrita.
5. Nao ignorar namespaces usados em MITL (`/migbot1/...`).
6. Nao quebrar scripts de teste; eles sao referencia operacional do projeto.
7. Nao substituir fluxo SITL/HITL por mock sem manter caminho real de validacao.

---

## 15) Arquivos de referencia essenciais

Arquitetura e docs:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PLUGINS.md`
- `docs/XITL.md`

Core simulacao:
- `xasv_sim/CMakeLists.txt`
- `xasv_sim/package.xml`
- `xasv_sim/launch/xasv_sim.launch`
- `xasv_sim/plugins/include/ArduPilotPlugin.hh`
- `xasv_sim/plugins/src/ArduPilotPlugin.cc`

IA HuITL:
- `xasv_sim/scripts/huitl_pretrain_pointcloud_node.py`
- `xasv_sim/scripts/train_supervised.py`
- `xasv_sim/scripts/xasv_huitl_policy_node.py`

HITL bridge:
- `ardupilot_hitl/src/rx_data.cpp`
- `ardupilot_hitl/src/tx_data.cpp`
- `ardupilot_hitl/launch/apm.launch`
- `ardupilot_hitl/launch/link.launch`

MITL utilitarios:
- `migbot_allocation/src/migbot_allocation.cpp`
- `teleop_wrench_keyboard/teleop_wrench_keyboard.py`
- `xasv_sim/scripts/rosgps2mission.py`

Testes:
- `xasv_sim/tests/mitl_test.sh`
- `xasv_sim/tests/sitl_test.sh`
- `xasv_sim/tests/hitl_test.sh`

---

## 16) Proximo passo recomendado

Comecar pela Fase 1 e Fase 2 com um artefato de comparacao explicito:
- tabela ROS1 vs ROS2 contendo para cada no:
  - nome
  - topicos pub/sub
  - parametros
  - frequencia esperada
  - dependencia externa

Esse artefato deve ser mantido atualizado durante toda a migracao para garantir paridade funcional e evitar regressao silenciosa.
