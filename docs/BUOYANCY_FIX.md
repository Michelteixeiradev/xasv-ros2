# Guia: Como Impedir o Barco de Levitar no Gazebo Harmonic

> **Este documento existe porque levamos horas para resolver este problema.**
> Leia-o inteiramente antes de mexer em qualquer configuração de física.

## O Sintoma

Ao remover o `VelocityControl` (controlador cinemático) e ativar a física real,
o barco **levita verticalmente para cima sem parar**, como um balão de hélio.
Não é uma explosão (NaN), é uma ascensão suave e constante.

## A Causa Raiz

O plugin `gz-sim-buoyancy-system` possui **dois modos** de operação:

### ❌ `uniform_fluid_density` (O VILÃO)

```xml
<plugin filename="gz-sim-buoyancy-system" name="gz::sim::systems::Buoyancy">
  <uniform_fluid_density>1000</uniform_fluid_density>
</plugin>
```

Neste modo, o Gazebo calcula a força de empuxo sobre **100% do volume de colisão,
SEMPRE**, independentemente da posição Z do modelo. Ele **NÃO** fatia o volume
pela linha d'água. Se `F_buoyancy > F_gravity`, o barco sobe infinitamente.

**A matemática que prova:**
```
Volume de colisão total = 0.44 m³ (dois pontões de 2.3×0.286×0.334)
F_buoyancy = 0.44 × 1000 × 9.81 = 4316 N  (para cima)
F_gravity  = 142.5 × 9.81       = 1398 N  (para baixo)
F_líquida  = 4316 - 1398         = +2918 N (PARA CIMA → barco vira balão!)
```

### ✅ `graded_buoyancy` (A SOLUÇÃO)

```xml
<plugin filename="gz-sim-buoyancy-system" name="gz::sim::systems::Buoyancy">
  <graded_buoyancy>
    <default_density>1000</default_density>
    <density_change>
      <above_depth>0</above_depth>
      <density>0</density>
    </density_change>
  </graded_buoyancy>
  <surface>0 0 1 0</surface>
</plugin>
```

Neste modo, o Gazebo define:
- **Abaixo de z=0:** fluido com densidade 1000 kg/m³ (água)
- **Acima de z=0:** densidade 0 (ar, sem empuxo)

O plugin **fatia cada caixa de colisão na superfície** (z=0) e aplica empuxo
**apenas no volume submerso**. Isso é o Princípio de Arquimedes real.

**Resultado no equilíbrio:**
```
Volume submerso necessário = massa / ρ = 142.5 / 1000 = 0.1425 m³
Cada pontão: 2.3 × 0.286 = 0.658 m² de seção
Dois pontões: 1.316 m²
Calado (profundidade submersa) = 0.1425 / 1.316 = 0.108 m ≈ 11 cm
→ ~32% dos pontões ficam submersos. Barco flutua estável.
```

## Outras Armadilhas Resolvidas no Caminho

### 1. Self-Collision das Hélices (Explosão NaN)
As 6 hélices tinham cilindros de colisão que intersectavam o casco.
O motor DART calculava forças repulsivas infinitas → barco explodia.
**Solução:** Remover todos os `<collision>` das hélices. Os plugins Thruster
são puramente matemáticos e não precisam de colisão.

### 2. VelocityControl Mascara Defeitos
O plugin `VelocityControl` torna o modelo **cinemático** (ignora gravidade,
buoyancy e todas as forças). Ele mascara 100% dos problemas de física.
Só remova-o quando estiver pronto para a dinâmica real.

### 3. Centro de Massa (CoM) Fora do Volume de Colisão
Colocar o `<origin>` do `<inertial>` muito longe das colisões (ex: z=-0.3
quando as colisões estão em z=0.028) causa instabilidades no DART.
**Regra:** Mantenha o CoM dentro ou muito próximo do volume de colisão.

### 4. Spawn Alto Demais
Com `VelocityControl`, spawnar em z=1.5 não causava problemas (cinemático).
Sem ele, o barco cai 1.5m e bate na água com violência.
**Regra:** Spawne em z=0.1 (logo acima da superfície).

## Arquivo de Referência

| Arquivo | O que configurar |
|---------|-----------------|
| `src/asv_gazebo/worlds/madeira_river_simple.sdf` | `graded_buoyancy` no plugin Buoyancy |
| `src/asv_description/urdf/migbot.urdf.xacro` | Colisões, massa, CoM, Thrusters, Hydro |
| `src/asv_bringup/launch/sim.launch.py` | Coordenadas de spawn e bridges |
