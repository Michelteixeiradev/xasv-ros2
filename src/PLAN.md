# Plano de Migração: ROS1 para ROS2

## Objetivo Geral
Criar uma base funcional em ROS2 (Jazzy) para o projeto xasv-sim, focando no fluxo principal de simulação sem depender de hardware físico no momento.

---

## FASE 1: Base Mínima e Estrutura Arquitetural (Implementada)

### Arquitetura de Pacotes Criada (`ros2_asv_ws/src/`)
- `asv_bringup`: Contém o maestro da simulação.
- `asv_description`: Contém o modelo URDF básico (`dummy_boat.urdf`).
- `asv_gazebo`: Contém o cenário genérico em SDF (`empty_ocean.sdf`).
- `asv_control`: Contém a infraestrutura Python e o nó inicial (`teleop_node.py`).
- `asv_mavlink`: Contém a estrutura para ponte de comunicação futura.
- `asv_missions`: Contém estrutura para rotas (`sample_mission.plan`).

### Arquivos Base Desenvolvidos
- `sim.launch.py` (em `asv_bringup`): Orquestra o Gazebo, processa o URDF via `robot_state_publisher` e faz o spawn do barco na água.
- `mavlink_bridge.launch.py` (em `asv_mavlink`): Placeholder para a futura integração com ArduPilot.

### Critérios de Aceite da Fase 1 
- [x] O workspace compila sem erros (Pronto e mapeado via `package.xml` para Ubuntu 24.04).
- [x] O simulador Gazebo abre através do `sim.launch.py`.
- [x] O robô genérico (caixa azul) aparece flutuando no mundo virtual.

---

## FASE 2: Controle Manual (Implementada)

### Escopo Realizado
- [x] Adicionar plugin `VelocityControl` ao modelo URDF (`dummy_boat.urdf`) para escutar o tópico `cmd_vel`.
- [x] Configurar a ponte (`ros_gz_bridge`) no launch principal para conectar a rede ROS 2 ao ecossistema interno do Gazebo.
- [x] Implementar controle via teclado utilizando o pacote padrão `teleop_twist_keyboard` (substituindo a necessidade inicial de joystick físico para simplificar a validação).
- [x] Validar que o barco genérico responde aos comandos e se move no Gazebo.

---

## FASE 3: Integração MAVLink e Autonomia Básica (Próximos Passos)

### Escopo Previsto
- Definir arquitetura da ponte de comunicação (MAVROS vs. pymavlink).
- Fazer o pacote `asv_mavlink` traduzir comandos de navegação do ROS para a controladora (ArduPilot/PX4).
- Implementar a leitura e execução de rotas do pacote `asv_missions`.