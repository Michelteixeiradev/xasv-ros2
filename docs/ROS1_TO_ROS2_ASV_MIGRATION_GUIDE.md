# Guia Prático: Migração de ASVs do ROS 1 (Gazebo Classic) para ROS 2 Jazzy (Gazebo Harmonic)

Este guia consolida as lições aprendidas durante a migração do projeto `xasv-sim` (Migbot) para servir de referência a outros projetos de embarcações autônomas (ASVs) e robótica aquática no laboratório. A transição não é apenas uma troca de sintaxe, mas uma mudança completa de paradigma arquitetural.

## 1. Arquitetura e Pacotes (`catkin` → `colcon`)

No ROS 2, abandonamos o `catkin_make` e ferramentas antigas em favor do `colcon`. A estrutura de pacotes também se beneficia de uma divisão estritamente modular:

- `meurobo_bringup`: Contém os Launch files (agora em Python) e configurações globais.
- `meurobo_description`: Contém o URDF/Xacro e as malhas (meshes) 3D.
- `meurobo_gazebo`: Contém os mundos (`.sdf`) e modelos estáticos do ambiente.

> **Dica de Arquitetura:** Launch files em ROS 2 são scripts Python (`.launch.py`). Isso permite lógica complexa, passagem de parâmetros dinâmicos e uma infraestrutura excelente para Injeção de Dependência (DI) ao instanciar os nós, o que facilita testes e isolamento de código.

## 2. A Morte dos Plugins Antigos

No ROS 1 / Gazebo Classic, dependíamos de dezenas de plugins `libgazebo_ros_*.so` embutidos no URDF. No Gazebo Harmonic, o simulador e o ROS 2 são entidades completamente separadas.

### Como lidar com a nova estrutura:

1. **Remova** todos os `<plugin filename="libgazebo_ros...">` do seu URDF.
2. **Adicione** plugins nativos do próprio Gazebo (`gz-sim-*-system`).
3. **Use a `ros_gz_bridge`** no seu arquivo de Launch para fazer a ponte de comunicação entre os tópicos internos do Gazebo e o ecossistema ROS 2.

**Exemplo de Ponte (no `sim.launch.py`):**
```python
bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/model/meurobo/pose@geometry_msgs/msg/Pose[gz.msgs.Pose'],
    output='screen'
)
```

## 3. Física de Embarcações: O Fim do "Barco Voador"

Uma das maiores dores de cabeça na transição é a física de flutuabilidade. No Gazebo Harmonic, o motor de física principal (DART) calcula forças de forma muito mais rigorosa.

### O Problema do `uniform_fluid_density`

Se você usar o plugin de Buoyancy no modo padrão (`uniform_fluid_density = 1000`), o Gazebo calculará o empuxo aplicando a força da água sobre **100% do volume da colisão do barco**, independentemente dele estar debaixo d'água ou levitando no ar. Isso faz o barco subir infinitamente se a massa não for perfeitamente balanceada com o volume total.

### A Solução: `graded_buoyancy`

No arquivo do mundo (`.sdf`), configure o plugin para fatiar as colisões na superfície da água (linha `z=0`):

```xml
<plugin filename="gz-sim-buoyancy-system" name="gz::sim::systems::Buoyancy">
  <graded_buoyancy>
    <default_density>1000</default_density> <!-- Água -->
    <density_change>
      <above_depth>0</above_depth>
      <density>0</density> <!-- Ar (sem empuxo ascendente) -->
    </density_change>
  </graded_buoyancy>
  <surface>0 0 1 0</surface>
</plugin>
```

### Regras de Ouro do URDF para Barcos:

- **A matemática não perdoa:** O volume de colisão submerso multiplicado pela densidade do fluido dita quantos quilos o barco aguenta. Não projete caixas de colisão superdimensionadas se o barco físico for leve.
- **Centro de Massa (CoM):** A tag `<origin>` dentro de `<inertial>` **deve** estar dentro ou muito próxima da geometria de colisão. Um CoM distante causa instabilidade matemática e falhas catastróficas no motor DART.
- **Self-Collision de Hélices:** Remova as tags `<collision>` das hélices. No Harmonic, elas intercedem com o casco, gerando forças repulsivas infinitas (`NaN`) e fazendo o barco explodir no spawn. Use apenas a malha visual para sistemas de propulsão acoplados.

## 4. Hidrodinâmica Avançada e SNAME

No ROS 1, usávamos plugins não oficiais da comunidade. No Harmonic, o Gazebo fornece suporte nativo a veículos marítimos.

### Propulsão (Thrusters)
O plugin `gz-sim-thruster-system` é adicionado diretamente nas juntas das hélices no URDF. Ele aceita comandos em Newtons (Força) via `/cmd_thrust` e simula a rotação visual e a força vetorial física.

