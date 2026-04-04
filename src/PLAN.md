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

### Critérios de Aceite da Fase 1 (Validação Pendente)
- [ ] O workspace compila sem erros (Pendente ambiente Linux/Docker).
- [ ] O simulador Gazebo abre através do `sim.launch.py`.
- [ ] O robô genérico (caixa azul) aparece flutuando no mundo virtual.
- [ ] O nó de controle consegue publicar no tópico `cmd_vel`.

---

## FASE 2: Controle por Operador (Próximos Passos)

### Escopo Previsto
- Adicionar suporte a joystick (pacote `joy`).
- Configurar conversão de comando (`teleop_twist_joy` ou conversor customizado).
- Fazer o robô genérico responder aos comandos e se mover no Gazebo.