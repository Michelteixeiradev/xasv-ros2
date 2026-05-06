# Dossiê Técnico: Problema de Propulsão do ASV Migbot

> **Data:** 2026-05-06  
> **Objetivo:** Documentar TUDO que foi tentado para fazer o barco Migbot navegar no Gazebo Harmonic controlado pelo ArduPilot SITL.  
> **Status:** ⚠️ NÃO RESOLVIDO — hélices giram mas o barco não se move (ou vira de cabeça para baixo quando se move).

---

## 1. Visão Geral da Arquitetura

```
┌──────────────┐     PWM (1000-2000)     ┌──────────────────┐     Torque/Vel     ┌─────────────────┐
│  ArduPilot   │ ──────────────────────> │  ArduPilotPlugin │ ───────────────> │  Joints (6x)    │
│  Rover SITL  │     via JSON UDP        │  (Gazebo)        │                  │  Engine_helice_* │
│  FRAME_CLASS │                         │                  │                  │                  │
│  = 15        │                         │  type=VELOCITY   │                  │  axis: 1 0 0     │
│  (Scripting) │                         │  multiplier=100  │                  │                  │
└──────┬───────┘                         └──────────────────┘                  └────────┬─────────┘
       │                                                                                │
       │  Lua Script                                                          ω (angvel)│
       │  (migbot_mixer.lua)                                                            │
       │  Lê rc:get_pwm(3)                                                              ▼
       │  Escreve SRV_Channels                                               ┌─────────────────┐
       │  :set_output_pwm(94..99)                                            │  Thruster Plugin │
       │                                                                     │  use_angvel_cmd  │
       └──> SERVO1..6 (func 94-99)                                          │  = true          │
            SERVO7 (func 70 = Throttle dummy)                                │  thrust_coeff    │
            SERVO8 (func 26 = Steering dummy)                                │  = 0.05          │
                                                                             │  prop_diameter   │
                                                                             │  = 0.2           │
                                                                             │  Gera empuxo ao  │
                                                                             │  longo do eixo   │
                                                                             │  da junta (X)    │
                                                                             └─────────────────┘
```

### Arquivos-chave:
| Arquivo | Caminho | Descrição |
|---------|---------|-----------|
| URDF | `src/asv_description/urdf/migbot.urdf.xacro` | Modelo físico, plugins, colisão |
| Lua Mixer | `config/migbot_mixer.lua` | Script que traduz throttle/steering → PWM dos 6 motores |
| Parâmetros SITL | `config/migbot_sitl.param` | Configuração do ArduPilot Rover |
| Launch File | `src/asv_bringup/launch/sim.launch.py` | Orquestra Gazebo + SITL + bridges |

---

## 2. Problemas Encontrados e Soluções Tentadas (Cronológico)

### 2.1 Servos presos em 1500 PWM (Motores mudos)

**Sintoma:** `status SERVO_OUTPUT_RAW` sempre retornava 1500 em todos os canais, mesmo após `arm throttle` e `rc 3 1900`.

**Causa 1 — Script Lua não carregava:**
- O ArduPilot procura scripts em `~/ardupilot/scripts/` E em `~/ardupilot/Rover/scripts/`.
- Existiam versões duplicadas e conflitantes em ambas as pastas.
- ✅ **Solução:** Apagar todas as cópias e copiar a versão correta para AMBAS as pastas.

**Causa 2 — Bug de retorno da API Lua:**
- `vehicle:get_control_output(3)` retorna **um único valor** (number ou nil) na versão do ArduPilot usada.
- O código tentava desempacotar dois valores (`local ok, val = ...`), causando crash silencioso do script.
- ✅ **Solução:** Usar `local throttle = vehicle:get_control_output(3) or 0.0`.

**Causa 3 — SERVO_FUNCTION errado:**
- Usávamos funções 33-38 (Motor1-Motor6), mas `FRAME_CLASS=15` exige funções 94-99 (Script1-Script6).
- O ArduPilot reportava: `PreArm: no motor, sail or scripting outputs defined`.
- ✅ **Solução:** Mudar `SERVO1_FUNCTION` de 33 para 94, etc.

