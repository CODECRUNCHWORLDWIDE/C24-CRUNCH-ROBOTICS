# Challenge 1 — Fix the Exploding Robot

**Estimated time:** ~2 hours.

A teammate pushed a branch with a new sensor mast on the team's diff-drive base and asked you to "just spawn it and confirm the LiDAR works." You spawn it. The instant the simulation starts, the robot detonates: the mast launches into the skybox, a wheel spins to infinity, the chassis vibrates through the ground plane, and `rviz2` shows a twitching smear. The teammate is on PTO. The demo is tomorrow.

This is the most realistic thing you do all week. You will treat the broken description below exactly like an on-call ticket: reproduce the failure, form a hypothesis from the symptom, test it against the four-cause differential from **Lecture 1 §1.7**, fix one fault at a time, and write up what you found. "It spawns now" is *not* the bar. "It spawns, sits perfectly still, drives smoothly, and I can name every fault I fixed and the sanity check that would have caught it" is the bar.

---

## The broken description

Create a package `exploder` (or drop these files into a scratch workspace) and save the following as `urdf/exploder.urdf` — this is plain URDF, not xacro, so there are no macros hiding the bugs. Read it; do **not** fix it yet. Reproduce the failure first.

```xml
<?xml version="1.0"?>
<robot name="exploder">

  <!-- ===== Chassis ===== -->
  <link name="base_link">
    <visual>
      <geometry><box size="0.4 0.3 0.1"/></geometry>
      <material name="red"><color rgba="0.86 0.15 0.15 1.0"/></material>
    </visual>
    <collision>
      <geometry><box size="0.4 0.3 0.1"/></geometry>
    </collision>
    <inertial>
      <mass value="2.0"/>
      <!-- BUG A: this tensor was hand-typed in g*mm^2 and never converted. -->
      <inertia ixx="16666.7" ixy="0.0" ixz="0.0"
               iyy="28333.3" iyz="0.0"
               izz="41666.7"/>
    </inertial>
  </link>

  <!-- ===== Left wheel ===== -->
  <link name="left_wheel">
    <visual>
      <geometry><cylinder radius="0.05" length="0.04"/></geometry>
    </visual>
    <collision>
      <geometry><cylinder radius="0.05" length="0.04"/></geometry>
    </collision>
    <inertial>
      <mass value="0.3"/>
      <inertia ixx="0.0002275" ixy="0.0" ixz="0.0"
               iyy="0.0002275" iyz="0.0"
               izz="0.000375"/>
    </inertial>
  </link>
  <joint name="left_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child link="left_wheel"/>
    <origin xyz="0 0.18 0" rpy="-1.5707963 0 0"/>
    <!-- BUG B: zero axis. A continuous joint with no axis is degenerate. -->
    <axis xyz="0 0 0"/>
  </joint>

  <!-- ===== Right wheel ===== -->
  <link name="right_wheel">
    <visual>
      <geometry><cylinder radius="0.05" length="0.04"/></geometry>
    </visual>
    <collision>
      <geometry><cylinder radius="0.05" length="0.04"/></geometry>
    </collision>
    <inertial>
      <mass value="0.3"/>
      <inertia ixx="0.0002275" ixy="0.0" ixz="0.0"
               iyy="0.0002275" iyz="0.0"
               izz="0.000375"/>
    </inertial>
  </link>
  <joint name="right_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child link="right_wheel"/>
    <origin xyz="0 -0.18 0" rpy="-1.5707963 0 0"/>
    <axis xyz="0 0 1"/>
  </joint>

  <!-- ===== Caster ===== -->
  <link name="front_caster">
    <visual>
      <geometry><sphere radius="0.025"/></geometry>
    </visual>
    <collision>
      <geometry><sphere radius="0.025"/></geometry>
    </collision>
    <inertial>
      <mass value="0.05"/>
      <inertia ixx="1.25e-5" ixy="0.0" ixz="0.0"
               iyy="1.25e-5" iyz="0.0"
               izz="1.25e-5"/>
    </inertial>
  </link>
  <joint name="front_caster_joint" type="fixed">
    <parent link="base_link"/>
    <child link="front_caster"/>
    <!-- BUG C: caster mounted at z=0, so it sits half-inside the chassis box
         (chassis bottom is at z=-0.05; this sphere center is at z=0). -->
    <origin xyz="0.175 0 0" rpy="0 0 0"/>
  </joint>

  <!-- ===== Sensor mast ===== -->
  <link name="mast">
    <visual>
      <geometry><cylinder radius="0.02" length="0.5"/></geometry>
    </visual>
    <collision>
      <geometry><cylinder radius="0.02" length="0.5"/></geometry>
    </collision>
    <inertial>
      <!-- BUG D: negative mass. Someone fat-fingered a minus sign. -->
      <mass value="-0.4"/>
      <inertia ixx="0.0084" ixy="0.0" ixz="0.0"
               iyy="0.0084" iyz="0.0"
               izz="0.00008"/>
    </inertial>
  </link>
  <joint name="mast_joint" type="fixed">
    <parent link="base_link"/>
    <child link="mast"/>
    <origin xyz="0 0 0.3" rpy="0 0 0"/>
  </joint>

</robot>
```

