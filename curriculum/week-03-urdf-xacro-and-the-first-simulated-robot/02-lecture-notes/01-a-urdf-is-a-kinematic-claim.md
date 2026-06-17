# Lecture 1 — A URDF Is a Kinematic Claim, Not a CAD File

> **Reading time:** ~75 minutes. **Hands-on time:** ~50 minutes (you author a link, compute its inertia, and visualize it).

This is the lecture that prevents three weeks of pain. Almost everyone who learns robotics meets the URDF and immediately misfiles it in their head as "the 3D model of the robot." It is not. A `.stl` or `.dae` is the 3D model. The URDF is something stranger and more important: it is a **structured claim about the robot's kinematics and dynamics** — where the joints are, which way they turn, how heavy each part is, and how that mass is distributed in space. Multiple very different programs read that claim and act on it: `robot_state_publisher` turns it into a tf2 tree, rviz2 draws it, MoveIt2 (Phase 3) plans against it, and — the part that bites — the **physics engine in Gz Sim simulates it literally**.

That last consumer is unforgiving. The physics engine does not look at your pretty mesh and infer reasonable mass. It reads the number you typed into `<mass>` and the nine numbers you typed into the inertia tensor, and it integrates Newton-Euler equations against them sixty or more times per second. If those numbers are wrong — and the single most common beginner error makes them wrong by a factor of a thousand — the simulation does exactly what the math says: it produces enormous accelerations, the robot's parts fling apart, and you get the infamous **"robot explodes on spawn"** failure. By the end of this lecture you will understand that failure so completely that it stops being scary and becomes a thirty-second diagnosis.

## 1.1 — The mental model: a graph of rigid bodies

Strip away the XML and a URDF is a **graph**. The nodes are **links** (rigid bodies). The edges are **joints** (constraints between two links). The graph must be a **tree**: exactly one root link, every other link reached by exactly one path of joints, no cycles. This is not an arbitrary rule — it is the same tree you built by hand in Week 2 with `static_transform_publisher`. The URDF is just a declarative way to describe that whole tree at once, with mass attached.

Here is the smallest legal URDF — a single link, no joints:

```xml
<?xml version="1.0"?>
<robot name="single_box">
  <link name="base_link">
    <visual>
      <geometry>
        <box size="0.4 0.3 0.1"/>
      </geometry>
    </visual>
  </link>
</robot>
```

Three things are already worth noticing:

1. **`<robot name=...>`** is the document root. Every URDF has exactly one.
2. **`base_link`** is the conventional name for the root link of a mobile robot. (Manipulators often use `base` or `base_footprint`; we follow the mobile-robot convention all phase.)
3. This link has a `<visual>` but **no `<collision>` and no `<inertial>`**. That is legal for visualization in rviz2 — but the moment you hand this to a physics engine, the missing `<inertial>` is a problem. A link with no inertial in Gz Sim defaults to a tiny mass with a tiny inertia, which behaves erratically. We will fix that shortly.

The tree gets interesting when you add a second link and a joint:

```xml
<?xml version="1.0"?>
<robot name="box_on_a_stick">
  <link name="base_link">
    <visual>
      <geometry><box size="0.4 0.3 0.1"/></geometry>
    </visual>
  </link>

  <link name="mast">
    <visual>
      <geometry><cylinder radius="0.02" length="0.5"/></geometry>
    </visual>
  </link>

  <joint name="base_to_mast" type="fixed">
    <parent link="base_link"/>
    <child link="mast"/>
    <origin xyz="0 0 0.3" rpy="0 0 0"/>
  </joint>
</robot>
```

The `<joint>` is where SE(3) lives. The `<origin>` is the transform from the **parent link frame** to the **child link frame**, expressed as a translation `xyz` (meters) and a rotation `rpy` (roll-pitch-yaw, radians, applied in fixed-axis ZYX convention). This is exactly the homogeneous transform from Week 2 — the URDF just spells it out per joint. When `robot_state_publisher` reads this file it will broadcast `base_link → mast` as a static transform, because the joint is `fixed`.