**Causa 4 — PreArm checks bloqueando armamento:**
- O Rover exige que pelo menos uma função de motor "conhecida" esteja mapeada.
- ✅ **Solução:** Adicionar servos dummy: `SERVO7_FUNCTION 70` (Throttle) e `SERVO8_FUNCTION 26` (Steering).
- ✅ **Solução extra:** `ARMING_CHECK 0` e `FS_THR_ENABLE 0` para ambiente SITL.

### 2.2 `vehicle:get_control_output()` retorna 0 em MANUAL

**Sintoma:** O script Lua mostrava `th=0.00` mesmo com `rc 3 1900`. Mas `servo7_raw = 1504` (dummy Throttle) se movia.

**Causa:** Em modo MANUAL com `FRAME_CLASS=15`, o ArduRover NÃO popula `get_control_output()`. Essa API só funciona em modos assistidos (AUTO, GUIDED). Em MANUAL, o Rover espera que o script Lua leia o RC diretamente.

**✅ Solução (versão atual do script):** Usar `rc:get_pwm(3)` e `rc:get_pwm(1)` diretamente:
```lua
local rc3 = rc:get_pwm(3)
local throttle = 0.0
if rc3 then throttle = (rc3 - 1500) / 500.0 end
```

**✅ Correção 2026-05-06:** O script agora usa uma estratégia híbrida. Quando `vehicle:get_control_output()` entrega throttle/yaw não nulos, o mixer usa a saída processada do controlador do Rover (AUTO/GUIDED). Quando ela está zerada, cai para `rc:get_pwm()` (MANUAL e teste `rc 3 1900`).

### 2.3 Hélices giram mas barco não se move

**Sintoma:** As hélices giram visualmente, o log mostra `th=1.00`, mas o barco fica parado na água.

**Causa:** O ArduPilotPlugin aplica torque/velocidade nas **juntas** das hélices. Isso faz girar a hélice visual, mas NÃO gera empuxo no barco. O empuxo é responsabilidade do plugin **gz-sim-thruster-system**.

**Tentativas de solução:**

| Tentativa | `use_angvel_cmd` | Resultado |
|-----------|-----------------|-----------|
| `false` | Thruster escuta tópico `cmd_thrust` | ❌ Ninguém publica nesse tópico |
| `true` | Thruster escuta tópico `cmd_vel` | ⚠️ Só gera empuxo se alguém publicar `/model/.../cmd_vel` |

**✅ Correção 2026-05-06:** `use_angvel_cmd=true` **não** lê a velocidade real da junta. No Gazebo Sim 8 (`gz-sim-thruster-system`), esse modo assina `/model/<namespace>/joint/<joint_name>/cmd_vel`, calcula o empuxo a partir da velocidade angular comandada, e publica feedback em `/force`. Portanto, o `ArduPilotPlugin` girar a junta diretamente não basta para gerar empuxo; é necessário publicar nos tópicos `cmd_vel` dos thrusters.

**Solução atual:** manter `use_angvel_cmd=true` e iniciar automaticamente `asv_mavlink/mavlink_bridge_node.py` no `sim.launch.py`. O SITL agora abre uma saída MAVLink extra em `udp:127.0.0.1:14555`; a bridge lê `SERVO_OUTPUT_RAW` e publica `/model/migbot/joint/Engine_helice_N/cmd_vel`.

### 2.4 Barco vira de cabeça para baixo ao acelerar

**Sintoma:** Com multiplicador alto (200-1000) e `type=EFFORT`, ao dar throttle o barco fazia um "death roll" e virava de ponta-cabeça.

**Causa:** Lei de Newton — quando o ArduPilotPlugin aplica torque para girar a hélice, o casco recebe torque OPOSTO. Com 6 motores a 1000 N·m cada (todos girando na mesma direção), o casco recebia 3000 N·m de torque de reação, fazendo-o girar como um crocodilo.

**Tentativas:**

| Multiplicador | Tipo | Resultado |
|--------------|------|-----------|
| 1000 | EFFORT | ❌ Barco faz death roll |
| 200 | EFFORT | ❌ Barco faz death roll |
| 10 | EFFORT | ❌ Hélices giram muito devagar, sem empuxo |
| 100 | VELOCITY | ⏳ **Tentativa atual** — elimina torque de reação |

**✅ Solução atual:** Mudamos de `<type>EFFORT</type>` para `<type>VELOCITY</type>`. Com VELOCITY, o ArduPilotPlugin comanda a velocidade angular desejada da junta SEM aplicar torque de reação no casco.

