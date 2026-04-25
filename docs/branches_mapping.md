# Mapeamento de Branches - xasv-ros2

Este documento mapeia as branches do repositório `xasv-ros2`, acompanhando a evolução do projeto e os merges realizados. Ele detalha o propósito de cada branch, os arquivos principais e o status atual, servindo como referência para a estrutura de desenvolvimento.

## 1. `main`
- **Status:** **Ativa** (Branch principal)
- **Propósito:** Branch principal do repositório, contendo a estrutura base e fundamental do projeto `xasv-ros2`. Todo o código estável é integrado aqui.

## 2. `feature/fase4-custom-environment` (Branch de Integração Atual)
- **Status:** **Ativa** (Integra os trabalhos das fases 1, 2, 3 e atual desenvolvimento da fase 4)
- **Propósito:** Atualmente serve como branch principal de integração do desenvolvimento. Foi criada para configurar o ambiente customizado da Fase 4 (cenário do Rio Madeira), mas também consolidou o trabalho e os merges de diversas branches das fases anteriores.
- **Principais Novidades e Arquivos:**
  - `src/asv_gazebo/worlds/madeira_river_simple.sdf` (Mundo do Rio Madeira para a simulação)
  - Modificações em `sim.launch.py` para carregar o mapa `madeira_river` e realizar roteamento dinâmico de tópicos.
  - Atualizações no `dummy_boat.urdf` para validação de movimento.
  - Implementação da ponte MAVLink Fase 3 e fluxo de controle manual.
  - Documentação atualizada (ex: inclusão do `GUIA_FASES.md`).
- **Merges Recebidos:** Incorporou as branches `fase1-asv-gazebo`, `fase1-asv-bringup-launch`, `fase1-asv-mavlink` e `fase1-asv-control`.

## 3. `chore/setup-devcontainer`
- **Status:** **Ativa**
- **Propósito:** Responsável pela configuração do ambiente de desenvolvimento remoto utilizando DevContainers, facilitando a padronização das ferramentas e dependências do projeto.
- **Principais Arquivos Relacionados:** 
  - `../.devcontainer/devcontainer.json`

## 4. `feature/fase1-asv-bringup-launch`
- **Status:** **Mergeada** (em `feature/fase4-custom-environment`)
- **Propósito:** Focada na orquestração da inicialização da simulação. Contém os arquivos responsáveis por iniciar o Gazebo, publicar o estado do robô (`robot_state_publisher`) e fazer o "spawn" do ASV (Autonomous Surface Vehicle). Também inclui o plugin de controle de velocidade e a ponte (bridge) ROS-Gazebo.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_bringup/launch/sim.launch.py` (Script de inicialização)
  - `src/asv_bringup/package.xml` (Atualização de dependências)
  - `src/asv_description/urdf/dummy_boat.urdf` (Adição e ajustes nos plugins em URDF)

## 5. `feature/fase1-asv-control`
- **Status:** **Mergeada** (em `feature/fase4-custom-environment`)
- **Propósito:** Implementa o pacote de controle e teleoperação do barco. Adiciona os scripts responsáveis por receber os comandos e atuar como nó de teleoperação para o barco.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_control/teleop_node.py` (Nó Python de teleoperação)
  - `src/asv_control/setup.py`, `src/asv_control/setup.cfg`, `src/asv_control/__init__.py` (Arquivos de setup do pacote de controle)
  - Modificações em dependências (ex.: `teleop_twist_keyboard`) no `src/asv_bringup/package.xml`

## 6. `feature/fase1-asv-gazebo`
- **Status:** **Mergeada** (em `feature/fase4-custom-environment`)
- **Propósito:** Criação do ambiente de simulação no Gazebo (pacote `asv_gazebo`). Define os mundos onde a embarcação será simulada.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_gazebo/worlds/empty_ocean.sdf` (Mundo vazio e base de simulação no oceano)
  - `src/asv_gazebo/CMakeLists.txt` e `src/asv_gazebo/package.xml` (Configuração do pacote)

## 7. `feature/fase1-asv-mavlink`
- **Status:** **Mergeada** (em `feature/fase4-custom-environment`)
- **Propósito:** Desenvolvimento da ponte de comunicação (MAVLink Bridge) funcional e integrada ao ROS 2. Prepara o ecossistema para integração futura com simuladores de controle de voo como ArduPilot e software base como QGroundControl.
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_mavlink/scripts/mavlink_bridge_node.py` (Estrutura inicial do nó usando `pymavlink`)
  - `src/asv_mavlink/launch/mavlink_bridge.launch.py` (Arquivo para launch da ponte)
  - `src/asv_mavlink/CMakeLists.txt` e `src/asv_mavlink/package.xml`

## 8. `feature/fase1-asv-missions`
- **Status:** **Ativa** (Ainda não mergeada na integração atual)
- **Propósito:** Adição do pacote `asv_missions` destinado a gerenciar o armazenamento e execução de missões. Cria a estrutura para carregar planos de voo e trajetórias do QGroundControl (`.plan`).
- **Principais Arquivos Modificados/Adicionados:**
  - `src/asv_missions/plans/sample_mission.plan` (Arquivo de amostra de missão extraído do QGroundControl)
  - `src/asv_missions/CMakeLists.txt` e `src/asv_missions/package.xml`
