# Guia Prático: Migração de ASVs do ROS 1 (Gazebo Classic) para ROS 2 Jazzy (Gazebo Harmonic)

> **Versão:** 3.0 — 2026-05-08
> **Status do projeto-fonte (`xasv-ros2` / Migbot):** Fases 1 a 7 fechadas e validadas. Migbot navega no Gazebo Harmonic com ArduPilot Rover SITL + AP_DDS + QGroundControl, missão WP1 → WP2 em modo AUTO. Fase 8 (obstacle avoidance + IA) em aberto.

Este guia consolida as lições aprendidas durante a migração do projeto `xasv-sim` (Migbot) do ROS 1 + Gazebo Classic 11 para o ROS 2 Jazzy + Gazebo Harmonic. Serve como referência prática para outros projetos de embarcações autônomas (ASVs) e robótica aquática que precisem fazer essa transição.

A migração não é troca de sintaxe. É mudança completa de paradigma arquitetural: build system, comunicação simulador↔middleware, plugins, físico de fluidos, autopiloto e até a forma de organizar launch files.

Documentos detalhados deste mesmo repositório complementam este guia:
- [`GUIA_FASES.md`](./GUIA_FASES.md) — roteiro fase a fase já executado.
- [`BUOYANCY_FIX.md`](./BUOYANCY_FIX.md) — por que o barco "voa" e como travar.
- [`SPAWN_TROUBLESHOOTING.md`](./SPAWN_TROUBLESHOOTING.md) — spawn, colisão, CoM.
- [`MOTOR_MIXER_DOSSIER.md`](./MOTOR_MIXER_DOSSIER.md) — `ArduPilotPlugin`, `Thruster`, mixer Lua, death roll.
- [`FASE7_AP_DDS.md`](./FASE7_AP_DDS.md) — integração SITL/Gazebo via AP_DDS.
- [`FASE7_STATUS.md`](./FASE7_STATUS.md) — estado operacional, troubleshooting.
- [`3DMODELLING.md`](./3DMODELLING.md) — pipeline Blender → URDF/SDF.

---

## 1. Roadmap de Migração em Fases

Para outro projeto que comece do zero, reproduza este faseamento. Cada fase tem critério de aceite explícito antes de seguir adiante; resista à tentação de pular etapas.

| Fase | Objetivo | Critério de aceite |
|------|----------|--------------------|
| 0 — Leitura | Entender stack ROS 1 atual: launches, URDFs, plugins, fluxos. | Inventário em texto dos pacotes/plugins/tópicos. |
| 1 — Base mínima ROS 2 | Workspace `colcon` com pacotes `*_bringup`, `*_description`, `*_gazebo`, `*_control`, etc. URDF e mundo genéricos. `sim.launch.py` sobe Gazebo, `robot_state_publisher` e spawn. | TF e spawn validados no Gazebo Harmonic. |
| 2 — Controle por operador | `cmd_vel` ou wrench publicado por teleop, ponte `ros_gz_bridge` configurada. | Barco responde a teclado. |
| 3 — MAVLink/autopiloto externo | Bridge MAVLink (pymavlink ou MAVROS ROS 2) entre ROS 2 e ArduPilot SITL. QGC conecta. | Missão simples carregada e armada. |
| 4 — Mundo customizado | Substituir mundo genérico por SDF do cenário real. | Spawn conjunto robô + mundo, sem explosão. |
| 5 — Robô customizado | Portar URDF/Xacro real, sem plugins legados. Controle cinemático provisório (`VelocityControl`) só para validar geometria/spawn. | Robô flutua e move. |
| 6A — Sensores nativos | IMU/GPS/MAG/LIDAR como `<sensor>` nativos do Gazebo, expostos via `ros_gz_bridge`. | Tópicos `/imu`, `/navsat`, etc. publicando. |
| 6B — Dinâmica real | Remover `VelocityControl`. Adicionar `Buoyancy` (modo `graded_buoyancy`), `Hydrodynamics` (SNAME) e 6× `Thruster`. | Barco flutua estável e arrasta na água. |
| 7 — ArduPilot SITL completo | `ArduPilotPlugin` no URDF, mixer Lua, AP_DDS auto-start, MAVLink bridge para atuadores, QGC end-to-end. | Missão AUTO via QGC navegando WP1 → WP2. |
| 8 — Sensores avançados + IA | LiDAR/Sonar/Câmera adicionais, obstacle avoidance (Nav2 ou `OA_TYPE`/`PRX_TYPE`), inferência de política em `/ap/cmd_vel`. | Política PyTorch atuando online sobre o autopiloto. |

