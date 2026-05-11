# Mapeamento de Branches - xasv-ros2

> **Atualizado:** 2026-05-08
> **Branch de integração ativa:** `feature/fase6b-integration` (35 commits à frente de `main`, sincronizada com origin).

Este documento mapeia branches do repositório `xasv-ros2`, evolução do projeto e merges realizados. Detalha propósito de cada branch, arquivos principais e status atual.

## Visão geral

```text
main  ───────────────────────────────────────────────────────────────  (base)
   │
   ├── chore/setup-devcontainer                                        (ativa, paralela)
   │
   └── feature/fase1-asv-gazebo  ─┐
       feature/fase1-asv-bringup-launch ─┤
       feature/fase1-asv-control ────────┼──► fase4-custom-environment ──► fase5-custom-robot
       feature/fase1-asv-mavlink ────────┘                                            │
       feature/fase1-asv-missions (não mergeada)                                      ▼
                                                              fase6-integration-new ──► fase6b-integration  (HEAD atual)
                                                                                            │
                                                                                            └── contém Fases 1-7 fechadas
```

## 1. `main`
- **Status:** Ativa (branch principal).
- **Propósito:** Base do repositório. Ainda **não recebeu** o merge da integração das fases. Todo trabalho de Fase 1 a 7 vive em `feature/fase6b-integration`.
- **Pendência:** abrir PR `feature/fase6b-integration` → `main` quando Fase 8 começar a estabilizar, para consolidar o caminho oficial.

## 2. `feature/fase6b-integration` — **branch de integração atual (HEAD)**
- **Status:** **Ativa**, sincronizada com `origin`, 35 commits à frente de `main`.
- **Propósito:** Consolida trabalhos das Fases 1 a 7. Sucessora natural de `fase6-integration-new`. Contém:
  - **Fase 6B (dinâmica real):** remoção do `VelocityControl`, `graded_buoyancy`, 6× `Thruster`, `Hydrodynamics` SNAME.
  - **Fase 7 (ArduPilot SITL avançada):** `ArduPilotPlugin` no URDF, mixer Lua V5 (`FRAME_CLASS=15`), bridge MAVLink → `cmd_vel` dos thrusters, AP_DDS auto-start com fix de race (`respawn=True`, agent t=10s / SITL t=18s / bridge t=28s), missão WP1 → WP2 em AUTO via QGroundControl.
- **Arquivos chave:**
  - `src/asv_bringup/launch/sim.launch.py` (fluxo automático SITL + AP_DDS + bridge).
  - `src/asv_description/urdf/migbot.urdf.xacro` (modelo físico, thrusters, hidrodinâmica, `ArduPilotPlugin`).
  - `src/asv_gazebo/worlds/madeira_river_simple.sdf` (mundo com `graded_buoyancy`).
  - `src/asv_mavlink/asv_mavlink/mavlink_bridge_node.py` (MAVLink → `cmd_vel` por junta).
  - `src/asv_mavlink/asv_mavlink/fase7_sanity_check.py` (validação automatizada `SERVO_OUTPUT_RAW → cmd_vel → force → pose`).
  - `config/migbot_mixer.lua` (V5, híbrido AP/RC).
  - `config/migbot_sitl.param` (FRAME_CLASS=15, SCR_ENABLE=1, SERVO1-6_FUNCTION 94-99, dummies SERVO7=70/SERVO8=26).
  - `docs/FASE7_AP_DDS.md`, `docs/FASE7_STATUS.md`, `docs/MOTOR_MIXER_DOSSIER.md`.
  - `docs/diario/2026-05-06.md` (registro do fechamento da Fase 7).
- **Commits relevantes:**
  - `946be7d` docs(diario): cria diário do projeto e registra sessão 2026-05-06.
  - `f69baf8` feat(fase7): fecha Fase 7 com AP_DDS auto-start, mixer Lua V5 e missão WP1→WP2.
  - `da5c949` docs: documentação técnica detalhada da Fase 7 (AP_DDS).
  - `bea1dca` feat(fase6): subfase 6B — fix do "barco voador".
  - `f827505` feat(fase6b): dinâmica real — thrusters, hidrodinâmica e flutuabilidade.

