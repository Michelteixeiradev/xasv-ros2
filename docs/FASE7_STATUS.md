# Fase 7 - Status Atual

> **Versao:** 2.2 - 2026-05-06  
> **Origem:** Resumo apos validacao do Migbot navegando no Gazebo Harmonic com ArduPilot Rover SITL, QGroundControl, AP_DDS e sanity check automatizado.  
> **Plano original:** [FASE7_AP_DDS.md](./FASE7_AP_DDS.md).  
> **Dossie tecnico:** [MOTOR_MIXER_DOSSIER.md](./MOTOR_MIXER_DOSSIER.md).

> **Atualizacao 2.2 (2026-05-06):** Fix de race no `sim.launch.py` para AP_DDS auto-start (`respawn=True` no `micro_ros_agent`, timing reordenado agent t=10s / SITL t=18s / bridge t=28s). Missao WP1->WP2 validada em AUTO via QGC sem warning `DDS: No ping response`. Limitacao conhecida: Migbot trava em obstaculos do `madeira_river_simple` (sem obstacle avoidance) - escopo Fase 8.

## Onde paramos

A stack ArduPilot SITL + Gazebo Harmonic + ROS 2 + QGroundControl esta funcional para navegacao do Migbot.

O barco agora se move em MANUAL e tambem executa missao iniciada pelo QGroundControl em AUTO. O problema "helices giram mas barco nao sai do lugar" foi resolvido.

AP_DDS tambem esta validado: o `micro-ros-agent` conecta ao SITL, o ROS 2 lista topicos/servicos `/ap/*`, e as taxas reais medidas foram aproximadamente 25.6 Hz em `/ap/pose/filtered`, 22.8 Hz em `/ap/twist/filtered` e 4.5 Hz em `/ap/navsat`.

A causa raiz nao era eixo, posicao Z das helices, hidrodinamica nem falta de thrust. O `gz-sim-thruster-system` com `use_angvel_cmd=true` nao le a velocidade real da junta. Ele escuta o topico:

```text
/model/migbot/joint/Engine_helice_N/cmd_vel
```

Antes, o `ArduPilotPlugin` fazia as juntas girarem, mas o `Thruster` continuava sem comando e gerava forca zero. A solucao validada foi recolocar a ponte MAVLink -> ROS 2 -> Gazebo no caminho dos atuadores:

```text
ArduPilot SERVO_OUTPUT_RAW
  -> asv_mavlink/mavlink_bridge_node.py
  -> /model/migbot/joint/Engine_helice_N/cmd_vel
  -> gz-sim-thruster-system
  -> empuxo fisico no barco
```

## Estado por subfase

### 7A - Dependencias e ArduPilot/Gazebo

Status: **validada**.

- `ardupilot_gazebo` esta instalado e o `ArduPilotPlugin` carrega no Gazebo.
- O SITL Rover em modo JSON conecta ao Gazebo.
- O `Micro-XRCE-DDS-Gen 2.0.2` compila com `./gradlew build`, mas ainda nao aceita `-default-container-prealloc-size`.
- O `ardurover` foi recompilado com `./waf configure --board sitl --enable-DDS` e `./waf rover`.
- Foram mantidos patches locais em `~/ardupilot/libraries/AP_DDS` para compatibilidade com o gerador 2.0.2.

### 7B - ArduPilotPlugin no URDF

Status: **validada para integracao SITL/Gazebo**.

Configuracao atual em `src/asv_description/urdf/migbot.urdf.xacro`:

- `ArduPilotPlugin` presente no modelo.
- `modelXYZToAirplaneXForwardZDown` ajustado para `0 0 0 0 0 0`.
- `gazeboXYZToNED` em `0 0 0 180 0 90`.
- Controles dos 6 canais em `type=VELOCITY`, com `cmd_min=-50` e `cmd_max=50`.
- Sensores do Gazebo chegam ao SITL.

Observacao importante: o `ArduPilotPlugin` girar as juntas nao basta para gerar empuxo no `Thruster`. A geracao fisica de empuxo validada hoje vem dos topicos `cmd_vel` publicados pela bridge MAVLink.

### 7C - Mixer Lua

Status: **validado**.

`config/migbot_mixer.lua` esta na versao V5:

- Usa `FRAME_CLASS=15`.
- Usa `SERVO1_FUNCTION` a `SERVO6_FUNCTION` como `94..99` (`Script1..Script6`).
- Mantem `SERVO7_FUNCTION=70` e `SERVO8_FUNCTION=26` como dummies para satisfazer o Rover.
- Quando a saida do controlador do Rover existe, usa `vehicle:get_control_output(3/4)` para AUTO/GUIDED.
- Quando essa saida esta zerada, cai para `rc:get_pwm(3/1)`, preservando MANUAL e teste `rc 3 1900`.
- Log esperado: `LUA V5[RC]` ou `LUA V5[AP]`.