### Arrasto e Matrizes SNAME
O arrasto da água é simulado pelo plugin `gz-sim-hydrodynamics-system` no `base_link`. O Gazebo Harmonic calcula as forças de resistência utilizando a formulação SNAME clássica. A força de arrasto ($X$) em um grau de liberdade (como o avanço longitudinal $u$) é modelada com componentes lineares e quadráticas:

`X = X_u_dot * u_dot + X_u * u + X_u_abs_u * u * |u|`

- **X_u_dot:** Massa adicional (Added Mass) — a inércia da água que o barco precisa deslocar ao acelerar.
- **X_u:** Coeficiente de arrasto linear (força dominante em baixas velocidades).
- **X_u_abs_u:** Coeficiente de arrasto quadrático (força dominante em altas velocidades).

> **Atenção:** Inserir valores arbitrários nestes coeficientes fará o barco acelerar ao infinito ou navegar como se estivesse em uma piscina de mel. Utilize ensaios reais do casco, softwares de CFD ou aproximações empíricas validadas.

## 5. Sensores

Sensores agora são definidos dentro de tags `<sensor>` nativas do Gazebo (ex: `imu`, `navsat`, `magnetometer`, `gpu_lidar`).

- A simulação gera dados no formato interno Gazebo Transport (ex: `gz.msgs.IMU`).
- Para que a sua pilha de navegação os enxergue, instancie a `ros_gz_bridge` no seu arquivo `.launch.py` mapeando `gz.msgs.IMU` para a mensagem padrão `sensor_msgs/msg/Imu` do ROS 2.

## 6. Autopiloto e Comunicação (Adoção do AP_DDS)

Para projetos que utilizam ArduPilot em SITL (Software-In-The-Loop) ou integração de hardware:

- **A Era do MAVROS passou:** O MAVROS era o padrão no ROS 1, comunicando-se via serial/UDP usando o protocolo MAVLink. No ROS 2, ele atua como um intermediário que adiciona latência indesejada.
- **O Novo Padrão - AP_DDS:** Adotamos o Micro-ROS nativo do ArduPilot. O firmware publica os tópicos de telemetria (ex: `/ap/pose/filtered`) e escuta comandos diretamente na malha do ROS 2.
  - **Performance:** A latência de comunicação cai de ~50ms (MAVROS) para ~2ms (DDS).
  - **Autonomia:** Essa topologia é requisito fundamental para pipelines de IA, permitindo que redes neurais baseadas em PyTorch enviem comandos de velocidade diretamente no tópico `/ap/cmd_vel` com resposta de baixo nível em tempo real.

## 7. Debugging e Visualização (CLI e RViz2)

Com a fronteira estrita entre simulador e middleware, a depuração exige novas práticas. A primeira falha geralmente ocorre na ponte de dados.

### Isolando o Problema
Utilize as ferramentas de linha de comando simultaneamente para rastrear onde o pacote se perde:
- **Lado Gazebo:** `gz topic -l` e `gz topic -e -t /nome_do_topico` (Confirma se a física gerou a informação).
- **Lado ROS 2:** `ros2 topic echo /nome_do_topico` (Confirma se a ponte realizou a tradução com sucesso).

### RViz2 como Fonte da Verdade
O visualizador do Gazebo mostra o cenário ideal. O RViz2 mostra o que as "mentes" dos algoritmos enxergam. Configure-o para assinar os tópicos de `PointCloud2` (LiDAR) e `Image` (Câmeras) para garantir que as matrizes de transformação (TF) estão publicando os frames nos locais corretos.

## 8. Padrões de Repositório, Code Review e Arquitetura

A migração é a oportunidade de elevar o rigor do ciclo de desenvolvimento no laboratório. Para garantir manutenibilidade e facilitar os processos de Peer Review em Pull Requests, todos os módulos ROS 2 devem seguir:

- **Commits Semânticos (Conventional Commits):** Padronizem o histórico para rastreabilidade (ex: `feat(dynamics): add SNAME hydrodynamics parameters to hull`, `fix(bridge): remap IMU topic to standard sensor_msgs`).
- **Test-Driven Development (TDD):** A nova estrutura de Nodes do ROS 2 Python é altamente favorável ao desenvolvimento orientado a testes. Escrevam a lógica de cobertura antes de validar no simulador físico.
- **Modularidade Absoluta:** O código de percepção ou navegação não deve conter referências amarradas (hardcoded) ao simulador. Utilize arquivos de parâmetros (`.yaml`) para definir constantes mecânicas.

---
**Autor:** Equipe de Migração (Atualizado: Abril 2026)
