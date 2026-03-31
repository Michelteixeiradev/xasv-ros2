# Plano de Migração: ROS1 para ROS2 (Fase 1)

## Objetivo
Criar uma base funcional em ROS2 (Jazzy) para o projeto xasv-sim, focando no fluxo principal de simulação sem depender de hardware físico no momento.

## Arquitetura de Pacotes
Os seguintes pacotes foram criados no workspace `ros2_asv_ws/src/`:
- `asv_bringup`: Conterá os arquivos de inicialização (launch).
- `asv_description`: Conterá os modelos 3D e URDF do robô.
- `asv_gazebo`: Conterá os cenários de simulação.
- `asv_control`: Conterá os nós de controle e teleoperação.
- `asv_mavlink`: Conterá a comunicação com o piloto automático.
- `asv_missions`: Conterá scripts de teste e validação.

## Arquivos Launch Previstos
- `sim.launch.py` (dentro de `asv_bringup`): Responsável por abrir o Gazebo, carregar o robô e publicar os estados (robot_state_publisher).

## Critérios de Aceite da Fase 1
1. O workspace compila sem erros.
2. O simulador Gazebo abre através de um arquivo launch único.
3. Um robô genérico aparece no mundo virtual.