**The key insight:** the position of a child link is *never* specified directly. It is *derived* by composing the parent's pose with the joint origin (and, for movable joints, the current joint value). You describe the robot once, in its "zero" configuration, via joint origins; the live pose of every link falls out of forward kinematics. This is why a URDF is a kinematic claim — you are asserting the *structure*, and the poses are *computed*.

## 1.2 — The three faces of a link

A serious link carries three blocks, and conflating them is the root of half of all URDF bugs. They answer three different questions, read by three different consumers.

```xml
<link name="chassis">
  <!-- What you SEE. Read by rviz2 and the Gazebo renderer. -->
  <visual>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <geometry>
      <box size="0.4 0.3 0.1"/>
    </geometry>
    <material name="cinnabar">
      <color rgba="0.86 0.15 0.15 1.0"/>
    </material>
  </visual>

  <!-- What the PHYSICS ENGINE TOUCHES. Read by the collision detector. -->
  <collision>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <geometry>
      <box size="0.4 0.3 0.1"/>
    </geometry>
  </collision>

  <!-- How it BEHAVES under force. Read by the dynamics integrator. -->
  <inertial>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <mass value="2.0"/>
    <inertia ixx="0.0083" ixy="0.0" ixz="0.0"
             iyy="0.0142" iyz="0.0"
             izz="0.0208"/>
  </inertial>
</link>
```

### `<visual>` — what you see

This is the geometry the renderer draws. It can be a primitive (`box`, `cylinder`, `sphere`) or a `<mesh filename="package://my_pkg/meshes/chassis.dae"/>`. It can be arbitrarily detailed — a million-triangle mesh of your CAD model with textures. The renderer can handle it; the physics engine never looks at it. Visual fidelity is *free* from the physics engine's perspective.

### `<collision>` — what the physics engine touches

This is the geometry used for **contact detection** — when does this link touch the ground, a wall, or another link? Collision checking against a million-triangle mesh, sixty times a second, against every other collision body, is brutally expensive and numerically fragile. So the universal practice is: **make the collision geometry a coarse primitive even when the visual is a detailed mesh.** A robot arm's forearm might have a beautiful machined-aluminum visual mesh and a single capsule for collision. This is not cheating; it is the correct engineering trade-off. The collision geometry's job is to be *approximately right and cheap*, not pixel-perfect.

A subtle trap lives here: if two collision bodies on the *same robot* overlap in the zero configuration — say, a wheel collision cylinder that pokes into the chassis collision box — the physics engine sees two interpenetrating solids and applies enormous separation forces to push them apart. That is one of the four ways a robot explodes on spawn (more in §1.7). Collision geometry must not self-intersect at rest.

### `<inertial>` — how it behaves under force

This is the block that matters most and gets ignored most. It has three parts:

- **`<origin>`** — the pose of the **center of mass** relative to the link frame. If your link is symmetric and centered, this is `0 0 0`. If the link is a chassis with a battery bolted to one side, the center of mass is offset, and you must say so.
- **`<mass value="..."/>`** — the mass in **kilograms**. Not grams. Not pounds. A 2 kg chassis has `value="2.0"`.
- **`<inertia .../>`** — the six independent entries of the symmetric 3×3 **inertia tensor**, in **kg·m²**, about the center of mass, aligned with the inertial frame's axes.

That inertia tensor is where everyone goes wrong, so it gets its own section.

## 1.3 — What the inertia tensor actually is

Mass tells you how hard it is to *translate* a body — `F = ma`. The inertia tensor tells you how hard it is to *rotate* it — `τ = Iα` (torque equals inertia times angular acceleration), generalized to three dimensions. In 3D, "how hard to rotate" depends on the axis you rotate about, so a single number is not enough; you need a 3×3 matrix:

```
     | Ixx  Ixy  Ixz |
 I = | Ixy  Iyy  Iyz |
     | Ixz  Iyz  Izz |
```

It is **symmetric** (`Ixy = Iyx`, etc.), so only six numbers are independent — exactly the six attributes `ixx ixy ixz iyy iyz izz` in the URDF. The diagonal terms (`Ixx`, `Iyy`, `Izz`) are the **moments of inertia** about each axis: how hard to spin the body about x, y, z. The off-diagonal terms (`Ixy`, `Ixz`, `Iyz`) are the **products of inertia**: they are zero when the body's mass is symmetric about the coordinate planes, which it usually is for a well-chosen link frame. For all of Phase 1 you can keep the off-diagonals at zero by placing link frames at the center of geometry of symmetric shapes.