There are **four** deliberately injected faults, spanning all four causes from the §1.7 differential. Two are inertia/mass bugs (Causes 1 and 2), one is a self-collision bug (Cause 3), and one is a degenerate-joint bug (Cause 4). Your job is to find all four — not just the first one that makes it stop exploding.

---

## Step 1 — Reproduce the failure (do this before touching anything)

```bash
# Parse it first — does it even survive the URDF parser?
check_urdf urdf/exploder.urdf

# Spawn it into an empty world and WATCH THE FIRST FRAME.
ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-r -v 4 empty.sdf" &
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$(cat urdf/exploder.urdf)" \
             -p use_sim_time:=true &
ros2 run ros_gz_sim create -topic /robot_description -name exploder -z 0.2
```

Watch carefully and write down the symptom *before* you theorize:

- Does it explode on the very first step (instant) or after settling for a moment?
- Which part moves first — the mast, a wheel, the whole chassis?
- Does `check_urdf` itself complain, or does it parse clean and only physics fail?

Per §1.7: instant explosion points at inertia/mass (Causes 1–2); explosion after a beat points at collision (Cause 3) or a joint (Cause 4). You have a mix, so you will see a mix.

---

## Step 2 — Run the diagnosis workflow in order

Do **not** start randomly editing numbers — that is how you turn four bugs into seven. Run the §1.7 workflow top to bottom.

1. **Parse.** `check_urdf urdf/exploder.urdf`. It parses clean (the bugs are physical, not structural) — note that a clean parse does *not* mean a clean spawn. This is the lesson of the week.
2. **Read every `<mass>`.** Are they all positive and plausible (Check 1)? One of them is not. Find it.
3. **Run the §1.6 sanity check on every link.** Positive diagonals, triangle inequality, order of magnitude (`m·r²`). One chassis tensor is off by a factor of a million. The validator below makes this mechanical.
4. **Inspect every movable joint's `<axis>`.** A `continuous` joint with `axis="0 0 0"` is degenerate (Cause 4). Find it.
5. **Pause physics and look at the static pose** for interpenetration (Cause 3). The caster is buried in the chassis.

Use this validator — it is the §1.6 check, wired to parse the URDF directly so you do not eyeball numbers:

