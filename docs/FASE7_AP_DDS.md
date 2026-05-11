# Fase 7: Integracao ArduPilot SITL Avancada via AP_DDS

> **Versao:** 2.2 - 2026-05-06  
> **Status:** Navegacao MANUAL/AUTO via QGroundControl validada. AP_DDS validado para telemetria/comandos ROS 2; MAVLink permanece fallback oficial dos atuadores.  
> **Status operacional detalhado:** [FASE7_STATUS.md](./FASE7_STATUS.md).  
> **Dossie do problema de propulsao:** [MOTOR_MIXER_DOSSIER.md](./MOTOR_MIXER_DOSSIER.md).

> **Atualizacao 2.2 (2026-05-06):**
> - Fix de race AP_DDS auto-start em `sim.launch.py`: `respawn=True, respawn_delay=2.0` no `micro_ros_agent` e timing reordenado (agent t=10s, SITL t=18s, bridge MAVLink t=28s). Resolve warning `DDS: No ping response, exiting` em launches limpos.
> - Procedimento manual em 4 terminais documentado em [FASE7_STATUS.md](./FASE7_STATUS.md) como fallback.
> - Missao WP1 -> WP2 confirmada em AUTO via QGroundControl no `madeira_river_simple` sem warnings DDS.
> - Limitacao: Migbot colide em obstaculos do mundo (sem obstacle avoidance) - escopo Fase 8.

## 1. Objetivo

Integrar o Migbot ao ArduPilot Rover SITL no Gazebo Harmonic, permitindo que o QGroundControl controle missoes de waypoints sobre o mundo `madeira_river_simple`.

O objetivo original era remover a ponte pymavlink e usar AP_DDS como caminho nativo ArduPilot -> ROS 2. O estado validado em 2026-05-06 fecha a Fase 7 com AP_DDS funcional e fallback MAVLink preservado:

- `ArduPilotPlugin` conecta Gazebo e SITL em modo JSON.
- Lua V5 faz o mixer dos 6 motores no ArduPilot.
- `asv_mavlink/mavlink_bridge_node.py` ainda e necessario para atuadores.
- A bridge publica `/model/migbot/joint/Engine_helice_N/cmd_vel`, que e o comando realmente consumido pelo `gz-sim-thruster-system`.
- `micro-ros-agent` conecta ao SITL DDS e expoe topicos/servicos `/ap/*`.
- AP_DDS fica disponivel para telemetria, servicos e comandos de alto nivel como `/ap/cmd_vel`, mas ainda nao substitui `SERVO_OUTPUT_RAW -> cmd_vel` dos 6 thrusters.

## 2. Arquitetura Validada

```text
QGroundControl
  -> MAVLink
  -> ArduPilot Rover SITL
  -> Lua mixer V5
  -> SERVO_OUTPUT_RAW 1..6
  -> asv_mavlink/mavlink_bridge_node.py
  -> /model/migbot/joint/Engine_helice_N/cmd_vel
  -> gz-sim-thruster-system
  -> empuxo fisico no Gazebo
```

Em paralelo:

```text
Gazebo Harmonic
  -> ArduPilotPlugin
  -> sensores/FDM para o SITL via JSON
```

E tambem:

```text
ArduPilot Rover SITL com AP_DDS
  -> micro-ros-agent udp4:2019
  -> /ap/pose/filtered, /ap/twist/filtered, /ap/navsat, /ap/cmd_vel, servicos /ap/*
```

Ponto critico validado: `use_angvel_cmd=true` no `gz-sim-thruster-system` nao le a velocidade real da junta. Ele escuta `cmd_vel`. Se o `cmd_vel` nao for publicado, as helices podem girar visualmente e ainda assim a forca do `Thruster` fica zero.

## 3. Mapa das Subfases

| Subfase | Status | Resultado |
|---------|--------|-----------|
| 7A - Dependencias | Validada | `ardupilot_gazebo` funcional; `ardurover` recompilado com AP_DDS usando patch local de compatibilidade. |
| 7B - ArduPilotPlugin | Validada | SITL conecta ao Gazebo e recebe FDM/sensores. |
| 7C - Motor Mixer Lua | Validada | Lua V5 mistura throttle/steering para 6 motores via funcoes `94..99`. |
| 7D - AP_DDS | Validada | `micro-ros-agent` conecta ao SITL e topicos/servicos `/ap/*` aparecem no ROS 2. |
| 7E - End-to-End QGC | Validada | Missao AUTO pelo QGC faz o Migbot navegar no Gazebo. |

## 4. Subfase 7A - Dependencias

### Estado Atual