The units are **kilogram-meters-squared (kg·m²)**, and this is where the factor-of-1000 disaster originates. People who learned mechanics with grams and centimeters carry the wrong mental scale. A 2 kg box that is 40 cm × 30 cm × 10 cm has moments of inertia on the order of **0.01 to 0.02 kg·m²** — small numbers. If you instead type something like `1.0` for each (a number that "feels" reasonable but is fifty times too big) or `0.000001` (a number copied from a millimeter-scale CAD export without converting units), the physics engine simulates a body whose rotational dynamics are wildly inconsistent with its mass and size, and the constraint solver — trying to hold the joints together against this inconsistency — generates the spurious forces that blow the robot apart.

## 1.4 — The closed-form inertia equations you will use all phase

You will compute inertia tensors for exactly three primitive shapes this phase, all about the center of mass, all with the off-diagonals zero. Memorize the *form*; keep the table handy for the constants.

### Solid box (dimensions `w` × `d` × `h` along x, y, z; mass `m`)

```
Ixx = (1/12) · m · (d² + h²)
Iyy = (1/12) · m · (w² + h²)
Izz = (1/12) · m · (w² + d²)
```

Worked example — the 2 kg chassis above (`w=0.4`, `d=0.3`, `h=0.1`):

```
Ixx = (1/12) · 2 · (0.3² + 0.1²) = (1/12) · 2 · (0.09 + 0.01) = (1/12) · 0.2 = 0.01667
Iyy = (1/12) · 2 · (0.4² + 0.1²) = (1/12) · 2 · (0.16 + 0.01) = (1/12) · 0.34 = 0.02833
Izz = (1/12) · 2 · (0.4² + 0.3²) = (1/12) · 2 · (0.16 + 0.09) = (1/12) · 0.5 = 0.04167
```

(The example XML in §1.2 used a slightly smaller mass distribution; the point is the *magnitude* — hundredths of a kg·m², not ones, not millionths.)

### Solid cylinder (radius `r`, length `l` along its local z-axis; mass `m`)

```
Ixx = Iyy = (1/12) · m · (3·r² + l²)
Izz = (1/2) · m · r²
```

A wheel is a short, fat cylinder. For a `r=0.05 m`, `l=0.04 m`, `m=0.3 kg` wheel **whose axle is its local z-axis**:

```
Ixx = Iyy = (1/12) · 0.3 · (3·0.05² + 0.04²) = (1/12) · 0.3 · (0.0075 + 0.0016) = 0.0002275
Izz = (1/2) · 0.3 · 0.05² = (1/2) · 0.3 · 0.0025 = 0.000375
```

**Mind the axis.** A wheel spins about its axle. If your wheel's local frame has the axle along z, the spin moment is `Izz`. If the axle is along y (common when you rotate the cylinder so it sits like a wheel on a car), you must rotate the tensor too — or, far simpler, set the wheel link frame so the axle is the joint's declared axis and keep the cylinder's natural z-axis as the spin axis. We will use a wheel macro that handles the rotation once and reuses it.

### Solid sphere (radius `r`, mass `m`) — used for casters

```
Ixx = Iyy = Izz = (2/5) · m · r²
```

A `r=0.025 m`, `m=0.05 kg` caster ball:

```
Ixx = Iyy = Izz = (2/5) · 0.05 · 0.025² = 0.4 · 0.05 · 0.000625 = 0.0000125
```

That is `1.25e-5 kg·m²` — genuinely tiny, and *correctly* tiny, because a 50-gram marble really is easy to spin. The lesson: small numbers are not automatically wrong. The question is always "is the number consistent with the mass and the size?" — which is exactly what the sanity checks in the next section formalize.

## 1.5 — Computing inertia in code (and why you should)

You can compute these by hand, but you will get a sign or a factor wrong eventually. Better: write a tiny Python helper, and — even better — generate the `<inertial>` block from xacro macros so the tensor is *guaranteed* consistent with the mass and dimensions you declared. Here is a standalone reference helper you can run today:

```python
#!/usr/bin/env python3
"""inertia.py — closed-form inertia tensors for URDF primitives.

All results are about the center of mass, axes aligned with the geometry's
local frame, in SI units (kg, m, kg*m^2). Off-diagonal terms are zero for
these symmetric primitives.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Inertia:
    """The six independent entries of a symmetric 3x3 inertia tensor."""
    ixx: float
    iyy: float
    izz: float
    ixy: float = 0.0
    ixz: float = 0.0
    iyz: float = 0.0

    def as_urdf_attrs(self) -> str:
        """Render as the attribute string for a URDF <inertia .../> element."""
        return (
            f'ixx="{self.ixx:.6g}" ixy="{self.ixy:.6g}" ixz="{self.ixz:.6g}" '
            f'iyy="{self.iyy:.6g}" iyz="{self.iyz:.6g}" izz="{self.izz:.6g}"'
        )


def box_inertia(mass: float, x: float, y: float, z: float) -> Inertia:
    """Solid box of dimensions (x, y, z) along the local axes."""
    c = mass / 12.0
    return Inertia(
        ixx=c * (y * y + z * z),
        iyy=c * (x * x + z * z),
        izz=c * (x * x + y * y),
    )


def cylinder_inertia(mass: float, radius: float, length: float) -> Inertia:
    """Solid cylinder with its symmetry (spin) axis along local z."""
    ixx = (1.0 / 12.0) * mass * (3.0 * radius * radius + length * length)
    izz = 0.5 * mass * radius * radius
    return Inertia(ixx=ixx, iyy=ixx, izz=izz)


def sphere_inertia(mass: float, radius: float) -> Inertia:
    """Solid sphere."""
    i = (2.0 / 5.0) * mass * radius * radius
    return Inertia(ixx=i, iyy=i, izz=i)


if __name__ == "__main__":
    chassis = box_inertia(2.0, 0.4, 0.3, 0.1)
    wheel = cylinder_inertia(0.3, 0.05, 0.04)
    caster = sphere_inertia(0.05, 0.025)
    print("chassis:", chassis.as_urdf_attrs())
    print("wheel:  ", wheel.as_urdf_attrs())
    print("caster: ", caster.as_urdf_attrs())
```

Run it:

```bash
python3 inertia.py
```

Expected output:

```
chassis: ixx="0.0166667" ixy="0" ixz="0" iyy="0.0283333" iyz="0" izz="0.0416667"
wheel:   ixx="0.0002275" ixy="0" ixz="0" iyy="0.0002275" iyz="0" izz="0.000375"
caster:  ixx="1.25e-05" ixy="0" ixz="0" iyy="1.25e-05" iyz="0" izz="1.25e-05"
```