```python
#!/usr/bin/env python3
"""validate_inertials.py — run the Lecture 1 §1.6 checks on every link."""
import sys
import xml.etree.ElementTree as ET


def char_len_of_link(link: ET.Element) -> float:
    """Crude characteristic length from the first collision/visual geometry."""
    geom = link.find(".//geometry")
    if geom is None:
        return 0.1
    box = geom.find("box")
    if box is not None:
        dims = [float(v) for v in box.get("size").split()]
        return max(dims) / 2.0
    cyl = geom.find("cylinder")
    if cyl is not None:
        return max(float(cyl.get("radius")), float(cyl.get("length")) / 2.0)
    sph = geom.find("sphere")
    if sph is not None:
        return float(sph.get("radius"))
    return 0.1


def check_link(link: ET.Element) -> list[str]:
    name = link.get("name")
    inertial = link.find("inertial")
    if inertial is None:
        return [f"[{name}] no <inertial> — Gz will substitute a degenerate default (Cause 2)"]
    mass = float(inertial.find("mass").get("value"))
    i = inertial.find("inertia")
    ixx, iyy, izz = (float(i.get(k)) for k in ("ixx", "iyy", "izz"))
    problems: list[str] = []
    # Check 1 — positive plausible mass.
    if mass <= 0:
        problems.append(f"[{name}] mass {mass} is not positive (Cause 2)")
    elif not (0.005 <= mass <= 50.0):
        problems.append(f"[{name}] mass {mass} kg is implausible for a hobby base")
    # Check 2 — positive diagonals.
    for k, v in (("ixx", ixx), ("iyy", iyy), ("izz", izz)):
        if v <= 0:
            problems.append(f"[{name}] {k}={v} is not positive")
    # Check 3 — triangle inequality.
    if ixx + iyy < izz or iyy + izz < ixx or izz + ixx < iyy:
        problems.append(f"[{name}] inertia triangle inequality violated")
    # Check 4 — order of magnitude vs m*r^2.
    cl = char_len_of_link(link)
    expected = abs(mass) * cl * cl
    for k, v in (("ixx", ixx), ("iyy", iyy), ("izz", izz)):
        if expected > 0:
            ratio = v / expected
            if ratio > 10.0 or ratio < 0.01:
                problems.append(
                    f"[{name}] {k}={v:.4g} is off by >10x from m*r^2 ~= {expected:.4g} "
                    f"(ratio {ratio:.3g}) — Cause 1")
    return problems


def main() -> int:
    tree = ET.parse(sys.argv[1])
    found = False
    for link in tree.getroot().findall("link"):
        for problem in check_link(link):
            print(problem)
            found = True
    if not found:
        print("All inertials pass the four sanity checks.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

Run it on the broken file:

```bash
python3 validate_inertials.py urdf/exploder.urdf
```

Expected output (before you fix anything):

```
[base_link] ixx=1.667e+04 is off by >10x from m*r^2 ~= 0.08 (ratio 2.08e+05) — Cause 1
[base_link] iyy=2.833e+04 is off by >10x from m*r^2 ~= 0.08 (ratio 3.54e+05) — Cause 1
[base_link] izz=4.167e+04 is off by >10x from m*r^2 ~= 0.08 (ratio 5.21e+05) — Cause 1
[mast] mass -0.4 is not positive (Cause 2)
```

The validator catches the two *inertial* bugs (A and D). It does **not** catch the degenerate axis (B) or the self-collision (C) — those are not inertia properties, and that is the point: the inertia validator is one tool of four. You still owe the axis inspection and the static-pose look.

---

## Step 3 — Fix one fault at a time

Fix and re-test after **each** change so you know which fix did what. The four faults and their correct repairs:

- **Bug A — chassis inertia in `g·mm²` instead of `kg·m²`.** The numbers `16666.7 / 28333.3 / 41666.7` are exactly the correct tensor multiplied by `10⁶` (1 kg = 1000 g, 1 m = 1000 mm, and inertia scales as `mass·length²`, so the factor is `1000·1000² = 10⁹`... but the original was typed in g·mm² which over-states by `10⁶` relative to kg·m² — work the unit algebra yourself in the writeup). The correct values are the Lecture 1 §1.4 chassis tensor: `ixx=0.0166667`, `iyy=0.0283333`, `izz=0.0416667`.
- **Bug B — `left_wheel_joint` has `axis="0 0 0"`.** A continuous joint must spin about a real axis. Set it to `axis="0 0 1"` to match the right wheel (the cylinder's local z, which after the `-π/2` roll is the rolling axis).
- **Bug C — `front_caster` mounted at `z=0`, buried in the chassis.** The chassis box half-height is `0.05`, so its bottom face is at `z=-0.05`. A caster of radius `0.025` whose bottom should touch the wheel contact plane (`z=-wheel_radius=-0.05`) must have its center at `z = -(0.05 - 0.025) = -0.025`. Set `origin xyz="0.175 0 -0.025"`. (Equivalently, the §Exercise-1 caster formula `-(wheel_radius - caster_radius)`.)
- **Bug D — mast `mass=-0.4`.** Make it positive: `mass="0.4"`. While you are there, sanity-check the mast tensor: a `r=0.02`, `l=0.5`, `m=0.4` cylinder has `ixx=iyy=(1/12)·0.4·(3·0.02²+0.5²)≈0.00837` and `izz=0.5·0.4·0.02²=0.00008` — the listed values are correct, only the mass sign was wrong.

After all four fixes, re-run the validator (it should report all-pass) and re-spawn. The robot must sit dead still on the ground plane.

---

## Step 4 — Confirm it drives

A robot that spawns still is necessary but not sufficient. Wire the DiffDrive plugin (Lecture 2 §2.3) — note the original `exploder.urdf` has no actuator — and confirm it drives smoothly:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: 'base_link'}, twist: {linear: {x: 0.2}, angular: {z: 0.3}}}"
```

