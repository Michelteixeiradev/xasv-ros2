# Guia Prático: Migração de ASVs do ROS 1 (Gazebo Classic) para ROS 2 Jazzy (Gazebo Harmonic)

Este guia consolida as lições aprendidas durante a migração do projeto `xasv-sim` (Migbot) para servir de referência a outros projetos de embarcações autônomas (ASVs) e robótica aquática no laboratório.

---

## 1. Arquitetura e Pacotes (`catkin` → `colcon`)

No ROS 2, abandonamos o `catkin_make` e ferramentas antigas em favor do `colcon`. A estrutura de pacotes também se beneficia de uma divisão modular:

- `meurobo_bringup`: Contém os Launch files (agora em Python) e configurações globais.
- `meurobo_description`: Contém o URDF/Xacro e as malhas (meshes) 3D.
- `meurobo_gazebo`: Contém os mundos (`.sdf`) e modelos estáticos do ambiente.

**Dica:** Launch files em ROS 2 são scripts Python (`.launch.py`). Isso permite lógica complexa (if/else), passagem de parâmetros e melhor integração do que o antigo XML (`.launch`).

---

## 2. A Morte dos Plugins Antigos

No ROS 1 / Gazebo Classic, dependíamos de dezenas de plugins `libgazebo_ros_*.so` no URDF. No Gazebo Harmonic, a arquitetura mudou drasticamente: o Gazebo e o ROS 2 são entidades separadas.

### Como lidar:
1. **Remova** todos os `<plugin filename="libgazebo_ros...">` do seu URDF.
2. **Adicione** plugins nativos do Gazebo (`gz-sim-*-system`).
3. **Use o `ros_gz_bridge`** no seu arquivo de Launch para fazer a ponte entre os tópicos do Gazebo e do ROS 2.

**Exemplo de Ponte (Launch):**
```python
bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/model/meurobo/pose@geometry_msgs/msg/Pose[gz.msgs.Pose'],
    output='screen'
)
```

---

## 3. Física de Embarcações: O Fim do "Barco Voador"

Uma das maiores dores de cabeça na transição é a física de flutuabilidade. No Gazebo Harmonic, o motor de física principal é o **DART**.

### O Problema do `uniform_fluid_density`
Se você usar o plugin de Buoyancy no modo padrão (`uniform_fluid_density = 1000`), o Gazebo calculará o empuxo aplicando a força da água sobre **100% do volume da colisão do barco**, independentemente dele estar debaixo d'água ou levitando a 10 metros de altura no ar! Isso faz o barco subir como um balão infinitamente se o volume for grande.

### A Solução: `graded_buoyancy`
No arquivo do mundo (`.sdf`), você deve configurar o plugin de Buoyancy para fatiar as colisões na superfície da água (linha `z=0`):

```xml
<plugin filename="gz-sim-buoyancy-system" name="gz::sim::systems::Buoyancy">
  <graded_buoyancy>
    <default_density>1000</default_density> <!-- Água -->
    <density_change>
      <above_depth>0</above_depth>
      <density>0</density> <!-- Ar (sem empuxo) -->
    </density_change>
  </graded_buoyancy>
  <surface>0 0 1 0</surface>
</plugin>
```

### Regras de Ouro do URDF para Barcos:
1. **A matemática não perdoa:** O volume de colisão submerso multiplicado por 1000 (densidade da água) dita quantos Kgs o barco aguenta. Não use caixas de colisão enormes se o barco for leve.
2. **Centro de Massa (CoM):** A tag `<origin>` dentro de `<inertial>` **deve** estar dentro ou muito próxima da geometria de colisão. CoM muito fora (ex: simulando uma quilha mágica muito profunda) causa falhas no motor DART.
3. **Self-Collision de Hélices:** Remova as tags `<collision>` das hélices. No Harmonic, elas costumam interceder com o casco e gerar forças repulsivas infinitas (`NaN`), explodindo o barco no spawn. Use apenas a geometria visual para hélices.

---

## 4. Substituindo os Plugins Específicos Marítimos

No ROS 1, usávamos plugins da comunidade (ex: `gazebo_usv_dynamics_plugin`). No Harmonic, o Gazebo já fornece suporte oficial a veículos marítimos via SNAME.

### Propulsão (Thrusters)
Adicione o plugin `gz-sim-thruster-system` diretamente nas juntas das hélices no seu URDF. Ele aceita comandos em Newtons (Força) no tópico `/cmd_thrust` e simula a rotação visual.

### Arrasto (Hidrodinâmica)
O arrasto da água é simulado pelo plugin `gz-sim-hydrodynamics-system` adicionado ao `base_link`. Você fornece as matrizes SNAME (ex: `xU`, `xUabsU`, `nR`) e ele impede que o barco acelere infinitamente na água, aplicando resistência baseada na velocidade.

---

## 5. Sensores

Sensores agora são definidos dentro de tags `<sensor>` nativas do Gazebo (tipo `imu`, `navsat`, `magnetometer`).
- Eles geram tópicos no formato Gazebo Transport (ex: `gz.msgs.IMU`).
- Você deve instanciar a ponte `ros_gz_bridge` no seu arquivo `.launch.py` para converter `gz.msgs.IMU` para `sensor_msgs/msg/Imu` no ROS 2.

---

## 6. Autopiloto e Comunicação (MAVROS vs AP_DDS)

Se o projeto usar ArduPilot em SITL (Software-In-The-Loop) ou HITL:
- **ROS 1:** MAVROS era o padrão absoluto, comunicando-se via serial/UDP com o protocolo MAVLink.
- **ROS 2:** Embora o `mavros` exista no ROS 2, a arquitetura recomendada agora é o **AP_DDS** (Micro-ROS nativo do ArduPilot).
  - O firmware do ArduPilot publica os tópicos (ex: `/ap/pose/filtered`) **diretamente na rede ROS 2**.
  - O overhead cai de ~50ms (MAVROS) para ~2ms (DDS).
  - Extremamente benéfico para pipelines modernos que envolvem redes neurais (PyTorch) ou processamento visual em tempo real para tomada de decisão (ex: envio direto em `/ap/cmd_vel`).

---
**Autor:** Equipe de Migração (Data: Abril 2026)
