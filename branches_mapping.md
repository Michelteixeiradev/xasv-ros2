# Mapeamento de Branches - xasv-ros2

Este documento mapeia as branches atuais do repositório `xasv-ros2`, explicando o propósito de cada uma e detalhando os principais arquivos adicionados ou modificados. Ele serve como referência para entender a estrutura e a divisão de trabalho da "Fase 1" do projeto.

## 1. `main`
- **Propósito:** Branch principal do repositório, contendo a estrutura base e fundamental do projeto `xasv-ros2`. Todo o código estável é integrado aqui.

## 2. `chore/setup-devcontainer`
- **Propósito:** Responsável pela configuração do ambiente de desenvolvimento remoto utilizando DevContainers, facilitando a padronização das ferramentas e dependências do projeto.
- **Principais Arquivos Relacionados:** 
  - `../.devcontainer/devcontainer.json`

## 3. `feature/fase1-asv-bringup-launch`
- **Propósito:** Focada na orquestração da inicialização da simulação. Contém os arquivos responsáveis por iniciar o Gazebo, publicar o estado do robô (`robot_state_publisher`) e fazer o "spawn" do ASV (Autonomous Surface Vehicle). Também inclui o plugin de controle de velocidade e a ponte (bridge) ROS-Gazebo.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_bringup/launch/sim.launch.py` (Script de inicialização)
  - `src/asv_bringup/package.xml` (Atualização de dependências)
  - `src/asv_description/urdf/dummy_boat.urdf` (Adição e ajustes nos plugins em URDF)

## 4. `feature/fase1-asv-control`
- **Propósito:** Implementa o pacote de controle e teleoperação do barco. Adiciona os scripts responsáveis por receber os comandos e atuar como nó de teleoperação para o barco.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_control/teleop_node.py` (Nó Python de teleoperação)
  - `src/asv_control/setup.py`, `src/asv_control/setup.cfg`, `src/asv_control/__init__.py` (Arquivos de setup do pacote de controle)
  - Modificações em dependências (ex.: `teleop_twist_keyboard`) no `src/asv_bringup/package.xml`

## 5. `feature/fase1-asv-gazebo`
- **Propósito:** Criação do ambiente de simulação no Gazebo (pacote `asv_gazebo`). Define os mundos onde a embarcação será simulada.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_gazebo/worlds/empty_ocean.sdf` (Mundo vazio e base de simulação no oceano)
  - `src/asv_gazebo/CMakeLists.txt` e `src/asv_gazebo/package.xml` (Configuração do pacote)

## 6. `feature/fase1-asv-mavlink`
- **Propósito:** Desenvolvimento da ponte de comunicação (MAVLink Bridge) funcional e integrada ao ROS 2. Prepara o ecossistema para integração futura com simuladores de controle de voo como ArduPilot e software base como QGroundControl.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_mavlink/scripts/mavlink_bridge_node.py` (Estrutura inicial do nó usando `pymavlink`)
  - `src/asv_mavlink/launch/mavlink_bridge.launch.py` (Arquivo para launch da ponte)
  - `src/asv_mavlink/CMakeLists.txt` e `src/asv_mavlink/package.xml`

## 7. `feature/fase1-asv-missions`
- **Propósito:** Adição do pacote `asv_missions` destinado a gerenciar o armazenamento e execução de missões. Cria a estrutura para carregar planos de voo e trajetórias do QGroundControl (`.plan`).
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_missions/plans/sample_mission.plan` (Arquivo de amostra de missão extraído do QGroundControl)
  - `src/asv_missions/CMakeLists.txt` e `src/asv_missions/package.xml`