Princípio: **cada fase tem que entregar algo executável e validável no `ros2 topic`/`gz topic`/QGC**. Fases que só "preparam código" sem rodar são ímãs de regressão silenciosa.

---

## 2. Arquitetura e Pacotes (`catkin` → `colcon`)

Abandone `catkin_make`/`catkin build`. Use `colcon`:

```bash
cd ~/meu_ros2_ws
colcon build
source install/setup.bash
```

### Estrutura modular recomendada

A divisão em pacotes pequenos e bem demarcados faz diferença real para CI, code review e Injeção de Dependência:

- `meurobo_bringup` — launch files Python (`*.launch.py`) e configs globais (`*.yaml`).
- `meurobo_description` — URDF/Xacro e malhas.
- `meurobo_gazebo` — mundos `.sdf` e modelos estáticos do ambiente.
- `meurobo_control` — nós Python de teleop, alocação de wrench, etc.
- `meurobo_mavlink` — bridge MAVLink ↔ Gazebo `cmd_vel` quando rodar SITL/HITL.
- `meurobo_missions` — `.plan` do QGC, conversores de rosbag → missão.

> **Dica de arquitetura:** launch ROS 2 é Python. Use isso. Permite condicionais (`IfCondition`), sequenciamento (`TimerAction`), respawn (`respawn=True`), e parametrização limpa via `LaunchArgument`. Trate `sim.launch.py` como código de produção, não como script descartável.

### Build system por pacote

- `package.xml` formato 3, com dependências de runtime corretas (`<exec_depend>` para Python).
- C++: `ament_cmake` em vez de `catkin`.
- Python: `ament_python` ou `ament_cmake_python` (use `ament_python` para nós puros).

---

## 3. A Morte dos Plugins Antigos

No ROS 1 / Gazebo Classic, dependíamos de dezenas de `libgazebo_ros_*.so` embutidos no URDF. No Gazebo Harmonic, **simulador e middleware ROS 2 são entidades separadas**.

### Procedimento

1. **Remover** todos os `<plugin filename="libgazebo_ros...">` do URDF.
2. **Adicionar** plugins nativos (`gz-sim-*-system`).
3. **Pontear** com `ros_gz_bridge` no launch para tópicos que precisam aparecer no ROS 2.

```python
bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/model/meurobo/pose@geometry_msgs/msg/Pose[gz.msgs.Pose'],
    output='screen'
)
```

Plugins nativos chave para ASV no Harmonic:
- `gz-sim-buoyancy-system` (flutuabilidade)
- `gz-sim-hydrodynamics-system` (arrasto)
- `gz-sim-thruster-system` (propulsão)
- `gz-sim-imu-system`, `gz-sim-navsat-system`, `gz-sim-magnetometer-system`, `gz-sim-sensors-system`
- `ArduPilotPlugin` (de `ardupilot_gazebo`, externo) — interface FDM JSON com SITL.

---

## 4. Física de Embarcações: Fim do "Barco Voador"

Maior dor de cabeça da transição. O motor DART do Harmonic é rigoroso. Detalhes completos: [`BUOYANCY_FIX.md`](./BUOYANCY_FIX.md).

### 4.1. `uniform_fluid_density` é vilão

```xml
<plugin filename="gz-sim-buoyancy-system" name="gz::sim::systems::Buoyancy">
  <uniform_fluid_density>1000</uniform_fluid_density>
</plugin>
```

Aplica empuxo sobre **100% do volume de colisão, sempre**, sem fatiar pela linha d'água. Resultado: se `F_emp > F_grav`, sobe infinito como balão.

### 4.2. `graded_buoyancy` é a solução

```xml
<plugin filename="gz-sim-buoyancy-system" name="gz::sim::systems::Buoyancy">
  <graded_buoyancy>
    <default_density>1000</default_density>
    <density_change>
      <above_depth>0</above_depth>
      <density>0</density>
    </density_change>
  </graded_buoyancy>
  <surface>0 0 1 0</surface>
</plugin>
```

Fatia cada caixa de colisão na superfície (z=0), aplica empuxo só no submerso. Princípio de Arquimedes real.

Cálculo de calado de equilíbrio:
```
V_submerso = m / ρ
calado     = V_submerso / A_seção_pontões
```

Para o Migbot (142.5 kg, dois pontões 2.3×0.286): calado ≈ 11 cm, 32% submerso. Estável.

### 4.3. Regras de ouro do URDF para barcos

