# Guia de Spawn e Estabilidade Física no Gazebo Harmonic

Este documento registra as lições aprendidas e as configurações exatas necessárias para que o ASV (Migbot) seja instanciado ("spawn") corretamente e mantenha estabilidade no simulador Gazebo Harmonic, evitando comportamentos anômalos como voar, girar fora de controle ou renderizar de forma incorreta.

## 1. O Problema do "Barco Voador" e a Ilusão de Ótica
**Sintoma:** O barco parecia nascer corretamente, mas apenas sua sombra era visível na água. Ao enviar comandos de movimento (`/cmd_vel`), o barco parecia se mover de forma estranha e "longe da câmera". Ao tentar corrigir isso rotacionando os eixos, o barco subia como um foguete vertical.

**Causa Raiz:** 
1. O comando de spawn no `sim.launch.py` estava configurado para soltar o barco a 1.5 metros de altura (`z=1.5`).
2. O uso do plugin `gz::sim::systems::VelocityControl` torna o link principal **cinemático**. Objetos cinemáticos não sofrem ação da gravidade.
3. Conclusão: O barco não estava com os eixos quebrados; ele estava literalmente **pairando no ar a 1.5m de altura**, e o observador via apenas a sombra sendo projetada no rio.

## 2. A Solução para um Spawn Perfeito

Para garantir que o modelo inicie adequadamente sobre a superfície do mapa (`madeira_river_simple`), siga estas regras no arquivo `sim.launch.py`:

```python
# Correto: Spawn com Z rente à água e X/Y no centro do rio.
spawn_entity = Node(
    package='ros_gz_sim',
    executable='create',
    arguments=['-name', 'migbot', '-string', robot_desc,
               '-x', '100.0', '-y', '20.0', '-z', '0.3'],
    output='screen'
)
```

## 3. Estabilidade do URDF (Armadilhas de Colisão)
O motor de física DART (padrão do Gazebo Harmonic) é extremamente sensível a hierarquias de colisão malformadas ou sobrepostas, especialmente quando o plugin `Buoyancy` (Flutuabilidade) entra em ação.

**Regras de Ouro para o `migbot.urdf.xacro`:**
- **Sem Rotações Compensatórias:** Mantenha o `<visual>` e `<collision>` do `base_link` com `rpy="0 0 0"`. O CAD original já possui os eixos corretos.
- **Evite Duplicatas:** Nunca coloque mais de uma tag `<origin>` ou `<geometry>` dentro do mesmo bloco `<collision>`. Cada caixa geométrica exige um bloco `<collision>` isolado.
- **Cuidado com Auto-colisões (Self-Collision):** Cilindros de colisão nas hélices que intersectam as caixas de colisão do casco principal geram forças repulsivas infinitas ("explosão" física), fazendo o modelo girar infinitamente (o bug do giro louco).
- **Inércia Realista:** O centro de massa (`origin` da tag `<inertial>`) deve estar alinhado fisicamente de forma a manter o centro de empuxo equilibrado.

## 4. Configuração de Sensores Reais (Subfase 6A)
Na migração para Gazebo Harmonic, os plugins de sensores foram abolidos de dentro de `<gazebo>` genéricos. Eles devem usar referencias a links específicos:

```xml
<gazebo reference="imu_link">
  <sensor name="imu_sensor" type="imu">
    <always_on>1</always_on>
    <update_rate>50</update_rate>
    <topic>imu</topic>
    <gz_frame_id>imu_link</gz_frame_id>
  </sensor>
</gazebo>
```

Esta documentação serve como referência obrigatória ("checkpoint mental") antes de tentarmos implementar plugins mais avançados de hidrodinâmica (SNAME) ou thrusters individuais (Subfase 6B).

## 5. Dinâmica de Flutuabilidade: Barco de Ponta-Cabeça e Proa Afundando
**Sintoma 1 (Barco Invertido):** O barco spawnava perfeitamente, mas caía na água e girava 180 graus, ficando com as hélices apontadas para o céu.
* **Solução Aplicada:** O Centro de Massa (CoM) original no eixo `Z` estava muito alto (`z=0.25`). Para que um barco seja naturalmente estável na água (efeito "joão-bobo"), o Centro de Massa precisa estar o mais baixo possível em relação ao Centro de Flutuabilidade. A IA anterior abaixou a origem inercial no eixo Z para `0.15`, forçando o barco a ficar de pé corretamente. Além disso, foram enxugadas as caixas de colisão antigas, simplificando os pontões.

**Sintoma 2 (Proa Afundando / Fundo Saltado):** Após a correção do eixo Z, o barco ficou na posição certa (hélices na água), mas a frente do barco (proa) começou a "embicar" para baixo, deixando a parte traseira levantada.
* **Causa Raiz:** O Centro de Massa no eixo longitudinal (`X`) estava muito à frente (`x=0.387`). No Gazebo, o `BuoyancyPlugin` calcula o empuxo estritamente pelo volume das malhas de colisão (`<collision>`) que estão submersas. Se o peso do barco estiver concentrado muito à frente do centro desse volume submerso, ele vai afundar a frente. Além disso, o peso das próprias hélices lá atrás influencia a inércia total.
* **Solução Aplicada:** Movimentamos a origem inercial no eixo X para trás, reduzindo de `0.387` para `0.150` no `<inertial>` do `base_link`. Isso atua como se tivéssemos colocado um contrapeso no fundo do barco, equilibrando a gangorra e deixando a linha d'água perfeitamente alinhada.