- Gazebo Harmonic: funcional.
- ROS 2 Jazzy: funcional.
- `ardupilot_gazebo`: instalado e usado pelo launch.
- ArduPilot Rover SITL JSON: funcional.
- AP_DDS: funcional com `Micro-XRCE-DDS-Gen 2.0.2` e patches locais de compatibilidade no ArduPilot.

### Notas AP_DDS

O gerador local continua rejeitando:

```text
Unknown argument -default-container-prealloc-size
```

Por isso foi mantido o workaround local em `~/ardupilot/libraries/AP_DDS/wscript`, removendo esse argumento da chamada do `microxrceddsgen`. O build DDS tambem exigiu compatibilidade com constantes IDL que o gerador 2.0.2 nao emite como simbolos C++:

- `AP_DDS_ExternalControl.cpp`: mascara local para `IGNORE_LATITUDE | IGNORE_LONGITUDE | IGNORE_ALTITUDE`.
- `AP_DDS_Client.cpp`: constantes locais para `FS_*` e `PARAMETER_*`.

Comandos validados:

```bash
cd ~/Micro-XRCE-DDS-Gen
git pull
./gradlew build
export PATH=$PATH:~/Micro-XRCE-DDS-Gen/scripts

cd ~/ardupilot
./waf configure --board sitl --enable-DDS
./waf rover
```

Validacao observada:

```bash
./waf configure --board sitl --enable-DDS
# Enabled DDS: yes
# Checking for program 'microxrceddsgen': ~/Micro-XRCE-DDS-Gen/scripts/microxrceddsgen

./waf rover
# 'rover' finished successfully
```

## 5. Subfase 7B - ArduPilotPlugin no URDF

### Estado Atual

O `ArduPilotPlugin` esta em `src/asv_description/urdf/migbot.urdf.xacro` e usa controles em formato `<control channel="N">`.

Configuracao relevante:

```xml
<modelXYZToAirplaneXForwardZDown degrees="true">0 0 0 0 0 0</modelXYZToAirplaneXForwardZDown>
<gazeboXYZToNED degrees="true">0 0 0 180 0 90</gazeboXYZToNED>

<control channel="0">
  <jointName>Engine_helice_1</jointName>
  <useForce>1</useForce>
  <multiplier>100.0</multiplier>
  <offset>-0.5</offset>
  <servo_min>1000</servo_min>
  <servo_max>2000</servo_max>
  <type>VELOCITY</type>
  <cmd_max>50.0</cmd_max>
  <cmd_min>-50.0</cmd_min>
</control>
```

O mesmo padrao existe para `Engine_helice_1` ate `Engine_helice_6`.

### Licao Aprendida

O `ArduPilotPlugin` em `type=VELOCITY` faz a junta girar, mas isso nao alimenta o `Thruster`. A forca fisica validada vem do `gz-sim-thruster-system` quando recebe `/cmd_vel`.

Nao tratar "helice girando" como prova de empuxo. A prova correta e:

```bash
gz topic -e -t /model/migbot/joint/Engine_helice_1/force
```

## 6. Subfase 7C - Motor Mixer Lua

### Estado Atual

Arquivo principal:

```text
config/migbot_mixer.lua
```

Versao validada: **V5**.

Caracteristicas:

- `FRAME_CLASS=15` no SITL.
- `SCR_ENABLE=1`.
- `SERVO1_FUNCTION` ate `SERVO6_FUNCTION` = `94..99`.
- `SERVO7_FUNCTION=70` e `SERVO8_FUNCTION=26` como saidas dummy.
- Em AUTO/GUIDED, usa `vehicle:get_control_output(3/4)` quando o controlador do Rover entrega saida.
- Em MANUAL ou quando a saida AP esta zerada, usa `rc:get_pwm(3/1)`.
- Log esperado: `LUA V5[AP]` ou `LUA V5[RC]`.

Copias que devem permanecer sincronizadas:

```bash
cp ~/ros2_asv_ws/xasv-ros2/config/migbot_mixer.lua ~/ros2_asv_ws/scripts/
cp ~/ros2_asv_ws/xasv-ros2/config/migbot_mixer.lua ~/ardupilot/scripts/
cp ~/ros2_asv_ws/xasv-ros2/config/migbot_mixer.lua ~/ardupilot/Rover/scripts/
```

Parametros essenciais:

```text
FRAME_CLASS 15
SCR_ENABLE 1
SERVO1_FUNCTION 94
SERVO2_FUNCTION 95
SERVO3_FUNCTION 96
SERVO4_FUNCTION 97
SERVO5_FUNCTION 98
SERVO6_FUNCTION 99
SERVO7_FUNCTION 70
SERVO8_FUNCTION 26
ARMING_CHECK 0
FS_THR_ENABLE 0
```