- **Volume de colisão × densidade do fluido = peso máximo suportado.** Não dimensione caixa de colisão "folgada"; ela vira empuxo extra.
- **Centro de massa (CoM):** `<origin>` do `<inertial>` deve ficar **dentro ou muito próximo** da geometria de colisão. CoM distante = instabilidade DART = explosão NaN.
- **CoM baixo no eixo Z:** efeito "joão-bobo". Se o barco virar de cabeça pra baixo ao tocar a água, abaixe o CoM.
- **CoM bem centralizado em X:** se CoM está muito à frente do volume submerso médio, a proa afunda. Recue a origem inercial.
- **Self-collision das hélices é assassina.** Cilindros de colisão das hélices intersectam o casco → forças repulsivas infinitas → barco explode (NaN) no spawn. **Remover todos os `<collision>` das hélices.** Plugins Thruster são puramente matemáticos, não precisam de colisão.
- **Não duplique tags:** uma tag `<origin>`/`<geometry>` por bloco `<collision>`. Múltiplas geometrias = blocos separados.
- **Sem rotações compensatórias** no `<visual>`/`<collision>` do `base_link`. Mantenha `rpy="0 0 0"`. Se o CAD original está certo, qualquer rotação extra duplica problema.

### 4.4. Spawn alto demais

Com `VelocityControl` (cinemático), spawnar em `z=1.5` parece funcionar (gravidade ignorada). Quando você remove `VelocityControl`, o barco cai 1.5 m e bate na água com violência. **Spawne em `z=0.1`–`0.3`**, logo acima da superfície.

Se está testando geometria e quer mascarar dinâmica, `VelocityControl` é OK temporariamente — só lembre que ele esconde 100% dos problemas físicos. Remova antes de declarar "barco funciona".

### 4.5. AHRS inconsistente entre sessões

Sintoma: `PreArm: AHRS: DCM Roll/Pitch inconsistent 175 deg` em sessão nova depois que sessões antigas spawnaram o barco invertido.

Causa: ArduPilot persiste calibração IMU em EEPROM/parâmetros. Próxima sessão acha que está de cabeça pra baixo.

Fix: usar `-w` (wipe) no `sim_vehicle.py` no launch:

```bash
sim_vehicle.py -v Rover -f JSON -w --console --map ...
```

Combine com `<modelXYZToAirplaneXForwardZDown>0 0 0 0 0 0</modelXYZToAirplaneXForwardZDown>` para evitar dupla rotação.

---

## 5. Hidrodinâmica e SNAME

Use `gz-sim-hydrodynamics-system` no `base_link`. Modelo SNAME clássico em cada DOF:

```
X = X_u_dot · u_dot + X_u · u + X_u_abs_u · u·|u|
```

- `X_u_dot` — massa adicional (added mass), inércia de fluido deslocado ao acelerar.
- `X_u` — arrasto linear, dominante em baixa velocidade.
- `X_u_abs_u` — arrasto quadrático, dominante em alta velocidade.

> **Atenção:** valores arbitrários fazem o barco acelerar ao infinito ou navegar como em mel. Use ensaios CFD, dados do casco real ou aproximações empíricas validadas. **Não chute.** Valores grandes demais "anulam" empuxo dos thrusters; valores pequenos demais explodem velocidade.

Valores referência usados no Migbot (`xU=-51.3`, `xUabsU=-72.4`) só servem como ordem de grandeza para ASVs de ~150 kg em rio; não copie cego.

---

## 6. Propulsão: A Armadilha do `Thruster` no Harmonic

Detalhes completos: [`MOTOR_MIXER_DOSSIER.md`](./MOTOR_MIXER_DOSSIER.md). Esta seção condensa o que custou semanas para descobrir.

### 6.1. `gz-sim-thruster-system` não lê velocidade da junta

Mesmo com `use_angvel_cmd=true`, o Thruster **não** observa `ω` real da junta. Ele assina explicitamente:

```text
/model/<robot>/joint/<joint_name>/cmd_vel
```

Calcula empuxo `T = Ct · ρ · D⁴ · |ω| · ω` a partir do **comando** publicado nesse tópico. Se ninguém publica, hélice gira (visualmente, via `ArduPilotPlugin`) mas força do Thruster é zero. Barco fica parado.

**Validação correta de empuxo:**
```bash
gz topic -e -t /model/migbot/joint/Engine_helice_1/force
```
Se `force = 0`, o problema é comando faltando, não falta de potência.

### 6.2. Eixo da junta = direção do empuxo

`Thruster` aplica força ao longo do eixo da junta. Para barco com proa em +X:

```xml
<axis xyz="1 0 0" />
```

Se você deixar `<axis xyz="0 1 0" />` (default Y), empuxo vai para o lado e o barco anda em círculos.

### 6.3. `ArduPilotPlugin` em `EFFORT` causa death roll

Lei de Newton: torque na junta da hélice gera contra-torque no casco. Com 6 motores em `<type>EFFORT</type>` e multiplicador alto (1000 N·m), o casco recebe ~3000 N·m de reação e capota como crocodilo.

Use `<type>VELOCITY</type>` no `ArduPilotPlugin`. Velocity comanda ω desejado sem aplicar contra-torque relevante:

```xml
<control channel="0">
  <jointName>Engine_helice_1</jointName>
  <multiplier>100.0</multiplier>
  <offset>-0.5</offset>
  <type>VELOCITY</type>
  <cmd_max>50.0</cmd_max>
  <cmd_min>-50.0</cmd_min>
</control>
```

### 6.4. Caminho validado dos atuadores: MAVLink bridge

Como `ArduPilotPlugin` girando junta não basta para `Thruster`, a solução validada é uma bridge MAVLink → ROS 2 → Gazebo:

```text
ArduPilot SERVO_OUTPUT_RAW
  → asv_mavlink/mavlink_bridge_node.py        (lê MAVLink UDP 14555)
  → /model/migbot/joint/Engine_helice_N/cmd_vel  (Float64, rad/s)
  → gz-sim-thruster-system                    (gera empuxo físico)
```

A bridge faz: PWM (1000–2000 µs) → ω (rad/s, escalonado) → publica em `cmd_vel` dos 6 thrusters.

Para outro projeto: mantenha um nó análogo em `<robo>_mavlink`. AP_DDS serve para telemetria e comandos de alto nível, **mas não substitui a bridge para os 6 atuadores**, porque `/ap/cmd_vel` opera no espaço de velocidade do veículo, não no espaço de cada thruster individual.

---

## 7. Mixer Lua para Frames Não Padronizados

Para ASV com 6 motores assimétricos (frame não suportado nativamente), use ArduPilot Scripting Matrix:

### 7.1. Parâmetros essenciais

```text
FRAME_CLASS 15            # Scripting Matrix
SCR_ENABLE 1
SERVO1_FUNCTION 94        # Script1
SERVO2_FUNCTION 95        # Script2
SERVO3_FUNCTION 96        # Script3
SERVO4_FUNCTION 97        # Script4
SERVO5_FUNCTION 98        # Script5
SERVO6_FUNCTION 99        # Script6
SERVO7_FUNCTION 70        # Throttle dummy (PreArm exige)
SERVO8_FUNCTION 26        # Steering dummy (PreArm exige)
ARMING_CHECK 0            # SITL only — em campo, deixe ligado
FS_THR_ENABLE 0           # SITL only
```

Sem `SERVO7=70` e `SERVO8=26`, o Rover bloqueia: `PreArm: no motor, sail or scripting outputs defined`.

### 7.2. Mixer híbrido AP/RC

Em modos assistidos (AUTO/GUIDED), o controlador do Rover popula `vehicle:get_control_output(3)` (throttle) e `vehicle:get_control_output(4)` (yaw). Em MANUAL com `FRAME_CLASS=15`, **essas APIs ficam zeradas** — o Rover espera que o script Lua leia o RC diretamente.

Solução híbrida: tenta `vehicle:get_control_output()`; se zero, cai para `rc:get_pwm()`:

```lua
local throttle_ap = vehicle:get_control_output(3) or 0.0
local throttle
if math.abs(throttle_ap) > 1e-3 then
    throttle = throttle_ap                   -- AUTO/GUIDED
    log_tag = "AP"
else
    local rc3 = rc:get_pwm(3) or 1500
    throttle = (rc3 - 1500) / 500.0          -- MANUAL
    log_tag = "RC"
end
```

Telemetria esperada no console: `LUA V5[AP]:` ou `LUA V5[RC]:`.

### 7.3. Bug de API Lua silencioso

`vehicle:get_control_output(N)` retorna **um único valor** (nem `ok, val`). Tentar desempacotar dois valores faz o script crashar silenciosamente — `script list` mostra rodando, mas servos travam em 1500.

```lua
-- ERRADO
local ok, val = vehicle:get_control_output(3)
-- CERTO
local val = vehicle:get_control_output(3) or 0.0
```

### 7.4. Onde colocar o script

ArduPilot procura em **dois** diretórios; mantenha cópias sincronizadas:

```bash
cp config/migbot_mixer.lua ~/ardupilot/scripts/
cp config/migbot_mixer.lua ~/ardupilot/Rover/scripts/
```

Versão idêntica nos dois evita "rodou ontem, hoje não".

---

## 8. AP_DDS: Como Configurar Sem Race Condition

Detalhes: [`FASE7_AP_DDS.md`](./FASE7_AP_DDS.md), [`FASE7_STATUS.md`](./FASE7_STATUS.md).

### 8.1. Por que AP_DDS

- Latência cai de ~50 ms (MAVROS) para ~2 ms (DDS).
- Tópicos `/ap/*` aparecem nativos no ROS 2.
- Pré-requisito para inferência de IA em loop fechado (PyTorch → `/ap/cmd_vel`).

### 8.2. Build do firmware com DDS

```bash
cd ~/Micro-XRCE-DDS-Gen
./gradlew build
export PATH=$PATH:~/Micro-XRCE-DDS-Gen/scripts

cd ~/ardupilot
./waf configure --board sitl --enable-DDS
./waf rover
```

### 8.3. Patches de compatibilidade (gerador 2.0.2)

O gerador atual rejeita argumentos novos do AP_DDS. Mantenha workarounds locais em `~/ardupilot/libraries/AP_DDS/`:

- `wscript`: remover `-default-container-prealloc-size` da chamada do `microxrceddsgen`.
- `AP_DDS_ExternalControl.cpp`: máscara local para `IGNORE_LATITUDE | IGNORE_LONGITUDE | IGNORE_ALTITUDE`.
- `AP_DDS_Client.cpp`: constantes locais para `FS_*` e `PARAMETER_*`.

Sem esses patches, o build morre em `Unknown argument -default-container-prealloc-size` ou em símbolos C++ ausentes.

### 8.4. Race condition no auto-start (e fix)

**Sintoma:** QGC mostra `Warning: DDS: No ping response, exiting`. SITL desiste do DDS na inicialização.

**Causa raiz:** `micro_ros_agent` e `sim_vehicle.py` subindo simultaneamente em `TimerAction(period=15.0)`. SITL ping no DDS antes do agent completar `bind` em `udp4:2019`.

**Fix no `sim.launch.py`:**

```python
micro_ros_agent = ExecuteProcess(
    cmd=micro_ros_agent_cmd,
    output='screen',
    respawn=True,
    respawn_delay=2.0,
    condition=IfCondition(ardupilot)
)

# Sequência com gap real, não simultâneo
delayed_micro_ros_agent = TimerAction(period=10.0, actions=[micro_ros_agent])
delayed_sitl            = TimerAction(period=18.0, actions=[sitl_process])
delayed_mavlink_bridge  = TimerAction(period=28.0, actions=[mavlink_bridge])
```

Princípios:
- **`respawn=True` para serviços auxiliares** (`micro_ros_agent`).
- **Gap real (≥ 8 s) entre serviços que se conversam por socket.** `TimerAction` simultâneo não é determinístico.
- Pré-condição: `pkill -f "micro_ros_agent\|MicroXRCEAgent"` antes de relançar, para liberar porta 2019. `errno: 98 EADDRINUSE` significa agent residual.

### 8.5. Diagnóstico rápido

```bash
ss -ulnp | grep 2019                  # agent escutando? sem listener => fail
ros2 topic list | grep /ap            # tópicos /ap/* visíveis?
ros2 topic hz /ap/pose/filtered       # ~20–25 Hz esperado
ros2 topic hz /ap/twist/filtered      # ~22 Hz
ros2 topic hz /ap/navsat              # ~4–5 Hz
```

### 8.6. Tópicos e serviços `/ap/*` esperados

```
/ap/pose/filtered         /ap/twist/filtered      /ap/navsat
/ap/geopose/filtered      /ap/battery             /ap/clock
/ap/cmd_vel               /ap/joy                 /ap/rc
/ap/status                /ap/tf                  /ap/tf_static
/ap/imu/experimental/data /ap/cmd_gps_pose        /ap/goal_lla

Serviços:
/ap/arm_motors            /ap/mode_switch         /ap/prearm_check
/ap/get_parameters        /ap/set_parameters      /ap/experimental/takeoff
```

### 8.7. AP_DDS não substitui a bridge MAVLink dos atuadores

Decisão validada: AP_DDS fica oficialmente como caminho de **telemetria, serviços e comandos ROS 2 de alto nível**. A bridge MAVLink continua sendo o **backend oficial dos atuadores** porque o `Thruster` precisa de `cmd_vel` por junta.