Copias sincronizadas:

```text
~/ros2_asv_ws/xasv-ros2/config/migbot_mixer.lua
~/ros2_asv_ws/scripts/migbot_mixer.lua
~/ardupilot/scripts/migbot_mixer.lua
~/ardupilot/Rover/scripts/migbot_mixer.lua
```

### 7D - AP_DDS

Status: **validada**.

O `micro-ros-agent` sobe pelo launch, recebe sessao do SITL e expoe topicos/servicos AP_DDS no ROS 2.

Topicos observados incluem `/ap/pose/filtered`, `/ap/twist/filtered`, `/ap/navsat`, `/ap/geopose/filtered`, `/ap/battery`, `/ap/clock`, `/ap/cmd_vel`, `/ap/joy`, `/ap/rc` e `/ap/status`. Servicos observados incluem `/ap/arm_motors`, `/ap/mode_switch`, `/ap/prearm_check`, `/ap/get_parameters` e `/ap/set_parameters`.

Decisao da Fase 7: AP_DDS fica validado para telemetria, servicos e comandos ROS 2 de alto nivel; a bridge MAVLink continua sendo o backend oficial dos atuadores porque o `Thruster` precisa de `/model/migbot/joint/Engine_helice_N/cmd_vel`.

### 7E - Validacao End-to-End com QGroundControl

Status: **validada**.

Fluxo validado:

- Abrir QGroundControl.
- Criar/upload de waypoints.
- Armar.
- Iniciar missao em AUTO.
- Helices recebem comandos.
- Bridge publica `cmd_vel`.
- `Thruster` gera forca.
- Migbot navega no Gazebo e no mapa do QGC.
- **2026-05-06:** Transicao WP1 -> WP2 confirmada em AUTO sem warning DDS no QGC.
- **Limitacao conhecida:** Migbot colide em obstaculos do `madeira_river_simple` (sem obstacle avoidance ativo). Mitigar via waypoints longe de obstaculos ou ativar `OA_TYPE`/`PRX_TYPE` no ArduPilot. Solucao definitiva fica na Fase 8 (Nav2 + sensores Gazebo).

## Arquivos alterados/essenciais

| Arquivo | Estado |
|---------|--------|
| `src/asv_bringup/launch/sim.launch.py` | Inicia Gazebo, SITL, micro-ros-agent e `mavlink_bridge_node.py` quando `ardupilot:=true`. Abre saida MAVLink extra em UDP `14555`, expoe `/force` via ROS 2 e permite `use_mavlink_bridge:=false` para testes DDS. |
| `src/asv_bringup/package.xml` | Declara dependencia runtime de `asv_mavlink`. |
| `src/asv_mavlink/asv_mavlink/mavlink_bridge_node.py` | Le `SERVO_OUTPUT_RAW`, converte PWM para rad/s e publica `cmd_vel` dos 6 thrusters. |
| `src/asv_mavlink/asv_mavlink/fase7_sanity_check.py` | Teste automatizado `SERVO_OUTPUT_RAW -> cmd_vel -> force -> pose`. |
| `config/migbot_mixer.lua` | Mixer Lua V5, hibrido AP/RC. |
| `config/migbot_sitl.param` | Parametros Rover SITL, scripting matrix e tuning inicial de AUTO. |
| `src/asv_description/urdf/migbot.urdf.xacro` | Modelo fisico, thrusters, hidrodinamica e ArduPilotPlugin. |

## Como reproduzir o estado funcional

### Modo automatico (launch unico)

```bash
cd ~/ros2_asv_ws
source /opt/ros/jazzy/setup.bash
source ~/ros2_asv_ws/install/setup.bash
ros2 launch asv_bringup sim.launch.py ardupilot:=true
```

Ordem de subida no `sim.launch.py` (apos fix 2026-05-06):

| Componente | t (s) | Observacao |
|------------|-------|------------|
| Gazebo + ros_gz_bridge | 0 | Carrega mundo, modelo Migbot, bridges. |
| `micro_ros_agent` | 10 | `udp4 -p 2019`, `respawn=True` se cair. |
| ArduPilot SITL Rover | 18 | Ping DDS encontra agent ja listening. |
| `mavlink_bridge_node` | 28 | SITL ja exportou UDP `14555`. |

### Modo manual (4 terminais) - fallback se launch falhar

Util quando ha conflito de portas residuais ou para depuracao isolada do agent.

```bash
# T0 - matar residuos
pkill -f "micro_ros_agent\|sim_vehicle\|ardurover\|gz sim\|parameter_bridge\|mavlink_bridge"
sleep 2
ss -ulnp | grep -E "2019|14555|14550"  # deve estar vazio
```