## 7. Subfase 7D - AP_DDS

### Estado Atual

Validada. O launch inicia `micro-ros-agent udp4 -p 2019`; o SITL conecta ao agent e cria publishers, subscribers e services AP_DDS no ROS 2.

Mesmo com AP_DDS validado:

- QGC e missoes continuam operacionais via MAVLink.
- A atuacao fisica dos thrusters continua via `asv_mavlink`.
- `/ap/cmd_vel` existe para comandos ROS 2 de alto nivel, mas nao substitui diretamente o caminho dos 6 motores.

### Criterios de Aceite

- [x] `micro-ros-agent udp4 -p 2019` inicia sem erro.
- [x] SITL conecta ao agent.
- [x] `ros2 topic list | grep /ap` mostra topicos AP.
- [x] `/ap/pose/filtered`, `/ap/twist/filtered` e `/ap/navsat` publicam.
- [x] O caminho AP_DDS foi comparado com MAVLink e MAVLink ficou como fallback oficial dos atuadores.

### Validacao Executada

```bash
cd ~/ros2_asv_ws
source /opt/ros/jazzy/setup.bash
source ~/ros2_asv_ws/install/setup.bash
ros2 launch asv_bringup sim.launch.py ardupilot:=true headless:=true

ros2 topic list | grep /ap
ros2 topic hz /ap/pose/filtered
ros2 topic hz /ap/twist/filtered
ros2 topic hz /ap/navsat
ros2 run asv_mavlink fase7_sanity_check
```

Taxas observadas:

| Topico | Taxa observada |
|--------|----------------|
| `/ap/pose/filtered` | ~25.6 Hz |
| `/ap/twist/filtered` | ~22.8 Hz |
| `/ap/navsat` | ~4.5 Hz |

Amostra AP_DDS:

```text
/ap/pose/filtered frame_id=base_link, position ~= x:3.51 y:0.08 z:0.08
/ap/navsat latitude=-8.798458 longitude=-63.951149 altitude=58.54
```

Observacao: o sensor Gazebo `/navsat` ainda apareceu em outra georreferencia (`latitude ~= -21.778`, `longitude ~= -43.369`). A telemetria AP_DDS esta coerente com o home do SITL; alinhar a georreferencia do sensor Gazebo fica como melhoria de sensores/geodesia, nao como bloqueio da Fase 7.

## 8. Subfase 7E - Validacao End-to-End

### Estado Atual

Validada com QGroundControl.

Sequencia operacional:

```bash
cd ~/ros2_asv_ws
source /opt/ros/jazzy/setup.bash
source ~/ros2_asv_ws/install/setup.bash
ros2 launch asv_bringup sim.launch.py ardupilot:=true
```

Depois:

```bash
~/QGroundControl-x86_64.AppImage
```

No QGC:

1. Planejar waypoints dentro do rio.
2. Fazer upload.
3. Armar o Migbot.
4. Entrar em AUTO.
5. Iniciar a missao pelo slider.

### Validacoes Recomendadas

Durante a missao:

```bash
ros2 node list | grep mavlink_bridge_node
ros2 topic echo /model/migbot/joint/Engine_helice_1/cmd_vel
ros2 topic echo /model/migbot/joint/Engine_helice_1/force
gz topic -e -t /world/madeira_river_simple/dynamic_pose/info
```

No console/MAVProxy:

```text
status SERVO_OUTPUT_RAW
script list
```

## 9. Topicos Esperados no Estado Atual

### Gazebo/ROS 2

| Topico | Tipo | Direcao | Uso |
|--------|------|---------|-----|
| `/model/migbot/joint/Engine_helice_N/cmd_vel` | `std_msgs/Float64` | ROS -> Gazebo | Comando angular dos thrusters. |
| `/model/migbot/joint/Engine_helice_N/force` | `std_msgs/Float64` | Gazebo -> ROS | Feedback de forca dos thrusters para diagnostico/teste. |
| `/model/migbot/pose` | `geometry_msgs/PoseArray` | Gazebo -> ROS | Pose publicada pelo Gazebo. |
| `/imu` | `sensor_msgs/Imu` | Gazebo -> ROS | IMU para comparacao/debug. |
| `/navsat` | `sensor_msgs/NavSatFix` | Gazebo -> ROS | GPS para comparacao/debug. |
| `/magnetometer` | `sensor_msgs/MagneticField` | Gazebo -> ROS | Magnetometro para comparacao/debug. |

### Gazebo Transport