Para Fase 8: política IA pode publicar em `/ap/cmd_vel`, ArduPilot consome → mixer Lua → `SERVO_OUTPUT_RAW` → MAVLink bridge → thrusters. AP_DDS é a entrada, MAVLink ainda é a saída.

---

## 9. Sensores

Sensores agora são `<sensor>` nativos do Gazebo (`imu`, `navsat`, `magnetometer`, `gpu_lidar`, `camera`). Plugins `libgazebo_ros_*_sensor.so` morreram.

```xml
<gazebo reference="imu_link">
  <sensor name="imu_sensor" type="imu">
    <always_on>1</always_on>
    <update_rate>50</update_rate>
    <topic>imu</topic>
    <gz_frame_id>imu_link</gz_frame_id>
  </sensor>
</gazebo>
```

Dados saem em `gz.msgs.IMU` (Gazebo Transport). Para o ROS 2 ver, instancie `ros_gz_bridge` mapeando para `sensor_msgs/msg/Imu`.

> **Pegadinha de georreferência:** o `/navsat` publicado pelo sensor Gazebo pode estar em frame diferente do home do SITL (visto no Migbot: `/ap/navsat ≈ -8.79°` enquanto `/navsat` Gazebo `≈ -21.78°`). Alinhar a `<spherical_coordinates>` do mundo SDF com `LATITUDE`/`LONGITUDE` do `migbot_sitl.param`. Não é bloqueante para Fase 7; é débito técnico para Fase 8.

---

## 10. Autopiloto e Comunicação (MAVROS → AP_DDS + MAVLink Bridge)

Não use MAVROS no ROS 2 quando AP_DDS estiver disponível, **exceto** como bridge especializada:

| Função | Caminho recomendado | Por quê |
|--------|---------------------|---------|
| Telemetria (`pose`, `twist`, `navsat`) | AP_DDS `/ap/*` | Latência ~2 ms, nativo ROS 2. |
| Serviços (`arm`, `mode_switch`, params) | AP_DDS `/ap/*` services | Resposta direta no ROS 2. |
| Comando alto nível (`cmd_vel`) | AP_DDS `/ap/cmd_vel` | Compatível com Nav2 / política IA. |
| Atuação física dos thrusters | MAVLink bridge (`SERVO_OUTPUT_RAW` → `cmd_vel` por junta) | Frame customizado (FRAME_CLASS=15) com 6 motores não cabe no `/ap/cmd_vel` direto. |
| Missões (waypoints) | QGC ↔ MAVLink ↔ SITL | QGC é maduro e operacionalmente preferido. |

---

## 11. Validação e Sanity Check

A regra: **não declarar fase fechada sem teste automatizado.**

### 11.1. Sanity check fim-a-fim

Construa um nó que valida a cadeia inteira em segundos. Padrão no Migbot:

```bash
ros2 run asv_mavlink fase7_sanity_check
```

Verifica nessa ordem, com timeout:
1. `SERVO_OUTPUT_RAW` chegando do SITL via MAVLink.
2. `cmd_vel` sendo publicado pela bridge nas 6 juntas.
3. `force` retornado pelo `Thruster` (não-zero).
4. Pose do barco mudando (`/model/<robo>/pose`).

Saída esperada:
```text
OK: SERVO_OUTPUT_RAW, cmd_vel, force e pose mudaram.
```

Rode antes de demos, depois de qualquer rebuild de URDF/launch, e em CI.

### 11.2. Diagnóstico rápido por tópico

| Para ver | Comando |
|----------|---------|
| Comando angular chegando ao Thruster | `ros2 topic echo /model/<robo>/joint/Engine_helice_1/cmd_vel` |
| Força física gerada | `gz topic -e -t /model/<robo>/joint/Engine_helice_1/force` |
| Movimento real | `gz topic -e -t /world/<mundo>/dynamic_pose/info` |
| Bridge MAVLink rodando | `ros2 node list \| grep mavlink_bridge_node` |
| Mixer Lua vivo | `script list` no MAVProxy; mensagens `LUA V5[AP/RC]:` no console |

### 11.3. Lado Gazebo vs lado ROS

Sempre cheque os dois quando bridge falhar:

```bash
gz topic -l                           # Lista tópicos do Gazebo Transport
gz topic -e -t /<topico>              # Confirma física gerou dado
ros2 topic echo /<topico>             # Confirma bridge traduziu
```

Pacote sumiu entre os dois? Bridge mal configurada (tipo errado, direção errada, prefixo de namespace errado).

---