```bash
# T1 - Gazebo + bridges
cd ~/ros2_asv_ws
source /opt/ros/jazzy/setup.bash
source ~/ros2_asv_ws/install/setup.bash
ros2 launch asv_bringup sim.launch.py ardupilot:=false
```

```bash
# T2 - micro-ros-agent (esperar mostrar "running... port: 2019")
source ~/micro_ros_ws/install/setup.bash
ros2 run micro_ros_agent micro_ros_agent udp4 -p 2019
```

```bash
# T3 - SITL
cd ~/ardupilot
python3 Tools/autotest/sim_vehicle.py -v Rover -f JSON -w --console --map \
  --enable-DDS --no-rebuild \
  --add-param-file ~/ros2_asv_ws/xasv-ros2/config/migbot_sitl.param \
  -l -8.798638,-63.952087,58,0 \
  --out=udp:127.0.0.1:14550 \
  --out=udp:127.0.0.1:14555
```

```bash
# T4 - bridge MAVLink
source /opt/ros/jazzy/setup.bash
source ~/ros2_asv_ws/install/setup.bash
ros2 run asv_mavlink mavlink_bridge_node.py --ros-args -p connection:=udpin:0.0.0.0:14555
```

Depois que Gazebo, SITL e bridge estiverem de pe:

```bash
~/QGroundControl-x86_64.AppImage
```

No QGC:

1. Criar uma missao com waypoints no rio.
2. Fazer upload.
3. Armar o veiculo.
4. Mudar para AUTO.
5. Iniciar a missao pelo slider.

## Troubleshooting AP_DDS

### `DDS: No ping response, exiting` no QGC/SITL

Cliente AP_DDS nao recebeu resposta do `micro-ros-agent` em `udp4:2019`.

Causas e fixes:

1. **Agent nao subiu.** Conferir log do launch por linha `UDPv4AgentLinux.cpp ... running... port: 2019`. Se ausente, verificar se launch foi com `ardupilot:=true`.
2. **Race agent x SITL.** Resolvido em 2.2 com agent em t=10s e SITL em t=18s. Se ainda ocorrer, aumentar gap.
3. **Porta 2019 ocupada (`errno: 98 EADDRINUSE`).** Outro agent residual segura porta. Mata e relanca:
   ```bash
   pkill -f "micro_ros_agent\|MicroXRCEAgent"
   sleep 2
   ss -ulnp | grep 2019  # deve estar vazio
   ```
4. **Workspace nao sourceado.** Confirmar que `~/micro_ros_ws/install/setup.bash` existe e build esta valido.

Validar reconexao apos fix:

```bash
ros2 topic list | grep /ap
ros2 topic hz /ap/pose/filtered  # esperado ~20-25 Hz
```

## Diagnosticos rapidos

Ver se a bridge esta rodando:

```bash
ros2 node list | grep mavlink_bridge_node
```

Ver comando angular chegando no Thruster:

```bash
ros2 topic echo /model/migbot/joint/Engine_helice_1/cmd_vel
```

Ver forca fisica gerada pelo Thruster:

```bash
ros2 topic echo /model/migbot/joint/Engine_helice_1/force
```

Ver movimento no mundo:

```bash
gz topic -e -t /world/madeira_river_simple/dynamic_pose/info
```

Ver o mixer no console do ArduPilot/MAVProxy:

```text
LUA V5[RC]: th=...
LUA V5[AP]: th=...
```

Rodar o sanity check completo:

```bash
ros2 run asv_mavlink fase7_sanity_check
```

Resultado validado:

```text
OK: SERVO_OUTPUT_RAW, cmd_vel, force e pose mudaram.
```

## Proximos passos

1. **Obstacle avoidance (Fase 8):** Migbot colide em obstaculos do `madeira_river_simple`. Mitigar curto prazo via waypoints longe de colisoes ou ativar `OA_TYPE` (BendyRuler/Dijkstra) + `PRX_TYPE` com sensor de proximidade no Gazebo. Solucao definitiva: Nav2 ROS 2 consumindo lidar/depth.

2. **Usar AP_DDS na Fase 8:** consumir `/ap/cmd_vel`, `/ap/joy` e servicos `/ap/*` para comandos ROS 2 de alto nivel, mantendo MAVLink como fallback dos atuadores.

3. **Tuning de navegacao:** ajustar `CRUISE_SPEED`, `WP_RADIUS`, `TURN_RADIUS`, `ATC_SPEED_*` e `ATC_STR_*` com base em logs de missao real no Gazebo.

4. **Corrigir tendencia em arco:** revisar simetria lateral das posicoes dos motores em relacao ao CoM e/ou aplicar compensacao no mixer.

5. **Alinhar georreferencia Gazebo:** o `/ap/navsat` esta coerente com o home SITL, mas `/navsat` do Gazebo ainda apareceu em outro referencial.

6. **Manter sanity check:** rodar `fase7_sanity_check` antes de sessoes longas ou demos com QGroundControl.