| Topico | Uso |
|--------|-----|
| `/model/migbot/joint/Engine_helice_N/force` | Feedback de forca do `Thruster`. |
| `/world/madeira_river_simple/dynamic_pose/info` | Pose dinamica dos modelos. |

### AP_DDS

Topicos observados:

```text
/ap/airspeed
/ap/battery
/ap/clock
/ap/cmd_gps_pose
/ap/cmd_vel
/ap/geopose/filtered
/ap/goal_lla
/ap/gps_global_origin/filtered
/ap/imu/experimental/data
/ap/joy
/ap/navsat
/ap/pose/filtered
/ap/rc
/ap/status
/ap/tf
/ap/tf_static
/ap/time
/ap/twist/filtered
```

Servicos observados:

```text
/ap/arm_motors
/ap/experimental/takeoff
/ap/get_parameters
/ap/mode_switch
/ap/prearm_check
/ap/set_parameters
```

## 10. Criterios de Aceite Atualizados da Fase 7

Concluido:

- [x] Gazebo Harmonic carrega `madeira_river_simple`.
- [x] Migbot spawna e flutua.
- [x] ArduPilot Rover SITL conecta ao Gazebo via JSON.
- [x] QGroundControl conecta ao SITL.
- [x] Lua mixer V5 carrega e escreve `SERVO_OUTPUT_RAW`.
- [x] Bridge MAVLink publica `cmd_vel` dos 6 thrusters.
- [x] `Thruster` gera forca fisica.
- [x] MANUAL com `rc 3 1900` move o barco.
- [x] AUTO via QGC move o barco em missao.
- [x] Recompilar `ardurover` com AP_DDS.
- [x] Validar topicos `/ap/*`.
- [x] Decidir atuadores: manter bridge MAVLink como fallback oficial.
- [x] Criar teste automatizado de sanidade para `SERVO_OUTPUT_RAW -> cmd_vel -> force -> pose`.

Pendente pos-Fase 7:

- [ ] Refinar tuning fino de navegacao e curva com logs de missoes longas.
- [ ] Alinhar georreferencia do sensor Gazebo `/navsat` com o home do SITL/AP_DDS.

## 11. Proximos Passos

1. Usar `ros2 run asv_mavlink fase7_sanity_check` como teste rapido antes de missoes.
2. Afinar os parametros de Rover para missoes mais suaves no rio.
3. Corrigir ou compensar tendencia em arco por assimetria lateral com base em logs.
4. **Fase 8 - Obstacle avoidance:** Migbot trava em obstaculos do `madeira_river_simple`. Avaliar `OA_TYPE` (BendyRuler/Dijkstra) + `PRX_TYPE` com sensor virtual no Gazebo, ou Nav2 ROS 2 sobre `/ap/cmd_vel`.
5. Na Fase 8, consumir `/ap/cmd_vel`/servicos AP_DDS para comandos ROS 2 de alto nivel, mantendo o caminho MAVLink dos thrusters como fallback operacional.

## 12. Historico de Race Condition AP_DDS (2026-05-06)

Sintoma observado: warning recorrente no QGC/SITL:

```text
Warning: DDS: No ping response, exiting
```

Causa raiz: no `sim.launch.py` v2.1, `micro_ros_agent` e `sim_vehicle.py` subiam ambos em `TimerAction(period=15.0)`. SITL podia iniciar ping ao DDS antes do agent completar `bind` em `udp4:2019`, soltar timeout e desistir. Em paralelo, se um agent manual ja segurasse a porta, respawn do launch quebrava com `errno: 98 EADDRINUSE`.

Fix v2.2 (`sim.launch.py:130-180`):

```python
micro_ros_agent = ExecuteProcess(
    cmd=micro_ros_agent_cmd,
    output='screen',
    respawn=True,
    respawn_delay=2.0,
    condition=IfCondition(ardupilot)
)

delayed_micro_ros_agent = TimerAction(period=10.0, actions=[micro_ros_agent])
delayed_sitl = TimerAction(period=18.0, actions=[sitl_process])
delayed_mavlink_bridge = TimerAction(period=28.0, actions=[mavlink_bridge])
```

Validacao pos-fix:

- Agent inicia em t=10s, listening em `udp4:2019` antes do SITL.
- SITL inicia em t=18s, encontra agent pronto, sessao DDS estabelecida sem warning.
- `/ap/pose/filtered` em ~20 Hz (ligeiramente abaixo dos 25.6 Hz baseline, aceitavel).
- Missao WP1 -> WP2 em AUTO sem reincidencia do warning.

Pre-condicao operacional: matar agentes manuais residuais antes de relancar (`pkill -f "micro_ros_agent\|MicroXRCEAgent"`), para evitar `errno: 98`.