## 12. Procedimento Operacional: Modo Automático e Fallback

Tenha sempre **dois modos** documentados.

### 12.1. Modo automático (launch único)

```bash
cd ~/meu_ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch <robo>_bringup sim.launch.py ardupilot:=true
```

Tabela de timing dentro do launch (Migbot, pós-fix 2026-05-06):

| Componente | t (s) | Observação |
|------------|-------|------------|
| Gazebo + `ros_gz_bridge` | 0 | Mundo + modelo + bridges. |
| `micro_ros_agent` | 10 | `udp4 -p 2019`, `respawn=True`. |
| ArduPilot SITL | 18 | Ping DDS encontra agent listening. |
| `mavlink_bridge_node` | 28 | SITL já abriu UDP 14555. |

### 12.2. Modo manual (4 terminais) — fallback

Útil quando há porta residual, conflito, ou para depurar componente isolado.

```bash
# T0 — limpar
pkill -f "micro_ros_agent\|sim_vehicle\|ardurover\|gz sim\|parameter_bridge\|mavlink_bridge"
sleep 2
ss -ulnp | grep -E "2019|14555|14550"   # deve estar vazio

# T1 — Gazebo + bridges
ros2 launch <robo>_bringup sim.launch.py ardupilot:=false

# T2 — agent
source ~/micro_ros_ws/install/setup.bash
ros2 run micro_ros_agent micro_ros_agent udp4 -p 2019

# T3 — SITL
sim_vehicle.py -v Rover -f JSON -w --console --map \
  --enable-DDS --no-rebuild \
  --add-param-file ~/ros2_asv_ws/xasv-ros2/config/migbot_sitl.param \
  -l <lat>,<lon>,<alt>,0 \
  --out=udp:127.0.0.1:14550 \
  --out=udp:127.0.0.1:14555

# T4 — bridge MAVLink
ros2 run <robo>_mavlink mavlink_bridge_node.py \
  --ros-args -p connection:=udpin:0.0.0.0:14555
```

Documentar o fallback explicitamente economiza horas em demo.

---

## 13. Pipeline de Modelagem 3D (Blender-First)

Detalhes: [`3DMODELLING.md`](./3DMODELLING.md). Resumo do que vale carregar para outro projeto.

### 13.1. Mundo

Autorar mundo (rio, cais, dam, vegetação) inteiro em Blender. Exportar via script `bpy` (`sdf_exporter.py`):

- Itera meshes visíveis.
- Exporta um `.dae` por objeto.
- Gera `model_raw.sdf`, `model.sdf` (com colisão simplificada), `model.config`, `meshes/`.

Saída padrão `~/.gazebo/models/<MODEL_NAME>/`.

### 13.2. Robô

Autorar robô em Blender com convenção de naming: `col0..colN` para colisões, `helice*` para hélices. Exportar via `migbot2_xacro_exporter.py`:

- Triangulação + smooth shading.
- `.dae` para cada mesh.
- `migbot2.urdf.xacro` com `base_link`, juntas, inércias do AABB e bloco de plugins parametrizado por xacro.

Materiais: o exporter rewrite COLLADA effects para PHONG e converte cores difusas em PNG 1×1, para o OGRE do Gazebo Harmonic carregar consistente.

### 13.3. Vantagem

Permite iterar visual + físico no mesmo arquivo Blender e regenerar Gazebo com um clique. Para projetos novos, vale gastar 1 dia escrevendo o exporter; economiza semanas depois.

---

## 14. XITL Modes Adaptados ao ROS 2

Modos suportados (ver [`XITL.md`](./XITL.md) original do projeto):

| Modo | ROS 1 (legado) | ROS 2 (estado atual) |
|------|----------------|----------------------|
| **MITL** | Teleop wrench → `migbot_allocation` → controllers ros_control. | `asv_control/teleop_node.py` → `cmd_vel`/wrench → bridge → Gazebo. |
| **SITL** | ArduPilot SITL + MAVROS + `xasv_sim.launch`. | ArduPilot SITL + AP_DDS + MAVLink bridge + `sim.launch.py`. **Validado.** |
| **HITL** | `ardupilot_hitl` + Pixhawk 4 + custom MAVLink `GazeboMavlink`. | A portar para ROS 2 com mesma estratégia: bridge MAVLink/UDP, sensores Gazebo → MAVLink → board. |
| **RITL** | `trunk_scaler` plugin altera mesh em runtime. | Plugin equivalente em `gz-sim`; roadmap para Fase 8+. |
| **HuITL** | `huitl_pretrain_pointcloud_node.py` (rospy) + virtual joystick + dataset CSV. | Portar para `rclpy`, manter ordem do feature vector 7D, `/ap/joy` para virtual joystick. |

