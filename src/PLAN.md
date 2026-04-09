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

## FASE 4: Integração de Sensores e Expansão da Simulação (Próximos Passos)

### Escopo Previsto
- Adicionar sensores simulados ao modelo (LiDAR Livox, Sonar Ping360 e RealSense D435).
- Configurar pontes de dados (`ros_gz_bridge`) para publicação de tópicos de percepção.
- Validar a visualização dos dados dos sensores no RViz2.

---

## FASE 5: Migração da Política de Autonomia (Inteligência Artificial)

### Escopo Previsto
- Migrar o nó `huitl_policy_node` de ROS 1 para ROS 2 (Python).
- Implementar a carga e inferência do modelo PyTorch (`.pt`) dentro do ambiente ROS 2 Jazzy.
- Adaptar o sistema de saída: transitar do antigo `rc_override` para comandos de velocidade/atitude via MAVLink (`SET_POSITION_TARGET_LOCAL_NED` ou similar).
- Testar o ciclo fechado: Percepção -> Política (IA) -> Comando MAVLink -> Movimento no SITL.