## 3. `feature/fase6-integration-new`
- **Status:** **Mergeada** em `feature/fase6b-integration` (substituída pela continuação 6B).
- **Propósito:** Fase 6A — primeira integração de sensores nativos do Gazebo Harmonic (IMU, GPS, magnetômetro) + correção do spawn no rio.
- **Arquivos chave:**
  - `src/asv_description/urdf/migbot.urdf.xacro` (sensores nativos `<sensor>` em vez de plugins legados).
  - `src/asv_bringup/launch/sim.launch.py` (spawn corrigido, bridges para `/imu`, `/navsat`, `/magnetometer`).
  - `docs/SPAWN_TROUBLESHOOTING.md`.
- **Commits relevantes:**
  - `8a45508` docs: doc de spawn do barco.
  - `64c5fc8` feat(fase6): subfase 6A — sensores IMU/GPS/MAG + spawn correto no rio.

## 4. `feature/fase5-custom-robot`
- **Status:** **Mergeada** (em `fase6-integration-new` → `fase6b-integration`).
- **Propósito:** Migração do modelo URDF/Xacro real do Migbot para ROS 2. Limpeza de plugins Gazebo Classic, ajuste de meshes, controle cinemático provisório `VelocityControl` para validar geometria e flutuabilidade básica.
- **Arquivos chave:**
  - `src/asv_description/urdf/migbot.urdf.xacro` (versão limpa, sem `libgazebo_ros_*.so`).
  - `src/asv_description/meshes/` (DAE migrados do projeto ROS 1).
- **Commits relevantes:**
  - `1aa9393` feat(fase5): migração do modelo URDF do Migbot, correções de meshes e Gazebo buoyancy.
  - `7f605a7` docs: atualiza PLAN.md e relatorio.md com status das Fases 4 e 5.

## 5. `feature/fase4-custom-environment`
- **Status:** **Mergeada** (em `fase5-custom-robot` → `fase6-integration-new` → `fase6b-integration`).
- **Propósito:** Substituição do mundo genérico (`empty_ocean`) pelo cenário Rio Madeira. Foi historicamente a primeira branch de integração antes de a sequência migrar para `fase6b-integration`. Consolidou também merges das Fases 1.
- **Arquivos chave:**
  - `src/asv_gazebo/worlds/madeira_river_simple.sdf`.
  - `src/asv_bringup/launch/sim.launch.py` (carregamento dinâmico de mundos, roteamento de tópicos).
  - `docs/GUIA_FASES.md` (criado nesta branch).
- **Commits relevantes:**
  - `2d2f8a5` docs: move markdown files to docs directory.
  - `2c6e635` feat: inclusão do Guia de fases + Madeira river no `sim.launch`.
  - `ceb93fb` feat(sim): adiciona mundo `madeira_river_simple` e roteamento dinâmico.
- **Merges recebidos:** `feature/fase1-asv-gazebo`, `feature/fase1-asv-bringup-launch`, `feature/fase1-asv-mavlink`, `feature/fase1-asv-control`.

## 6. `chore/setup-devcontainer`
- **Status:** **Ativa**, paralela ao fluxo principal.
- **Propósito:** Configuração de ambiente de desenvolvimento remoto via DevContainers. Padroniza ferramentas e dependências.
- **Arquivos chave:** `../.devcontainer/devcontainer.json`.
- **Pendência:** decidir se entra em `main` antes ou depois da consolidação Fase 7.

## 7. `feature/fase1-asv-bringup-launch`
- **Status:** **Mergeada** (em `fase4-custom-environment`).
- **Propósito:** Orquestração inicial da simulação. Gazebo + `robot_state_publisher` + spawn ASV. Plugin `VelocityControl` provisório e ponte ROS↔Gazebo.
- **Arquivos chave:**
  - `src/asv_bringup/launch/sim.launch.py` (versão Fase 1).
  - `src/asv_bringup/package.xml`.
  - `src/asv_description/urdf/dummy_boat.urdf` (URDF inicial genérico).

