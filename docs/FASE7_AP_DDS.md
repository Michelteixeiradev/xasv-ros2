# Fase 7: Integracaoo ArduPilot SITL Avancada via AP_DDS

> **Versao:** 1.0 — Maio 2026
> **Pre-requisito:** Fases 1-6 concluidas e validadas (barco migbot flutuando com fisica real, 6 thrusters, hidrodinamica SNAME, sensores IMU/GPS/Mag funcionando via ros_gz_bridge).

---

## Indice

1. [Objetivo Geral](#1-objetivo-geral)
2. [Mapa de Dependencias entre Subfases](#2-mapa-de-dependencias-entre-subfases)
3. [Pre-requisitos Tecnicos](#3-pre-requisitos-tecnicos)
4. [Subfase 7A — Dependencias e Compilacao](#4-subfase-7a--dependencias-e-compilacao)
5. [Subfase 7B — ArduPilotPlugin no URDF](#5-subfase-7b--ardupilotplugin-no-urdf)
6. [Subfase 7C — Motor Mixer Lua](#6-subfase-7c--motor-mixer-lua)
7. [Subfase 7D — Comunicacao AP_DDS (micro-ros-agent)](#7-subfase-7d--comunicacao-ap_dds-micro-ros-agent)
8. [Subfase 7E — Validacao End-to-End](#8-subfase-7e--validacao-end-to-end)
9. [Tabela de Topicos ROS 2 Esperados Apos Fase 7](#9-tabela-de-topicos-ros-2-esperados-apos-fase-7)
10. [Atualizacoes Pendentes em Outros Documentos](#10-atualizacoes-pendentes-em-outros-documentos)

---

## 1. Objetivo Geral

Substituir a ponte provisoria pymavlink (`mavlink_bridge_node.py`) por uma integracao nativa entre o ArduPilot Rover SITL e o Gazebo Harmonic, usando:

- O **`ArduPilotPlugin`** (do repositorio `ardupilot_gazebo`) para conectar o firmware SITL diretamente ao simulador via socket JSON — permitindo que o ArduPilot leia sensores simulados e envie comandos PWM para os 6 thrusters.
- O **AP_DDS** (MicroXRCE-DDS nativo do ArduPilot) para expor topicos de telemetria diretamente na malha ROS 2 Jazzy com latencia ~2ms, eliminando o MAVROS e preparando a infraestrutura para a Fase 8 (IA em tempo real com PyTorch).

**Resultado esperado:** O QGroundControl envia uma missao de waypoints ao ArduPilot SITL, que controla autonomamente os 6 motores do migbot no Rio Madeira simulado, com todos os dados de telemetria visiveis como topicos ROS 2 nativos.

---

## 2. Mapa de Dependencias entre Subfases

```
7A (Dependencias)
 |
 +---> 7B (ArduPilotPlugin no URDF)
 |      |
 |      +---> 7C (Motor Mixer Lua)
 |             |
 +---> 7D (AP_DDS / micro-ros-agent)
        |
        +---> 7E (Validacao End-to-End)
```

- **7A** e obrigatoria antes de tudo — sem os binarios compilados, nada funciona.
- **7B** e **7D** podem ser desenvolvidas em paralelo apos 7A.
- **7C** depende de 7B (precisa do plugin respondendo a PWM para testar o mixer).
- **7E** depende de todas as anteriores.

---

## 3. Pre-requisitos Tecnicos

Antes de iniciar a Fase 7, confirme que o seguinte esta operacional:

| Item | Comando de Verificacao | Resultado Esperado |
|------|----------------------|-------------------|
| Gazebo Harmonic instalado | `gz sim --version` | >= 8.x (Harmonic) |
| ROS 2 Jazzy funcional | `ros2 doctor` | All checks passed |
| Workspace compila | `cd ros2_asv_ws && colcon build` | 0 erros |
| Barco flutua no rio | `ros2 launch asv_bringup sim.launch.py` | migbot flutuando em x=100, y=20, z~0 |
| Thrusters respondem | `ros2 topic pub /model/migbot/joint/Engine_helice_1/cmd_thrust std_msgs/msg/Float64 "{data: 5.0}"` | Barco se move |
| Sensores publicando | `ros2 topic hz /imu` | ~50 Hz |
| Bridge pymavlink operacional | `ros2 launch asv_mavlink mavlink_bridge.launch.py` | Recebe SERVO_OUTPUT_RAW |

**Arquivos criticos da Fase 6 que NAO devem ser alterados sem motivo:**
- `src/asv_gazebo/worlds/madeira_river_simple.sdf` — graded_buoyancy ja configurado
- `src/asv_description/urdf/migbot.urdf.xacro` — thrusters e hidrodinamica calibrados

---

## 4. Subfase 7A — Dependencias e Compilacao

### O que fazer

Instalar e compilar dois componentes externos:

1. **`ardupilot_gazebo`** — plugin que conecta o ArduPilot SITL ao Gazebo Harmonic via socket JSON (porta 9002/9003).
2. **ArduPilot Rover SITL** — compilado com suporte a **AP_DDS** (MicroXRCE-DDS Agent) para publicacao nativa de topicos ROS 2.

### Por que estas acoes sao necessarias

- O `ardupilot_gazebo` fornece o `ArduPilotPlugin` para gz-sim (Gazebo Harmonic). Este plugin:
  - Le dados de sensores (IMU, GPS, barometro) diretamente do Gazebo.
  - Recebe comandos PWM do SITL e os converte em forcas nos joints dos thrusters.
  - Usa um protocolo JSON sobre socket TCP (diferente do UDP binario do Gazebo Classic).
- Sem o AP_DDS compilado no firmware, o ArduPilot so se comunica via MAVLink (protocolo binario), exigindo um intermediario como MAVROS ou a bridge pymavlink atual. Com AP_DDS, os topicos aparecem nativamente no DDS/ROS 2.

### Acoes Detalhadas

#### 4.1 Instalar ardupilot_gazebo

```bash
# 1. Clonar o repositorio oficial
cd ~/
git clone https://github.com/ArduPilot/ardupilot_gazebo.git
cd ardupilot_gazebo

# 2. Checkout da branch compativel com Harmonic
git checkout main  # verificar compatibilidade com gz-harmonic

# 3. Compilar
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo
make -j$(nproc)

# 4. Configurar variaveis de ambiente (adicionar ao ~/.bashrc ou ~/.zshrc)
export GZ_SIM_SYSTEM_PLUGIN_PATH=~/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH
export GZ_SIM_RESOURCE_PATH=~/ardupilot_gazebo/models:~/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH
```

> **LEMBRETE PARA A IA:** Antes de compilar, verificar qual versao do `gz-sim` esta instalada (`gz sim --version`). O `ardupilot_gazebo` tem branches diferentes para Garden vs Harmonic. Se der erro de include `gz/sim/...`, provavelmente e incompatibilidade de versao.

#### 4.2 Compilar ArduPilot com AP_DDS

```bash
# 1. Clonar ArduPilot (se ainda nao tiver)
cd ~/
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot

# 2. Instalar dependencias do ArduPilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile

# 3. Instalar Micro-XRCE-DDS-Gen (gerador de codigo DDS)
# ATENCAO: Requer Java 11+
sudo apt install default-jdk
cd ~/
git clone --recurse-submodules https://github.com/eProsima/Micro-XRCE-DDS-Gen.git
cd Micro-XRCE-DDS-Gen
gradle build
export PATH=$PATH:~/Micro-XRCE-DDS-Gen/scripts

# 4. Compilar Rover SITL com DDS habilitado
cd ~/ardupilot
./waf configure --board sitl --enable-dds
./waf rover

# 5. Verificar que o binario foi gerado
ls -la build/sitl/bin/ardurover
```

> **LEMBRETE PARA A IA:** O `--enable-dds` e o flag critico. Sem ele, o firmware compila mas nao tera os topicos `/ap/*`. Se o `waf configure` falhar mencionando `microxrceddsgen`, o gerador DDS nao esta no PATH. Verificar com `which microxrceddsgen`.

#### 4.3 Instalar micro-ros-agent (lado ROS 2)

```bash
# Opcao A: Via pacote (se disponivel para Jazzy)
sudo apt install ros-jazzy-micro-ros-agent

# Opcao B: Compilar do fonte
cd ~/
git clone https://github.com/micro-ROS/micro-ROS-Agent.git
cd micro-ROS-Agent
colcon build
source install/setup.bash
```

#### 4.4 Teste isolado do plugin (sem o migbot)

Antes de integrar com o nosso URDF, validar que o `ardupilot_gazebo` funciona com o modelo de exemplo:

```bash
# Terminal 1: Gazebo com modelo de teste do ardupilot_gazebo
gz sim -v4 -r iris_runway.sdf  # modelo de drone do ardupilot_gazebo

# Terminal 2: ArduPilot SITL
cd ~/ardupilot
sim_vehicle.py -v Rover -f JSON --console --map
```

Se o Gazebo mostrar o modelo e o SITL conectar (heartbeat no console), o plugin esta funcional.

### Criterios de Aceite da Subfase 7A

- [  ] `ardupilot_gazebo` compila sem erros.
- [  ] `GZ_SIM_SYSTEM_PLUGIN_PATH` configurado e persistido.
- [  ] ArduPilot Rover compila com `--enable-dds` sem erros.
- [  ] `ardurover` binario existe em `build/sitl/bin/`.
- [  ] `microxrceddsgen` acessivel no PATH.
- [  ] `micro-ros-agent` instalado (pacote ou compilado).
- [  ] Teste isolado com `iris_runway.sdf` + `sim_vehicle.py -f JSON` funciona (heartbeat OK).

### Armadilhas Conhecidas

| Problema | Causa | Solucao |
|----------|-------|---------|
| `CMake Error: gz-sim not found` | Versao do Gazebo incompativel | Verificar branch do ardupilot_gazebo (main = Harmonic, geralmente) |
| `microxrceddsgen: command not found` | Gerador DDS nao no PATH | Exportar PATH para `~/Micro-XRCE-DDS-Gen/scripts` |
| `waf configure` falha com DDS | Java nao instalado ou versao < 11 | `java -version` → instalar `default-jdk` |
| SITL nao conecta ao Gazebo | Porta JSON errada ou plugin nao carregado | Verificar log do Gazebo (`-v4`) por erros de plugin load |
| Modelo de teste nao aparece | `GZ_SIM_RESOURCE_PATH` nao configurado | Exportar caminho para `~/ardupilot_gazebo/models` |

---

## 5. Subfase 7B — ArduPilotPlugin no URDF

### O que fazer

Adicionar o bloco `<plugin>` do `ArduPilotPlugin` (do `ardupilot_gazebo`) no arquivo `src/asv_description/urdf/migbot.urdf.xacro`, configurando 6 canais PWM→Forca que mapeiam as saidas SERVO do ArduPilot SITL para os 6 thrusters existentes.

### Por que esta acao e necessaria

Atualmente, os 6 thrusters do migbot sao controlados via topicos ROS 2:
```
/model/migbot/joint/Engine_helice_X/cmd_thrust  (std_msgs/Float64, em Newtons)
```

Esses topicos sao acessiveis via `ros_gz_bridge` e usados manualmente (teleop) ou pela ponte pymavlink. O `ArduPilotPlugin` substitui esse fluxo: ele **injeta forcas diretamente nos joints** usando a API interna do Gazebo, sem passar pelo ROS. O ArduPilot SITL envia valores PWM (1000-2000), e o plugin os converte em forcas (Newtons) usando uma funcao linear configuravel.

### Estado Atual do URDF (Referencia)

Cada thruster esta configurado assim no `migbot.urdf.xacro` (linhas 276-323):

```xml
<plugin filename="gz-sim-thruster-system" name="gz::sim::systems::Thruster">
  <namespace>migbot</namespace>
  <joint_name>Engine_helice_X</joint_name>
  <thrust_coefficient>0.004422</thrust_coefficient>
  <fluid_density>997.8</fluid_density>
  <propeller_diameter>0.08</propeller_diameter>
  <use_angvel_cmd>false</use_angvel_cmd>
</plugin>
```

**Posicoes das 6 helices (extraidas dos joints do URDF):**

| Motor | Joint | X (m) | Y (m) | Z (m) | Posicao Aproximada |
|-------|-------|--------|--------|--------|-------------------|
| 1 | Engine_helice_1 | +1.010 | -0.554 | 0.660 | Proa Estibordo (frente direita) |
| 2 | Engine_helice_2 | -0.345 | +0.746 | 0.660 | Meia-Nau Bombordo (meio esquerda) |
| 3 | Engine_helice_3 | +1.010 | +0.746 | 0.660 | Proa Bombordo (frente esquerda) |
| 4 | Engine_helice_4 | -0.345 | -0.554 | 0.660 | Meia-Nau Estibordo (meio direita) |
| 5 | Engine_helice_5 | -0.717 | +0.746 | 0.660 | Popa Bombordo (tras esquerda) |
| 6 | Engine_helice_6 | -0.717 | -0.554 | 0.660 | Popa Estibordo (tras direita) |

### Acoes Detalhadas

#### 5.1 Adicionar o ArduPilotPlugin ao URDF

Adicionar o seguinte bloco `<gazebo>` ao final do `migbot.urdf.xacro`, **dentro** do tag `<robot>`, apos os plugins existentes:

```xml
<!-- ====================================================== -->
<!-- ArduPilot SITL Plugin (Fase 7B)                        -->
<!-- Conecta o firmware SITL ao Gazebo via socket JSON.      -->
<!-- Cada <channel> mapeia um SERVO_OUTPUT do ArduPilot      -->
<!-- para uma junta de thruster no Gazebo.                   -->
<!-- ====================================================== -->
<gazebo>
  <plugin filename="ArduPilotPlugin" name="ArduPilotPlugin">
    <!-- Conexao JSON com o SITL -->
    <fdm_addr>127.0.0.1</fdm_addr>
    <fdm_port_in>9002</fdm_port_in>
    <listen_addr>127.0.0.1</listen_addr>
    <fdm_port_out>9003</fdm_port_out>

    <!-- Lock-step: sincronizar tempo Gazebo ↔ SITL -->
    <modelXYZToAirplaneXForwardZDown>0 0 0 3.14159 0 0</modelXYZToAirplaneXForwardZDown>
    <gazeboXYZToNED>0 0 0 3.14159 0 -1.5708</gazeboXYZToNED>

    <!-- Canal 1 → Engine_helice_1 (Proa Estibordo) -->
    <channel>
      <input_index>0</input_index>
      <servo_min>1000</servo_min>
      <servo_max>2000</servo_max>
      <joint_name>Engine_helice_1</joint_name>
      <use_force_cmd>true</use_force_cmd>
      <multiplier>50.0</multiplier> <!-- CALIBRAR: N por unidade normalizada -->
    </channel>

    <!-- Canal 2 → Engine_helice_2 (Meia-Nau Bombordo) -->
    <channel>
      <input_index>1</input_index>
      <servo_min>1000</servo_min>
      <servo_max>2000</servo_max>
      <joint_name>Engine_helice_2</joint_name>
      <use_force_cmd>true</use_force_cmd>
      <multiplier>50.0</multiplier>
    </channel>

    <!-- Canal 3 → Engine_helice_3 (Proa Bombordo) -->
    <channel>
      <input_index>2</input_index>
      <servo_min>1000</servo_min>
      <servo_max>2000</servo_max>
      <joint_name>Engine_helice_3</joint_name>
      <use_force_cmd>true</use_force_cmd>
      <multiplier>50.0</multiplier>
    </channel>

    <!-- Canal 4 → Engine_helice_4 (Meia-Nau Estibordo) -->
    <channel>
      <input_index>3</input_index>
      <servo_min>1000</servo_min>
      <servo_max>2000</servo_max>
      <joint_name>Engine_helice_4</joint_name>
      <use_force_cmd>true</use_force_cmd>
      <multiplier>50.0</multiplier>
    </channel>

    <!-- Canal 5 → Engine_helice_5 (Popa Bombordo) -->
    <channel>
      <input_index>4</input_index>
      <servo_min>1000</servo_min>
      <servo_max>2000</servo_max>
      <joint_name>Engine_helice_5</joint_name>
      <use_force_cmd>true</use_force_cmd>
      <multiplier>50.0</multiplier>
    </channel>

    <!-- Canal 6 → Engine_helice_6 (Popa Estibordo) -->
    <channel>
      <input_index>5</input_index>
      <servo_min>1000</servo_min>
      <servo_max>2000</servo_max>
      <joint_name>Engine_helice_6</joint_name>
      <use_force_cmd>true</use_force_cmd>
      <multiplier>50.0</multiplier>
    </channel>
  </plugin>
</gazebo>
```

> **LEMBRETE PARA A IA:**
> - O `<multiplier>` de 50.0 e um valor inicial estimado. A calibracao real deve ser feita comparando o comportamento com os thrusters manuais (que aceitam Newtons diretamente). O valor correto depende da forca maxima desejada por motor.
> - O `<input_index>` corresponde ao SERVO_OUTPUT do ArduPilot (0-indexed: index 0 = SERVO1, index 1 = SERVO2, etc).
> - Os tags `<modelXYZToAirplaneXForwardZDown>` e `<gazeboXYZToNED>` convertem entre o frame do Gazebo (ENU, X-forward) e o frame do ArduPilot (NED, X-forward). Os valores acima sao padrao para veiculos de superficie. Se o barco andar ao contrario ou virar, esses valores estao errados.
> - **NAO remover** os plugins `gz-sim-thruster-system` existentes durante a Subfase 7B. Eles ainda sao necessarios para que o Gazebo aplique as forcas nos joints. O ArduPilotPlugin envia comandos; os Thruster plugins os executam.

#### 5.2 Decisao Arquitetural: Thruster plugins vs force_cmd direto

Existem duas abordagens para aplicar forca nos motores:

**Opcao A (Recomendada para comecar):** Manter os `gz-sim-thruster-system` existentes. O ArduPilotPlugin envia valores normalizados que sao traduzidos em forca pelos Thruster plugins. Neste caso, `<use_force_cmd>true</use_force_cmd>` faz o plugin enviar forca diretamente para o joint.

**Opcao B (Avancada):** Remover os Thruster plugins e deixar o ArduPilotPlugin aplicar forca diretamente nos joints via a API `gz::sim::Joint::SetForce()`. Mais simples, mas perde a simulacao visual de rotacao das helices.

> **LEMBRETE PARA A IA:** Comecar com a Opcao A. Somente migrar para Opcao B se houver conflitos entre o ArduPilotPlugin e os Thruster plugins (ex: forcas duplicadas). Se isso acontecer, o barco vai se comportar como se tivesse o dobro da potencia.

#### 5.3 Teste da Subfase 7B

```bash
# Terminal 1: Gazebo com migbot
ros2 launch asv_bringup sim.launch.py

# Terminal 2: ArduPilot SITL (modo JSON para Gazebo)
cd ~/ardupilot
sim_vehicle.py -v Rover -f JSON --console --map

# Observar no console do SITL:
# - "EKF3 IMU0 is using GPS" → sensores do Gazebo estao sendo lidos
# - "GPS: detected" → plugin transmitindo GPS
# - Heartbeat estavel
```

### Criterios de Aceite da Subfase 7B

- [  ] Plugin `ArduPilotPlugin` carregado sem erros no log do Gazebo (`gz sim -v4`).
- [  ] ArduPilot SITL conecta ao Gazebo (heartbeat estavel no console).
- [  ] SITL recebe dados de IMU, GPS e barometro do Gazebo (verificar com `status` no MAVProxy).
- [  ] Ao armar o Rover no SITL e aplicar throttle manual, o barco se move no Gazebo.
- [  ] Barco nao apresenta forca duplicada (comparar velocidade com o controle manual via `/cmd_thrust`).

### Armadilhas Conhecidas

| Problema | Causa | Solucao |
|----------|-------|---------|
| `ArduPilotPlugin: Failed to connect` | Porta JSON errada ou SITL nao iniciado com `-f JSON` | Usar `sim_vehicle.py -v Rover -f JSON` (flag `-f JSON` e obrigatoria) |
| Barco anda ao contrario | Frames ENU/NED invertidos | Ajustar `<modelXYZToAirplaneXForwardZDown>` e `<gazeboXYZToNED>` |
| Forca duplicada (barco muito rapido) | ArduPilotPlugin + Thruster plugin ambos aplicando forca | Reduzir `<multiplier>` ou remover Thruster plugins (Opcao B) |
| EKF diverge / "Bad AHRS" | Sensores nao chegando ao SITL ou com ruido excessivo | Verificar se os sensores IMU/GPS/Mag estao configurados no URDF |
| Barco afunda ao armar | Forca dos thrusters empurrando para baixo | Verificar eixo dos joints (deve ser `xyz="0 1 0"` para empuxo horizontal) |

---

## 6. Subfase 7C — Motor Mixer Lua

### O que fazer

Criar um script Lua que roda dentro do ArduPilot para distribuir os comandos de aceleracao (throttle) e direcao (steering) entre os 6 motores assimetricos do migbot, usando `FRAME_CLASS=15` (Scripting Matrix).

### Por que esta acao e necessaria

O ArduPilot Rover nativamente suporta configuracoes de ate 4 motores em layouts pre-definidos (skid-steer, ackermann, etc.). O migbot tem **6 helices em posicoes assimetricas** que nao correspondem a nenhum layout padrao. Sem o mixer customizado:
- O ArduPilot nao sabera como distribuir throttle/yaw entre os 6 canais SERVO.
- Os motores receberao todos o mesmo PWM ou ficarao em neutro.

**No ROS 1**, essa funcao era desempenhada pelo node `migbot_allocation.cpp` (`migbot_allocation` package), que convertia um `geometry_msgs/Wrench` em 6 comandos de esforco. **No ROS 2 com AP_DDS**, a alocacao ocorre dentro do proprio ArduPilot via Lua, o que e mais eficiente e elimina latencia de comunicacao.

### Geometria dos Motores (Base para a Matriz de Mistura)

Usando as posicoes dos joints do `migbot.urdf.xacro` relativas ao centro de massa (`CoM` em x=0.387, y=0.095):

| Motor | Joint | dx (relativo CoM) | dy (relativo CoM) | Posicao |
|-------|-------|------|------|---------|
| 1 | Engine_helice_1 | +0.623 | -0.649 | Proa Estibordo |
| 2 | Engine_helice_2 | -0.732 | +0.651 | Meia-Nau Bombordo |
| 3 | Engine_helice_3 | +0.623 | +0.651 | Proa Bombordo |
| 4 | Engine_helice_4 | -0.732 | -0.649 | Meia-Nau Estibordo |
| 5 | Engine_helice_5 | -1.104 | +0.651 | Popa Bombordo |
| 6 | Engine_helice_6 | -1.104 | -0.649 | Popa Estibordo |

> Nota: dx = posicao_joint_x - CoM_x (0.387), dy = posicao_joint_y - CoM_y (0.095). Valores positivos de dy = bombordo (esquerda), negativos = estibordo (direita).

### Acoes Detalhadas

#### 6.1 Configurar Parametros do ArduPilot

No MAVProxy ou QGC, setar os seguintes parametros:

```
# Tipo de frame: Scripting Matrix (permite mixer Lua customizado)
FRAME_CLASS 15

# Habilitar scripting Lua
SCR_ENABLE 1

# Funcao dos 6 canais SERVO (33-38 = motor 1-6 para scripting matrix)
SERVO1_FUNCTION 33
SERVO2_FUNCTION 34
SERVO3_FUNCTION 35
SERVO4_FUNCTION 36
SERVO5_FUNCTION 37
SERVO6_FUNCTION 38

# Limites PWM (devem corresponder ao ArduPilotPlugin)
SERVO1_MIN 1000
SERVO1_MAX 2000
SERVO2_MIN 1000
SERVO2_MAX 2000
SERVO3_MIN 1000
SERVO3_MAX 2000
SERVO4_MIN 1000
SERVO4_MAX 2000
SERVO5_MIN 1000
SERVO5_MAX 2000
SERVO6_MIN 1000
SERVO6_MAX 2000
```

#### 6.2 Script Lua — migbot_motor_mixer.lua

Este script deve ser colocado em `~/ardupilot/Rover/scripts/` (ou transferido para `/APM/scripts/` no SITL):

```lua
-- migbot_motor_mixer.lua
-- Mixer de motores customizado para o migbot (6 helices assimetricas)
-- Usa FRAME_CLASS=15 (Scripting Matrix)
--
-- Convencao:
--   throttle = avanco longitudinal (+1 = frente, -1 = re)
--   steering = rotacao yaw (+1 = girar direita, -1 = girar esquerda)
--
-- A matriz de mistura e baseada nas posicoes geometricas dos motores
-- relativas ao centro de massa do migbot.

local SERVO_FUNCTION_MOTOR1 = 33
local SERVO_FUNCTION_MOTOR2 = 34
local SERVO_FUNCTION_MOTOR3 = 35
local SERVO_FUNCTION_MOTOR4 = 36
local SERVO_FUNCTION_MOTOR5 = 37
local SERVO_FUNCTION_MOTOR6 = 38

-- Posicoes dy dos motores (positivo = bombordo/esquerda)
-- Motores a bombordo contribuem positivamente para yaw (girar direita)
-- Motores a estibordo contribuem negativamente para yaw (girar direita)
local DY = {
    -0.649,  -- Motor 1: Estibordo
     0.651,  -- Motor 2: Bombordo
     0.651,  -- Motor 3: Bombordo
    -0.649,  -- Motor 4: Estibordo
     0.651,  -- Motor 5: Bombordo
    -0.649,  -- Motor 6: Estibordo
}

-- Pesos de throttle por motor (todos iguais para avanco reto)
local THROTTLE_WEIGHT = { 1.0, 1.0, 1.0, 1.0, 1.0, 1.0 }

-- Pesos de steering por motor (baseados na distancia lateral dy)
-- Positivo = motor contribui para virar a estibordo (direita)
-- A normalizacao e feita pelo maior valor absoluto de dy
local max_dy = 0.651
local STEERING_WEIGHT = {}
for i = 1, 6 do
    STEERING_WEIGHT[i] = -DY[i] / max_dy
end

function update()
    -- Obter inputs do ArduPilot (normalizados -1 a +1)
    local throttle = vehicle:get_throttle() or 0.0
    local steering = vehicle:get_steering() or 0.0

    -- Calcular saida de cada motor
    for i = 1, 6 do
        local output = throttle * THROTTLE_WEIGHT[i] + steering * STEERING_WEIGHT[i]
        -- Limitar entre -1 e +1
        output = math.max(-1.0, math.min(1.0, output))
        -- Converter para PWM (1000-2000)
        local pwm = 1500 + (output * 500)
        SRV_Channels:set_output_pwm(SERVO_FUNCTION_MOTOR1 + (i - 1), math.floor(pwm))
    end

    return update, 20  -- Executar a cada 20ms (50Hz)
end

return update, 1000  -- Delay inicial de 1s para boot
```

> **LEMBRETE PARA A IA:**
> - Este script e um ponto de partida. A API exata do Lua no ArduPilot pode variar entre versoes. Consultar a documentacao oficial do ArduPilot Lua Scripting antes de implementar.
> - `vehicle:get_throttle()` e `vehicle:get_steering()` sao funcoes da API do Rover. Para outros tipos de veiculo, os nomes podem diferir.
> - A matriz de mistura assume que todas as helices empurram na mesma direcao (eixo Y do joint = forward). Se alguma helice estiver invertida fisicamente no URDF, o peso de throttle deve ser negativo para esse motor.
> - O script Lua do ROS 1 era chamado `aeroboat-controlallocation.lua` e usava uma logica similar. Pode servir de referencia adicional.

#### 6.3 Copiar o script para o SITL

```bash
# Para SITL local:
mkdir -p ~/ardupilot/Rover/scripts/
cp migbot_motor_mixer.lua ~/ardupilot/Rover/scripts/

# Ou via MAVProxy (se conectado a um SITL ou hardware):
# ftp put migbot_motor_mixer.lua /APM/scripts/
```

#### 6.4 Teste da Subfase 7C

```bash
# Terminal 1: Gazebo
ros2 launch asv_bringup sim.launch.py

# Terminal 2: SITL com scripts Lua
cd ~/ardupilot
sim_vehicle.py -v Rover -f JSON --console --map \
    --add-param-file=Tools/autotest/default_params/rover.parm

# No console do MAVProxy:
# 1. Verificar se o script carregou:
module load scripting
script list
# Deve mostrar "migbot_motor_mixer.lua: running"

# 2. Armar e testar:
arm throttle force
rc 3 1600   # Throttle para frente
# Barco deve avancar reto

rc 1 1300   # Steering para esquerda
# Barco deve girar para a esquerda

rc 1 1500   # Centralizar
rc 3 1500   # Parar
disarm
```

### Criterios de Aceite da Subfase 7C

- [  ] Script Lua carregado sem erros (`script list` mostra status "running").
- [  ] Com throttle puro (+frente), todos os 6 motores giram na mesma direcao → barco avanca reto.
- [  ] Com steering puro (esquerda), motores de bombordo e estibordo giram em direcoes opostas → barco gira.
- [  ] Combinacao throttle+steering produz curva suave (nao trava nem capota).
- [  ] PWM dos 6 canais SERVO visivel no MAVProxy (`status servo*`) e coerente com os comandos.

### Armadilhas Conhecidas

| Problema | Causa | Solucao |
|----------|-------|---------|
| `Scripting: script not found` | Arquivo nao no diretorio correto do SITL | Verificar que esta em `Rover/scripts/` ou transferir via `ftp put` |
| `Scripting: error in script` | Erro de sintaxe Lua ou API invalida | Verificar console do MAVProxy; testar script com `lua -e` localmente |
| Barco gira em vez de avancar | Pesos de steering invertidos | Inverter sinais no vetor `DY` |
| Barco nao responde | SERVO_FUNCTION nao configurado | Verificar que `SERVO1_FUNCTION=33` ate `SERVO6_FUNCTION=38` |
| Motores saturando (todos em 2000) | Throttle + steering somam > 1.0 | O clamp `math.max/min` deve cuidar disso; se nao, reduzir pesos |

---

## 7. Subfase 7D — Comunicacao AP_DDS (micro-ros-agent)

### O que fazer

Configurar e inicializar o `micro-ros-agent` para que o ArduPilot SITL publique topicos de telemetria diretamente na malha DDS do ROS 2 Jazzy, e deprecar/substituir a ponte pymavlink atual (`mavlink_bridge_node.py`).

### Por que esta acao e necessaria

A bridge atual tem limitacoes severas:

| Aspecto | pymavlink bridge (atual) | AP_DDS (objetivo) |
|---------|-------------------------|-------------------|
| Latencia | ~50ms (UDP + polling 20Hz) | ~2ms (DDS nativo) |
| Topicos disponiveis | Apenas SERVO_OUTPUT_RAW → Twist | Pose, velocidade, GPS, estado, RC, modos |
| Direcao | Unidirecional (ArduPilot → ROS) | Bidirecional (pode enviar comandos pelo DDS) |
| Dependencia | pymavlink (Python) | Nativa no firmware (C++) |
| Requisito para IA | Insuficiente (latencia alta) | Essencial (Fase 8 PyTorch precisa de <5ms) |

### Acoes Detalhadas

#### 7.1 Habilitar AP_DDS no ArduPilot SITL

No MAVProxy ou QGC, configurar:

```
# Habilitar o modulo DDS
DDS_ENABLE 1

# Configurar o endereco do micro-ros-agent
DDS_UDP_PORT 2019
```

Reiniciar o SITL apos alterar `DDS_ENABLE`.

#### 7.2 Iniciar o micro-ros-agent

```bash
# Em um terminal dedicado, ANTES de iniciar o SITL:
micro-ros-agent udp4 -p 2019

# Ou, se compilado do fonte:
ros2 run micro_ros_agent micro_ros_agent udp4 -p 2019
```

Quando o SITL iniciar e conectar, o agent deve imprimir mensagens de sessao criada.

#### 7.3 Verificar topicos publicados

```bash
# Listar topicos do ArduPilot no ROS 2
ros2 topic list | grep /ap

# Topicos esperados (podem variar conforme versao do ArduPilot):
# /ap/battery/battery0
# /ap/clock
# /ap/geopose/filtered
# /ap/gps_global_origin/filtered
# /ap/navsat/navsat0
# /ap/pose/filtered
# /ap/time
# /ap/twist/filtered
# /ap/velocity/filtered

# Verificar dados:
ros2 topic echo /ap/pose/filtered
ros2 topic hz /ap/pose/filtered
```

#### 7.4 Atualizar o sim.launch.py

O launch file precisara ser atualizado para:

1. **Remover** as bridges dos sensores do Gazebo que agora vem pelo AP_DDS (GPS, IMU podem vir pelo ArduPilot).
2. **Manter** as bridges dos thrusters (controle ainda precisa do Gazebo).
3. **Adicionar** o node do micro-ros-agent (opcional, pode rodar separado).
4. **Deprecar** a referencia ao `asv_mavlink` package.

> **LEMBRETE PARA A IA:**
> - NAO remover TODAS as bridges de sensores imediatamente. Os sensores do Gazebo (via ros_gz_bridge) e os do ArduPilot (via AP_DDS) publicam dados com frames e taxas diferentes. Na Subfase 7D, manter ambos e comparar. Remover as bridges do Gazebo somente quando confirmar que os topicos `/ap/*` sao suficientes.
> - O pacote `asv_mavlink` nao deve ser deletado — apenas marcado como deprecado. Ele pode ser util para debug ou como fallback.
> - O micro-ros-agent pode ser lancado como um Node no launch file OU como processo externo. Para a Fase 7, lancar externamente e mais facil de debugar. Integrar no launch file somente na Fase 7E.

#### 7.5 Teste da Subfase 7D

```bash
# Terminal 1: micro-ros-agent
micro-ros-agent udp4 -p 2019

# Terminal 2: Gazebo
ros2 launch asv_bringup sim.launch.py

# Terminal 3: SITL com DDS
cd ~/ardupilot
sim_vehicle.py -v Rover -f JSON --console --map

# Terminal 4: Verificar topicos
ros2 topic list | grep /ap
ros2 topic echo /ap/pose/filtered   # Deve mostrar pose do barco
ros2 topic hz /ap/twist/filtered    # Deve mostrar ~50Hz
```

### Criterios de Aceite da Subfase 7D

- [  ] `micro-ros-agent` inicia sem erros e reporta sessao criada quando o SITL conecta.
- [  ] `ros2 topic list` mostra topicos `/ap/*` (minimo: pose, twist, navsat).
- [  ] `ros2 topic hz /ap/pose/filtered` reporta taxa >= 10Hz.
- [  ] Dados de `/ap/pose/filtered` correspondem a posicao real do barco no Gazebo.
- [  ] Bridge pymavlink pode ser desligada sem perda de funcionalidade (exceto teleop manual via `/cmd_vel`).

### Armadilhas Conhecidas

| Problema | Causa | Solucao |
|----------|-------|---------|
| Nenhum topico `/ap/*` aparece | `DDS_ENABLE` nao configurado ou SITL sem `--enable-dds` | Recompilar SITL com `--enable-dds` e setar `DDS_ENABLE 1` |
| Agent imprime `error creating session` | Incompatibilidade de versao DDS | Verificar que o micro-ros-agent e compativel com a versao do eProsima no ArduPilot |
| Topicos aparecem mas sem dados | Porta UDP errada | Verificar que `DDS_UDP_PORT` no ArduPilot = porta do agent |
| Pose mostra (0,0,0) | EKF nao inicializado | Aguardar GPS lock no SITL (pode levar 30-60s) |
| Conflito de topicos GPS | Dois GPS no mesmo namespace (Gazebo bridge + AP_DDS) | Usar remappings ou desabilitar uma das fontes |

---

## 8. Subfase 7E — Validacao End-to-End

### O que fazer

Executar uma missao autonoma completa com waypoints usando QGroundControl, validando toda a cadeia de controle e telemetria.

### Por que esta acao e necessaria

As subfases 7A-7D foram testadas isoladamente. A Subfase 7E valida a integracao de todos os componentes simultaneamente, garantindo que nao ha regressoes e que o sistema esta pronto para a Fase 8.

### Sequencia Operacional Completa

```bash
# === PREPARACAO ===

# Terminal 1: micro-ros-agent (iniciar PRIMEIRO)
micro-ros-agent udp4 -p 2019

# Terminal 2: Gazebo + migbot
ros2 launch asv_bringup sim.launch.py

# Terminal 3: ArduPilot SITL
cd ~/ardupilot
sim_vehicle.py -v Rover -f JSON --console --map \
    --out=udp:127.0.0.1:14550

# Terminal 4: QGroundControl
~/QGroundControl-x86_64.AppImage

# === MISSAO ===

# No QGC:
# 1. Verificar conexao com o SITL (icone verde no topo)
# 2. Criar uma missao simples com 3-4 waypoints no rio
#    (coordenadas proximas a lat=-8.798638, lon=-63.952087)
# 3. Upload da missao
# 4. Armar o veiculo
# 5. Mudar para modo AUTO
# 6. Observar o barco seguindo os waypoints no Gazebo

# === MONITORAMENTO ===

# Terminal 5: Monitorar telemetria ROS 2
ros2 topic echo /ap/pose/filtered     # Posicao em tempo real
ros2 topic echo /ap/twist/filtered    # Velocidade
ros2 topic echo /ap/navsat/navsat0    # GPS
```

### Metricas de Validacao

| Metrica | Valor Esperado | Como Medir |
|---------|---------------|-----------|
| Latencia AP_DDS | < 5ms | `ros2 topic delay /ap/pose/filtered` |
| Taxa de pose | >= 10 Hz | `ros2 topic hz /ap/pose/filtered` |
| Taxa de IMU Gazebo | ~50 Hz | `ros2 topic hz /imu` |
| Desvio de waypoint | < 5m do ponto planejado | Comparar no QGC |
| Barco completa missao | Retorna a HOME ou para no ultimo WP | Observar no QGC |
| Consumo CPU SITL | < 100% de 1 core | `top` ou `htop` |
| Estabilidade do EKF | Sem warnings "EKF variance" | Console do MAVProxy |

### Criterios de Aceite da Subfase 7E

- [  ] Missao com 3+ waypoints carregada e iniciada no QGC.
- [  ] Barco segue os waypoints autonomamente no Gazebo (sem intervencao manual).
- [  ] Topicos `/ap/*` publicando continuamente durante toda a missao.
- [  ] Sem crashes, NaN, ou comportamentos fisicos anomalos.
- [  ] Barco retorna ao modo HOLD ou completa a missao sem divergencia do EKF.
- [  ] Toda a sequencia operacional documentada e reproduzivel.

### Teste de Regressao

Alem da missao autonoma, re-executar os seguintes testes das fases anteriores:

| Teste | Comando | Resultado Esperado |
|-------|---------|-------------------|
| Teleop manual via teclado | `ros2 run teleop_twist_keyboard teleop_twist_keyboard` + bridge `/cmd_vel` | Barco responde (validar que controle manual ainda funciona) |
| Sensores Gazebo | `ros2 topic hz /imu /navsat /magnetometer` | Taxas estaveis (50Hz, 5Hz, 20Hz) |
| Flutuabilidade | Spawnar sem thrusters ativos | Barco flutua a ~11cm de calado, estavel |

---

## 9. Tabela de Topicos ROS 2 Esperados Apos Fase 7

### Topicos do Gazebo (via ros_gz_bridge, mantidos)

| Topico ROS 2 | Tipo | Direcao | Taxa | Origem |
|--------------|------|---------|------|--------|
| `/model/migbot/joint/Engine_helice_X/cmd_thrust` | `std_msgs/Float64` | ROS→GZ | On demand | Bridge (controle manual) |
| `/model/migbot/pose` | `geometry_msgs/PoseArray` | GZ→ROS | ~50 Hz | Bridge |
| `/imu` | `sensor_msgs/Imu` | GZ→ROS | 50 Hz | Bridge |
| `/navsat` | `sensor_msgs/NavSatFix` | GZ→ROS | 5 Hz | Bridge |
| `/magnetometer` | `sensor_msgs/MagneticField` | GZ→ROS | 20 Hz | Bridge |

### Topicos do ArduPilot (via AP_DDS, novos)

| Topico ROS 2 | Tipo | Direcao | Taxa | Origem |
|--------------|------|---------|------|--------|
| `/ap/pose/filtered` | `geometry_msgs/PoseStamped` | AP→ROS | ~50 Hz | AP_DDS |
| `/ap/twist/filtered` | `geometry_msgs/TwistStamped` | AP→ROS | ~50 Hz | AP_DDS |
| `/ap/navsat/navsat0` | `sensor_msgs/NavSatFix` | AP→ROS | ~5 Hz | AP_DDS |
| `/ap/battery/battery0` | `sensor_msgs/BatteryState` | AP→ROS | ~1 Hz | AP_DDS |
| `/ap/clock` | `rosgraph_msgs/Clock` | AP→ROS | ~50 Hz | AP_DDS |
| `/ap/geopose/filtered` | `geographic_msgs/GeoPoseStamped` | AP→ROS | ~50 Hz | AP_DDS |
| `/ap/cmd_vel` | `geometry_msgs/TwistStamped` | ROS→AP | On demand | AP_DDS (Fase 8) |

> Nota: A lista exata de topicos depende da versao do ArduPilot e da configuracao do DDS. Verificar com `ros2 topic list | grep /ap` apos iniciar.

---

## 10. Atualizacoes Pendentes em Outros Documentos

Apos a conclusao da Fase 7, os seguintes documentos devem ser atualizados:

| Documento | O que atualizar |
|-----------|----------------|
| `docs/GUIA_FASES.md` | Adicionar Fase 7 (AP_DDS) e Fase 8 (Sensores + IA) |
| `src/PLAN.md` | Marcar Fase 7 como concluida, detalhar Fase 8 |
| `src/relatorio.md` | Atualizar status para refletir Fase 7 concluida |
| `docs/branches_mapping.md` | Adicionar branch da Fase 7 |
| `docs/ARCHITECTURE.md` | Atualizar diagrama para incluir fluxo AP_DDS (sem MAVROS) |
| `src/asv_bringup/launch/sim.launch.py` | Comentarios indicando bridges deprecadas vs ativas |

---

## Resumo de Lembretes para Implementacao (IA)

1. **Subfase 7A:** Verificar versao do Gazebo antes de compilar `ardupilot_gazebo`. Flag `--enable-dds` e obrigatoria no `waf configure`. Testar com modelo de exemplo antes de integrar.

2. **Subfase 7B:** NAO remover os plugins `gz-sim-thruster-system` existentes. Comecar com `<multiplier>50.0</multiplier>` e calibrar. Se houver forca duplicada, reduzir multiplier pela metade.

3. **Subfase 7C:** A API Lua do ArduPilot muda entre versoes — verificar documentacao oficial. O script e baseado na geometria real das helices do URDF. Se posicoes mudarem, recalcular a matriz.

4. **Subfase 7D:** Manter bridges do Gazebo em paralelo com AP_DDS durante os testes. NAO deletar `asv_mavlink`, apenas deprecar. micro-ros-agent deve ser iniciado ANTES do SITL.

5. **Subfase 7E:** Re-executar testes de regressao das fases anteriores. Documentar a sequencia operacional exata com todos os terminais.