---

## 15. Convenções de Repositório

Conforme migração consolida, adote:

- **Conventional Commits.** Ex.: `feat(dynamics): add SNAME hydrodynamics parameters to hull`, `fix(bridge): publish cmd_vel for thruster N`.
- **TDD onde fizer sentido.** Sanity checks (ver §11) substituem testes unitários quando lógica é fortemente acoplada a simulador.
- **Modularidade absoluta.** Nada hardcoded ao simulador no código de percepção/navegação. Use `.yaml` para constantes mecânicas.
- **Diário do projeto** em `docs/diario/YYYY-MM-DD.md`. Template canônico em [`docs/diario/README.md`](./diario/README.md): contexto / o que evoluímos / o que aprendi / problemas / pendências / commits. Vale mais que comentários inline para entender por que decisões foram tomadas.
- **Documentação por fase.** Cada fase ganha um `FASEN_STATUS.md` quando fecha, com critério de aceite checado, comandos para reproduzir e troubleshooting. Não confie só em README global.
- **Branches por fase.** Ver [`branches_mapping.md`](./branches_mapping.md). Padrão: `feature/faseN-<escopo>`, mergeada na branch de integração corrente.

---

## 16. Riscos Conhecidos para Reproduzir em Outro ASV

Lista de armadilhas observadas durante a migração do Migbot, em ordem de "tempo perdido até descobrir":

1. **Plugin Buoyancy modo `uniform_fluid_density`.** Barco vira balão. — §4.1.
2. **Self-collision das hélices.** NaN na inicialização. — §4.3.
3. **`Thruster` com `use_angvel_cmd=true` não lê junta.** Hélice gira mas barco para. — §6.1.
4. **Eixo da junta errado.** Barco anda lateralmente. — §6.2.
5. **`ArduPilotPlugin` em `EFFORT` causa death roll.** — §6.3.
6. **Lua: `vehicle:get_control_output()` zerado em MANUAL com `FRAME_CLASS=15`.** — §7.2.
7. **Lua: API retorna 1 valor, não 2.** Crash silencioso. — §7.3.
8. **Mixer não carregado (script em só um dos dois diretórios).** — §7.4.
9. **AP_DDS race condition entre agent e SITL.** — §8.4.
10. **AHRS persistente entre sessões.** Sem `-w`, barco nasce certo mas SITL acha que está invertido. — §4.5.
11. **CoM longe do volume de colisão.** Instabilidade DART. — §4.3.
12. **Spawn alto demais ao remover `VelocityControl`.** Barco bate na água. — §4.4.
13. **Hidrodinâmica overdimensionada anula thrust.** — §5.
14. **`/navsat` Gazebo em frame diferente do home SITL.** — §9.
15. **Esperar `/ap/cmd_vel` substituir os 6 thrusters.** Não substitui. — §6.4 e §10.

Imprima esta lista e cole na parede antes de começar.

---

## 17. Próximos Passos (Fase 8)

Em aberto no projeto-fonte:

1. **Obstacle avoidance.** Migbot trava em obstáculos do `madeira_river_simple`. Curto prazo: waypoints longe; médio: `OA_TYPE` (BendyRuler/Dijkstra) + `PRX_TYPE` com sensor virtual no Gazebo; longo: Nav2 ROS 2 sobre `/ap/cmd_vel`.
2. **Stack de sensores extras.** LiDAR (Livox), Sonar (Ping360), Câmera D435 com bridges nativas.
3. **Política de IA.** Portar `huitl_pretrain_pointcloud_node.py` e `xasv_huitl_policy_node.py` de `rospy` para `rclpy`. Inferência publicando em `/ap/cmd_vel`. Ordem do feature vector 7D **não pode mudar** entre treino e inferência.
4. **Tendência em arco.** Revisar simetria lateral dos motores em relação ao CoM ou compensar no mixer.
5. **Tuning de navegação.** `CRUISE_SPEED`, `WP_RADIUS`, `TURN_RADIUS`, `ATC_SPEED_*`, `ATC_STR_*` com base em logs reais.
6. **Alinhamento georreferência** do `/navsat` Gazebo com home SITL/AP_DDS.

---

**Autor:** Equipe de Migração ASV — `xasv-ros2`
**Última atualização:** 2026-05-08
**Versão do guia:** 3.0 (consolida lições das Fases 1–7 e fix AP_DDS de 2026-05-06)
