# Plano de Migração: ROS1 para ROS2

## Objetivo Geral
Criar uma base funcional em ROS2 (Jazzy) para o projeto xasv-sim, focando no fluxo principal de simulação sem depender de hardware físico no momento.

---

## FASE 1: Base Mínima e Estrutura Arquitetural (Implementada)

### Arquitetura de Pacotes Criada (`ros2_asv_ws/src/`)
- `asv_bringup`: Maestro da simulação.
- `asv_description`: Modelo URDF básico (`dummy_boat.urdf`).
- `asv_gazebo`: Cenário genérico em SDF (`empty_ocean.sdf`).
- `asv_control`: Infraestrutura Python e nó inicial (`teleop_node.py`).
- `asv_mavlink`: Estrutura para ponte de comunicação.
- `asv_missions`: Estrutura para rotas (`sample_mission.plan`).

### Critérios de Aceite da Fase 1 
- [x] O workspace compila sem erros (Ubuntu 24.04).
- [x] O simulador Gazebo abre através do `sim.launch.py`.
- [x] O robô genérico aparece no mundo virtual.

---

## FASE 2: Controle Manual (Implementada)

### Escopo Realizado
- [x] Adicionar plugin `VelocityControl` ao modelo URDF para escutar o tópico `cmd_vel`.
- [x] Configurar a ponte `ros_gz_bridge` no launch principal.
- [x] Implementar controle via teclado utilizando `teleop_twist_keyboard`.
- [x] Validar resposta de movimento do barco no Gazebo.

---

## FASE 3: Integração MAVLink e Autonomia Básica (Implementada)

### Escopo Realizado
- [x] Definição da arquitetura da ponte de comunicação (MAVROS vs. pymavlink).
- [x] Implementação do pacote `asv_mavlink` para tradução de comandos ROS -> ArduPilot.
- [x] Implementação da execução de rotas via `asv_missions`.
- [x] Validação em cenário SITL com ArduPilot e QGroundControl (QGC).

---

## FASE 4: Ambiente Customizado (Concluída)

### Escopo Realizado
- [x] Configurar um mundo realista no Gazebo Harmonic (`madeira_river_simple.sdf`).
- [x] Adicionar geometria do rio e assets visuais básicos.
- [x] Testar compatibilidade do mundo no Gazebo Harmonic e adaptar shaders/plugins.
- [x] Atualizar launch file para permitir seleção dinâmica de mundos.

---

## FASE 5: Robô Customizado "migbot" (Concluída)

### Escopo Realizado
- [x] Mover as meshes (geometria 3D e colisão) do ROS 1 para o novo pacote `asv_description`.
- [x] Limpar `migbot2.urdf.xacro` de todos os plugins incompatíveis do Gazebo Classic.
- [x] Injetar controle cinemático provisório `VelocityControl` e plugin de `Buoyancy` no mundo.
- [x] Ajustar coordenadas de spawn no Launch (`Y=25.0`) para garantir flutuabilidade funcional.
- [x] Validar que o barco autêntico flutua no Rio Madeira e responde aos comandos `/cmd_vel` via ROS 2.

---

## FASE 6: Integração Complexa (Sensores e Física) (Concluída)

### Escopo Realizado
- [x] **Fase 6A (Sensores):** Inclusão de IMU, GPS e Magnetômetro no URDF, com bridges ROS 2 configuradas para leitura das informações do Gazebo.
- [x] **Fase 6B (Dinâmica Real):** 
  - Remoção do `VelocityControl` (cinemático).
  - Substituição da flutuabilidade (`uniform_fluid_density` → `graded_buoyancy`) no mundo para corrigir o Princípio de Arquimedes e estabilizar o barco com ~11cm de calado.
  - Adição de 6 plugins `Thruster` individuais, controlados por força em Newtons (`/cmd_thrust`).
  - Adição do plugin `Hydrodynamics` com coeficientes SNAME para simulação realista de arrasto na água.

---

## FASE 7: Integração ArduPilot SITL Avançada via AP_DDS (Próximos Passos)

### Escopo Previsto
- **Subfase 7A (Dependências):** Instalar plugin `ardupilot_gazebo` e compilar o ArduPilot Rover SITL com suporte nativo ao **MicroXRCE DDS** (AP_DDS).
- **Subfase 7B (Plugin no URDF):** Configurar o `ArduPilotPlugin` no `migbot.urdf.xacro` para converter as saídas PWM do SITL em forças (Newtons) para os 6 thrusters.
- **Subfase 7C (Motor Mixer Lua):** Implementar um script Lua (Scripting Matrix, `FRAME_CLASS=15`) rodando no ArduPilot para distribuir comandos de aceleração e direção entre os 6 motores assimétricos.
- **Subfase 7D (Comunicação):** Inicializar o `micro-ros-agent` para expor os tópicos do ArduPilot nativamente no ROS 2 Jazzy (ex: `/ap/pose/filtered`), substituindo a necessidade do MAVROS (visando latência mínima de ~2ms para futura integração de IA).
- **Subfase 7E (Validação):** Conectar o QGroundControl ao SITL e executar missões autônomas (waypoints) no mundo `madeira_river_simple`.

---

## FASE 8: Sensores Adicionais e IA (Futuro)
- Adição de LiDAR (Livox), Sonar (Ping360) e Câmera D435.
- Execução de inferência de Política de IA (PyTorch) publicando diretamente em `/ap/cmd_vel`.