### 2.5 Eixo da junta errado (empuxo lateral)

**Sintoma:** Mesmo com tudo conectado, o barco se movia de forma estranha (lateral/circular).

**Causa:** O eixo original das juntas era `<axis xyz="0 1 0" />` (eixo Y = lateral). O Thruster gera empuxo ao longo do eixo da junta. Com eixo Y, o empuxo ia para os LADOS, não para frente.

**✅ Solução:** Alterado para `<axis xyz="1 0 0" />` (eixo X = longitudinal/frente). Agora o empuxo vai para frente.

> ⚠️ **Efeito colateral visual:** A hélice agora gira em torno do eixo X. Dependendo de como o mesh `.dae` foi modelado, a animação visual pode parecer diferente (wobble vs. spin suave).

### 2.6 AHRS inconsistente (175 graus)

**Sintoma:** `PreArm: AHRS: DCM Roll/Pitch inconsistent 175 deg`

**Causa 1:** O ArduPilot salvava calibração do IMU de sessões anteriores (quando o barco nascia invertido). Na próxima sessão, com o barco agora de pé, ele achava que estava de ponta-cabeça.
- ✅ **Solução:** Adicionamos a flag `-w` (wipe) no `sim_vehicle.py` no launch file para limpar o EEPROM a cada inicialização.

**Causa 2:** A transformação `<modelXYZToAirplaneXForwardZDown>` estava com rotação de 180° que duplicava a inversão.
- ✅ **Solução:** Mudamos de `0 0 0 180 0 0` para `0 0 0 0 0 0`.

### 2.7 Barco inclinando para um lado (bombordo submerso)

**Sintoma:** O barco flutuava com o lado esquerdo afundando e o direito levantando.

**Causa:** Centro de Massa no eixo Y (`0.095`) estava levemente deslocado em relação ao centro de flutuabilidade dos pontões. O eixo Z estava alto demais (`0.15`), reduzindo a estabilidade lateral.

**✅ Solução:** Ajustamos o CoM para `Y=0.096` (centralizado) e `Z=0.05` (mais baixo = maior estabilidade):
```xml
<origin xyz="0.150 0.096 0.05" rpy="0 0 0" />
```

---

## 3. Estado Atual dos Arquivos (Snapshot)

### 3.1 migbot_mixer.lua (Versão 5)
- Usa `vehicle:get_control_output(3/4)` quando o controlador do Rover está ativo
- Cai para `rc:get_pwm(3)` e `rc:get_pwm(1)` quando a saída do controlador está zerada
- Converte PWM → range [-1, +1]
- Aplica mixing baseado em posição lateral dos motores (DY)
- Escreve para funções 94-99 via `SRV_Channels:set_output_pwm()`
- Mostra telemetria: `LUA V5[RC/AP]: th=X.XX, st=X.XX, rc3=XXXX, rc1=XXXX`

### 3.2 migbot_sitl.param
- `FRAME_CLASS 15` (Scripting Matrix)
- `SCR_ENABLE 1`
- `SERVO1-6_FUNCTION 94-99` (Script1-6)
- `SERVO7_FUNCTION 70`, `SERVO8_FUNCTION 26` (dummies)
- `ARMING_CHECK 0`, `FS_THR_ENABLE 0`
- Tuning de AUTO mode (ATC_SPEED_FF, CRUISE_SPEED, etc.)

### 3.3 migbot.urdf.xacro (ArduPilotPlugin)
- `modelXYZToAirplaneXForwardZDown`: `0 0 0 0 0 0`
- `gazeboXYZToNED`: `0 0 0 180 0 90`
- 6 controles: channel 0-5, multiplier=100, type=VELOCITY, offset=-0.5
- cmd_max=50, cmd_min=-50

### 3.4 migbot.urdf.xacro (Thruster Plugins)
- 6x `gz-sim-thruster-system`
- `thrust_coefficient=0.05`, `fluid_density=997.8`, `propeller_diameter=0.2`
- `use_angvel_cmd=true`
- Juntas com `axis xyz="1 0 0"`