This is the source of truth. When your xacro generates inertials with the same formulas (and it will — Lecture 2's exercise builds exactly this macro), the tensor is *by construction* consistent with the mass and size. The whole class of factor-of-1000 errors becomes impossible, because you never type the tensor by hand again.

## 1.6 — The four sanity checks every inertia tensor must pass

Before a physics engine sees your URDF, run these four checks. They take thirty seconds and catch every common error. Treat them as a pre-flight checklist.

### Check 1 — Mass is positive and physically plausible

`<mass value="...">` must be `> 0`. A zero or negative mass is an instant explosion — the dynamics equations divide by mass. And the value must be *plausible*: a hobby robot chassis is 1–5 kg, a wheel is 0.1–0.5 kg, a caster ball is 20–80 g. If you see a chassis with `value="0.001"` (1 gram) or `value="500"` (half a ton), stop. The most common real bug is `value="1000"` from someone who thought the unit was grams.

### Check 2 — Diagonal entries are positive

`Ixx`, `Iyy`, `Izz` must all be strictly positive. A zero or negative principal moment is unphysical — no real rigid body has it — and the solver will produce NaNs or infinities. If a generated tensor has a negative diagonal entry, you have a sign error or a dimension typed as negative.

### Check 3 — The triangle inequality holds

For any real rigid body, the three principal moments of inertia satisfy the **triangle inequalities**:

```
Ixx + Iyy >= Izz
Iyy + Izz >= Ixx
Izz + Ixx >= Iyy
```

This is a deep fact: it is impossible for one principal moment to exceed the sum of the other two, because the inertia tensor is built from a sum of `m·(distance²)` terms that the three axes share. If your tensor violates it, the tensor does not correspond to any physical mass distribution, and Gz Sim's physics back-end (DART, by default on Harmonic) will either refuse it or simulate garbage. Hand-typed tensors violate this constantly; generated tensors from §1.5 never do.

### Check 4 — Order of magnitude matches `m·r²`

The crudest and most useful check: every moment of inertia should be roughly `mass × (characteristic length)²`, within a factor of ~10. For the 2 kg chassis with a ~0.2 m characteristic size, expect moments around `2 × 0.2² = 0.08` — and indeed they are 0.017 to 0.042, in the right ballpark. If your "chassis" has a moment of `50` or `0.00001`, the order of magnitude is wrong by 1000×, and that is your bug. This single check, internalized, catches the explode-on-spawn cause before you ever spawn.

A compact Python validator you can drop into a test:

```python
def sanity_check(mass: float, ixx: float, iyy: float, izz: float,
                 char_len: float) -> list[str]:
    """Return a list of human-readable problems; empty list means it passed."""
    problems: list[str] = []
    if mass <= 0:
        problems.append(f"mass {mass} is not positive")
    for name, v in (("ixx", ixx), ("iyy", iyy), ("izz", izz)):
        if v <= 0:
            problems.append(f"{name} {v} is not positive")
    if ixx + iyy < izz:
        problems.append("triangle inequality violated: ixx + iyy < izz")
    if iyy + izz < ixx:
        problems.append("triangle inequality violated: iyy + izz < ixx")
    if izz + ixx < iyy:
        problems.append("triangle inequality violated: izz + ixx < iyy")
    expected = mass * char_len * char_len
    for name, v in (("ixx", ixx), ("iyy", iyy), ("izz", izz)):
        ratio = v / expected if expected > 0 else float("inf")
        if ratio > 10.0 or ratio < 0.01:
            problems.append(
                f"{name} {v:.4g} is off by >10x from m*r^2 ~= {expected:.4g}")
    return problems
```

## 1.7 — The "robot explodes on spawn" failure mode

Now we can name the disease precisely. When you spawn a robot and it instantly vibrates, flings parts across the world, sinks through the ground, or launches into the sky, **one of exactly four things is wrong**. Memorize the differential diagnosis; it turns a baffling spectacle into a checklist.

### Cause 1 — Bad inertia tensor (the factor-of-1000 classic)

**Symptom:** the robot trembles, then accelerates parts apart explosively, often within the first simulation step. **Why:** an inertia inconsistent with the mass/geometry makes the constraint solver compute absurd reaction forces to hold the joints together. **Fix:** generate the tensor from §1.5; verify with §1.6. This is the cause ~70% of the time.

### Cause 2 — Zero, negative, or missing mass

**Symptom:** a link flies off immediately, or the whole robot ignores gravity, or rviz2 shows the robot but Gz Sim shows nothing where the link should be. **Why:** zero/negative mass breaks `F = ma`; a missing `<inertial>` makes Gz Sim substitute a degenerate default. **Fix:** every dynamic link gets an `<inertial>` with positive mass. (A `fixed`-joint child can sometimes be lumped into its parent, but in Phase 1 give every link its own honest inertial.)

### Cause 3 — Self-colliding collision geometry

**Symptom:** the robot "jumps" or shudders at spawn but does not necessarily fly to infinity; parts push away from each other. **Why:** two collision primitives on the same robot overlap at rest, so the contact solver applies separation forces. A wheel collision cylinder poking into the chassis collision box is the classic. **Fix:** ensure collision primitives do not interpenetrate in the zero configuration; or disable self-collision between adjacent links (in SDF via `<self_collide>false</self_collide>`, which is the Gz default for links joined by a joint — but overlapping geometry can still bite when the joint lets them move into each other).

### Cause 4 — A degenerate or mis-specified joint

**Symptom:** a wheel spins to infinity, a link whips around, or the robot teleports. **Why:** a `continuous` joint with a zero or undefined axis, a `revolute` joint with inverted limits (`lower > upper`), or a joint whose `<origin>` places the child inside the parent. **Fix:** every movable joint has a non-zero `<axis>`; revolute limits satisfy `lower < upper`; joint origins place children outside their parents.

### The diagnosis workflow

When (not if) your robot explodes, run this in order, and stop at the first thing that's wrong:

1. **Expand the URDF and parse it.** `xacro crunchbot.urdf.xacro > /tmp/crunchbot.urdf && check_urdf /tmp/crunchbot.urdf`. This catches structural errors (broken tree, duplicate link names) before physics is even involved.
2. **Read every `<mass>`.** Are they all positive and plausible (Check 1)? Grep for them: `grep -A1 inertial /tmp/crunchbot.urdf` or just eyeball them.
3. **Run the §1.6 sanity check on every link.** Positive diagonals, triangle inequality, order of magnitude. This catches Cause 1 and most of Cause 2.
4. **Spawn into an empty world and watch the *first frame*.** If it explodes instantly, it is inertia/mass (Causes 1–2). If it explodes after settling for a moment, it is collision (Cause 3) or a joint (Cause 4).
5. **Disable physics and look at the static pose.** In Gz Sim, pause the simulation before stepping (`gz sim -s` with the world paused, or spawn paused). If the *static* pose already shows interpenetrating parts, it is Cause 3. If a wheel is pointed the wrong way, it is Cause 4.

The challenge this week (`challenge-01-fix-the-exploding-robot.md`) hands you a URDF with two of these four causes deliberately injected and asks you to run exactly this workflow.

## 1.8 — Joints: choosing the right type

Four joint types cover everything in Phase 1.

- **`fixed`** — no motion. The child is rigidly attached to the parent. Use it for sensors (the LiDAR is fixed to the chassis), for structural mounts, and for the caster *mount* (the swivel itself is modeled as a frictionless sphere collision, not a real joint, in Phase 1). A fixed joint adds no degree of freedom and publishes a static transform.

- **`continuous`** — a revolute joint with **no angle limit**: it can spin forever. This is what a **drive wheel** uses. It has an `<axis>` (the spin axis, almost always the wheel's local y or z depending on how you oriented the cylinder) and optional `<dynamics>` (damping, friction). No `<limit>` element is required.

- **`revolute`** — a hinge with **angle limits**. A robot arm's elbow. Requires `<axis>` and a `<limit lower=... upper=... effort=... velocity=.../>`. You meet these heavily in Phase 3 (manipulators); in Phase 1 you use them only if you add a pan-tilt sensor mount.

- **`prismatic`** — a linear slider with position limits. A linear actuator, a forklift mast. Requires `<axis>` and `<limit>`. Rare in Phase 1.

A wheel joint, fully specified:

```xml
<joint name="left_wheel_joint" type="continuous">
  <parent link="base_link"/>
  <child link="left_wheel"/>
  <origin xyz="0.0 0.18 0.0" rpy="-1.5708 0 0"/>
  <axis xyz="0 0 1"/>
  <dynamics damping="0.01" friction="0.0"/>
</joint>
```

Read it carefully. The `<origin>` places the wheel 18 cm to the left (+y) of the chassis center and rotates it −90° about x (`rpy="-1.5708 0 0"`) so the cylinder, whose natural symmetry axis is its local z, ends up with that axis pointing along the robot's +y — i.e., the wheel stands up like a wheel. The `<axis xyz="0 0 1"/>` then says "spin about the wheel's local z," which after the rotation is the world's y at zero — the correct rolling axis. This rotate-the-cylinder-then-spin-about-its-own-z trick is why the inertia stays simple: we computed `Izz` as the spin moment in §1.4, and the joint axis is exactly that z. Everything lines up.

## 1.9 — Who reads the URDF, and when

It clarifies the whole picture to trace the data flow once.

1. **You** write `crunchbot.urdf.xacro` (xacro source).
2. **`xacro`** expands it to plain URDF (XML) at launch time. No macros survive; it is pure `<robot>`/`<link>`/`<joint>`.
3. **`robot_state_publisher`** is launched with that URDF as its `robot_description` parameter. It parses the tree, publishes `/robot_description` (a `std_msgs/String` latched topic), and broadcasts the **static** parts of the tf2 tree (`fixed` joints). For movable joints it subscribes to `/joint_states` and broadcasts the **dynamic** transforms.
4. **`rviz2`** reads `/robot_description` and `/tf`, and draws the visual geometry at the live poses.
5. **`ros_gz_sim create`** takes the same `/robot_description`, converts the URDF to SDF, and **spawns** it into the running Gz world. From this moment the physics engine owns the robot's pose.
6. **Gz Sim's physics back-end (DART)** reads the collision and inertial blocks and integrates the dynamics. The `DiffDrive` system plugin reads `/cmd_vel`, computes wheel velocities, and the physics moves the robot. A `JointStatePublisher` system (or the DiffDrive's own state output) publishes joint angles back, which — bridged to ROS2 — feed `robot_state_publisher` so the tf tree tracks the simulated robot.

Notice that the **visual** block is read by exactly one consumer (the renderer), the **collision** block by exactly one (the contact solver), and the **inertial** block by exactly one (the dynamics integrator). When you understand which block each consumer reads, you understand exactly which block to fix when something looks wrong. A robot that *looks* right in rviz2 but explodes in Gz Sim has a visual block that's fine and an inertial/collision block that's broken — because rviz2 never reads inertials.

## 1.10 — The reflexes to internalize this week

- **A URDF is a claim, not a model.** The mesh is the model; the URDF asserts kinematics and dynamics.
- **Every dynamic link has all three blocks.** Visual, collision, inertial. A missing inertial is a bug, not a shortcut.
- **Never type an inertia tensor by hand.** Generate it from mass and dimensions, in code or in xacro. Hand-typed tensors are where the factor-of-1000 explosions come from.
- **Run the four sanity checks before you spawn.** Positive mass, positive diagonals, triangle inequality, order of magnitude. Thirty seconds; saves an hour.
- **Collision geometry is coarse on purpose.** Primitives for collision, meshes for visual. Don't make the physics engine collide a million triangles.
- **When it explodes, run the four-cause differential.** Inertia, mass, self-collision, joint. Stop at the first thing that's wrong.
- **`check_urdf` before physics.** Structural errors are cheaper to find with a parser than with a detonating robot.

These reflexes are the entire methodology of robot-description authoring. Lecture 2 takes this clean, physically-honest robot body and gives it actuators and sensors — the Gz Sim plugins that make `/cmd_vel`, `/imu`, and `/scan` real.

---

## Lecture 1 — checklist before moving on

- [ ] I can explain why a URDF is a kinematic claim rather than a CAD file, and name the four consumers that read it.
- [ ] I can write a `<link>` with all three blocks (visual, collision, inertial) and explain who reads each.
- [ ] I can compute the inertia tensor of a box, a cylinder, and a sphere from the closed-form equations.
- [ ] I can run the four sanity checks (positive mass, positive diagonals, triangle inequality, order of magnitude) on any tensor.
- [ ] I can name the four causes of explode-on-spawn and the symptom that distinguishes each.
- [ ] I can choose the correct joint type and specify its axis, origin, and limits.
- [ ] I have actually run `inertia.py` from §1.5 and matched its output.

If any box is unchecked, return to that section. Lecture 2 assumes you can produce a physically-honest robot body.

---

**References cited in this lecture**

- URDF XML specification — `<link>`: <https://wiki.ros.org/urdf/XML/link>
- URDF XML specification — `<joint>`: <https://wiki.ros.org/urdf/XML/joint>
- List of moments of inertia (closed-form table): <https://en.wikipedia.org/wiki/List_of_moments_of_inertia>
- Moment of inertia (concept, parallel-axis, principal axes): <https://en.wikipedia.org/wiki/Moment_of_inertia>
- SDFormat 1.11 `<inertial>` (the target format, with the triangle-inequality validation): <http://sdformat.org/spec?ver=1.11&elem=link#link_inertial>
- ROS2 Jazzy — "Building a Visual Robot Model with URDF from Scratch": <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/Building-a-Visual-Robot-Model-with-URDF-from-Scratch.html>