If it glides in a smooth arc, you are done. If it still shudders, you missed a fault — go back to Step 2.

---

## Acceptance criteria

You can mark this challenge done when **all** of the following hold:

- [ ] You reproduced the explosion and recorded the symptom **before** editing anything.
- [ ] `validate_inertials.py` reports all-pass on your repaired URDF.
- [ ] You identified and fixed **all four** faults — not just enough to stop the explosion.
- [ ] The robot spawns and **sits perfectly still** with no command sent (`/odom` position constant).
- [ ] The robot **drives smoothly** under `/cmd_vel` with the DiffDrive plugin wired in.
- [ ] Your writeup maps each of the four faults to one of the four §1.7 causes, names the §1.6 sanity check that would have caught it (or explains why none would, as for the self-collision and degenerate-axis bugs), and shows the unit algebra for Bug A.

---

## The writeup (half the grade)

Submit a `DIAGNOSIS.md` (1–2 pages) structured like an incident postmortem:

1. **Symptom** — what you observed on spawn, in plain language, before any hypothesis.
2. **Differential** — the four §1.7 causes, and which symptom pointed at which.
3. **Findings** — the four faults, each tied to a cause, with the offending line.
4. **The check that would have caught it** — for each fault, the §1.6 check (or, for Bugs B and C, the workflow step: axis inspection / static-pose look). Be honest where the inertia validator was blind.
5. **The unit algebra for Bug A** — show, with units, why `16666.7 g·mm²` became `0.0166667 kg·m²` (the conversion factor and where it comes from).
6. **Verification** — the validator output and a screenshot/recording of the robot spawning still and driving.

Submit your repaired `exploder.urdf`, your `DIAGNOSIS.md`, and a short screen recording (or a sequence of screenshots) showing the robot spawning cleanly, sitting still, and driving.

---

## Stretch

- **Add a fifth fault yourself** — a self-colliding wheel (move a wheel `<origin>` so its collision cylinder overlaps the chassis box at rest) — and confirm the validator stays silent (it does not check collision geometry) while the spawn shudders. This proves *why* the four-tool workflow exists: no single tool catches everything.
- **Wrap `validate_inertials.py` as a `colcon test`** so a broken inertial fails CI before it ever reaches a simulator. This is exactly how a production robotics shop keeps explode-on-spawn out of `main`.
- **Render the inertia ellipsoids** in rviz2 (the InertiaDisplay) on the broken vs. fixed robot and screenshot the difference. A chassis ellipsoid the size of a building is Bug A made visible.

---

*This challenge maps to the homework's "diagnose a broken description" deliverable. Keep your `DIAGNOSIS.md` — you will reference its sanity-check list in the mini-project's `README`.*