### 3.5 sim.launch.py
- Flag `-w` para wipe EEPROM
- `--no-rebuild` para evitar recompilação
- `--enable-DDS` para AP_DDS
- `--out=udp:127.0.0.1:14555` para alimentar a bridge MAVLink → Thruster
- `asv_mavlink/mavlink_bridge_node.py` iniciado automaticamente quando `ardupilot:=true`
- micro-ros-agent na porta UDP 2019

---

## 4. Problema Principal Não Resolvido

**O barco NÃO navega.** As hélices giram quando throttle é aplicado, mas o barco permanece estacionário na água. Isso sugere que o plugin Thruster não está gerando empuxo suficiente, ou que a direção do empuxo ainda está incorreta.

### Hipóteses para investigar:

1. **Eixo de empuxo ainda errado:** Verificar se o eixo `1 0 0` das juntas está realmente gerando empuxo ao longo de X do barco, ou se há alguma transformação que o rotaciona.

2. **Posição Z das hélices:** As hélices estão em `Z=0.66`. Se a superfície da água está em `Z=0`, as hélices podem estar **acima da linha d'água**, onde o Thruster não gera empuxo (sem fluido). Verificar a posição vertical do barco na água.

3. **Thrust insuficiente:** Com `thrust_coefficient=0.05`, `propeller_diameter=0.2m` e `fluid_density=997.8`, o Gazebo Sim 8 usa:
   ```
   T = Ct * ρ * D⁴ * |ω| * ω
   T = 0.05 * 997.8 * 0.2⁴ * |ω| * ω
   T ≈ 0.0798 * |ω| * ω
   ```
   A 50 rad/s: T ≈ 199.6 N por motor, ~1197 N total. Para 142kg, isso é mais que suficiente para movimento visível. Se `/force` continuar em zero, o problema é comando ausente no `Thruster`, não falta de potência.

4. **Hidrodinâmica excessiva:** O plugin `gz-sim-hydrodynamics-system` tem `xU = -51.3` (resistência linear) e `xUabsU = -72.4` (resistência quadrática). Isso pode estar "anulando" a pequena força dos thrusters.

5. **Arquitetura alternativa:** Considerar abandonar o acoplamento `ArduPilotPlugin → Joint → Thruster` e usar tópicos `cmd_vel`/`cmd_thrust` diretamente via um nó ROS 2 que leia os servos do ArduPilot (MAVLink agora; AP_DDS quando disponível) e publique nos tópicos do Thruster.

### Abordagem alternativa sugerida:
```
ArduPilot → MAVLink/AP_DDS → ROS 2 → /model/migbot/joint/Engine_helice_X/cmd_vel → Thruster
```
Isso eliminaria o ArduPilotPlugin como intermediário para a propulsão (mantendo-o apenas para sensores).

---

## 5. Comandos de Teste

```bash
# Terminal 1 — Simulação
cd ~/ros2_asv_ws && source install/setup.bash
ros2 launch asv_bringup sim.launch.py world:=madeira_river_simple.sdf ardupilot:=true

# Terminal 2 — MAVProxy
mavproxy.py --master tcp:127.0.0.1:5762

# Dentro do MAVProxy
mode MANUAL
rc 3 1500
arm throttle
rc 3 1900
status SERVO_OUTPUT_RAW
```

### Verificações diagnósticas:
```bash
# Ver se os tópicos de thrust estão recebendo algo
ros2 topic echo /model/migbot/joint/Engine_helice_1/cmd_vel

# Ver se o Thruster está gerando força (feedback Gazebo)
gz topic -e -t /model/migbot/joint/Engine_helice_1/force

# Ver se a bridge MAVLink está publicando
ros2 node list | grep mavlink_bridge_node

# Ver se o script Lua está rodando (no MAVProxy)
script list
```

---

## 6. Rebuild Necessário Após Mudanças

```bash
# Se mudou o URDF:
cd ~/ros2_asv_ws && colcon build --packages-select asv_description && source install/setup.bash

# Se mudou o Lua:
cp ~/ros2_asv_ws/xasv-ros2/config/migbot_mixer.lua ~/ardupilot/scripts/
cp ~/ros2_asv_ws/xasv-ros2/config/migbot_mixer.lua ~/ardupilot/Rover/scripts/

# Se mudou o launch:
cd ~/ros2_asv_ws && colcon build --packages-select asv_bringup && source install/setup.bash
```