## 8. `feature/fase1-asv-control`
- **Status:** **Mergeada** (em `fase4-custom-environment`).
- **Propósito:** Pacote de controle/teleoperação. Recebe comandos e atua como nó de teleop.
- **Arquivos chave:**
  - `src/asv_control/teleop_node.py`.
  - `src/asv_control/setup.py`, `setup.cfg`, `__init__.py`.
  - Dependência `teleop_twist_keyboard` em `src/asv_bringup/package.xml`.

## 9. `feature/fase1-asv-gazebo`
- **Status:** **Mergeada** (em `fase4-custom-environment`).
- **Propósito:** Pacote `asv_gazebo`. Define mundos iniciais.
- **Arquivos chave:**
  - `src/asv_gazebo/worlds/empty_ocean.sdf`.
  - `src/asv_gazebo/CMakeLists.txt`, `package.xml`.

## 10. `feature/fase1-asv-mavlink`
- **Status:** **Mergeada** (em `fase4-custom-environment`).
- **Propósito:** Estrutura inicial da bridge MAVLink. Base para integração futura com ArduPilot SITL e QGC.
- **Arquivos chave:**
  - `src/asv_mavlink/scripts/mavlink_bridge_node.py` (estrutura inicial pymavlink).
  - `src/asv_mavlink/launch/mavlink_bridge.launch.py`.
  - `src/asv_mavlink/CMakeLists.txt`, `package.xml`.
- **Nota:** evoluiu na Fase 7 para o nó atual `src/asv_mavlink/asv_mavlink/mavlink_bridge_node.py`, que consome `SERVO_OUTPUT_RAW` e publica `cmd_vel` por junta dos 6 thrusters.

## 11. `feature/fase1-asv-missions`
- **Status:** **Não mergeada** (existe em `origin`, sem merge na integração atual).
- **Propósito:** Pacote `asv_missions` para gerenciar missões `.plan` do QGC.
- **Arquivos chave:**
  - `src/asv_missions/plans/sample_mission.plan`.
  - `src/asv_missions/CMakeLists.txt`, `package.xml`.
- **Pendência:** avaliar merge antes da Fase 8 (obstacle avoidance e missões IA podem reusar essa estrutura).

---

## Resumo do estado atual

| Branch | Estado | Fase coberta |
|--------|--------|--------------|
| `main` | Base, sem integração | Pré-Fase 1 |
| `feature/fase6b-integration` | **HEAD ativo**, sync com origin | Fases 1-7 fechadas |
| `feature/fase6-integration-new` | Mergeada em 6b | Fase 6A |
| `feature/fase5-custom-robot` | Mergeada | Fase 5 |
| `feature/fase4-custom-environment` | Mergeada | Fase 4 + integração das Fases 1 |
| `feature/fase1-asv-bringup-launch` | Mergeada | Fase 1 (bringup) |
| `feature/fase1-asv-control` | Mergeada | Fase 1 (control) |
| `feature/fase1-asv-gazebo` | Mergeada | Fase 1 (gazebo) |
| `feature/fase1-asv-mavlink` | Mergeada | Fase 1 (mavlink) |
| `feature/fase1-asv-missions` | **Não mergeada** | Fase 1 (missions) |
| `chore/setup-devcontainer` | Ativa, paralela | Infra dev |

## Próximos passos de branching

1. Abrir `feature/fase8-obstacle-avoidance` a partir de `fase6b-integration` (Nav2 ou `OA_TYPE`/`PRX_TYPE`).
2. Avaliar merge de `feature/fase1-asv-missions` antes da Fase 8 (sample `.plan` reutilizável).
3. Consolidar `fase6b-integration` em `main` quando Fase 7 estiver com `git tag v0.7.0` e sanity check passando em CI.
4. Decidir destino de `chore/setup-devcontainer` (merge ou manter paralela).
