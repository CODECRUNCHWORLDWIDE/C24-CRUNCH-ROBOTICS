# Exercise 1 — Build the Diff-Drive Body in xacro

**Goal:** Author a complete differential-drive robot body — a chassis, two driven wheels, and two casters — in xacro, with correct visual, collision, and inertial blocks. Parse it with `check_urdf`, expand it with `xacro`, and visualize it in rviz2. No physics yet; that comes in Exercise 3. This exercise is about a clean, well-formed, physically-honest *description*.

**Estimated time:** 90 minutes.

---

## Setup

Create a description package inside your workspace:

```bash
cd ~/crunch_ws/src
ros2 pkg create --build-type ament_cmake crunchbot_description
cd crunchbot_description
mkdir -p urdf config launch
```

Edit `CMakeLists.txt` to install the directories (add this before `ament_package()`):

```cmake
install(DIRECTORY urdf config launch
        DESTINATION share/${PROJECT_NAME})
```

---

## Step 1 — Properties and the inertia macros

Create `urdf/inertials.xacro`. This file holds reusable macros that *generate* inertial blocks from mass and dimensions, so you never type a tensor by hand (Lecture 1 §1.5):

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro">

  <!-- Solid box inertia, about the center of mass. -->
  <xacro:macro name="box_inertia" params="m x y z">
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="${m}"/>
      <inertia
        ixx="${(1.0/12.0) * m * (y*y + z*z)}" ixy="0.0" ixz="0.0"
        iyy="${(1.0/12.0) * m * (x*x + z*z)}" iyz="0.0"
        izz="${(1.0/12.0) * m * (x*x + y*y)}"/>
    </inertial>
  </xacro:macro>

  <!-- Solid cylinder inertia, spin axis along local z. -->
  <xacro:macro name="cylinder_inertia" params="m r l">
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="${m}"/>
      <inertia
        ixx="${(1.0/12.0) * m * (3.0*r*r + l*l)}" ixy="0.0" ixz="0.0"
        iyy="${(1.0/12.0) * m * (3.0*r*r + l*l)}" iyz="0.0"
        izz="${0.5 * m * r * r}"/>
    </inertial>
  </xacro:macro>

  <!-- Solid sphere inertia. -->
  <xacro:macro name="sphere_inertia" params="m r">
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="${m}"/>
      <inertia
        ixx="${(2.0/5.0) * m * r * r}" ixy="0.0" ixz="0.0"
        iyy="${(2.0/5.0) * m * r * r}" iyz="0.0"
        izz="${(2.0/5.0) * m * r * r}"/>
    </inertial>
  </xacro:macro>

</robot>
```

These three macros are the entire defense against the factor-of-1000 explosion. Because the tensor is *computed* from the same `m`, `x`, `y`, `z` you declare, it is consistent by construction.

---

## Step 2 — The wheel macro

Create `urdf/wheel.xacro`. One macro generates a wheel and its `continuous` joint; you call it twice (left, right):

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro">

  <!-- prefix: "left" or "right"; reflect: +1 or -1 to mirror the y position. -->
  <xacro:macro name="wheel" params="prefix reflect">
    <link name="${prefix}_wheel">
      <visual>
        <origin xyz="0 0 0" rpy="0 0 0"/>
        <geometry>
          <cylinder radius="${wheel_radius}" length="${wheel_width}"/>
        </geometry>
        <material name="wheel_black">
          <color rgba="0.1 0.1 0.1 1.0"/>
        </material>
      </visual>
      <collision>
        <origin xyz="0 0 0" rpy="0 0 0"/>
        <geometry>
          <cylinder radius="${wheel_radius}" length="${wheel_width}"/>
        </geometry>
      </collision>
      <xacro:cylinder_inertia m="${wheel_mass}" r="${wheel_radius}" l="${wheel_width}"/>
    </link>

    <joint name="${prefix}_wheel_joint" type="continuous">
      <parent link="base_link"/>
      <child link="${prefix}_wheel"/>
      <!-- rotate -90 deg about x so the cylinder's z-axis (spin axis) points along the robot y. -->
      <origin xyz="0 ${reflect * wheel_separation / 2.0} 0" rpy="-1.5707963 0 0"/>
      <axis xyz="0 0 1"/>
      <dynamics damping="0.01" friction="0.0"/>
    </joint>
  </xacro:macro>

</robot>
```

The `reflect` parameter (`+1` left, `-1` right) is the standard xacro trick for mirrored parts — write the geometry once, place it twice.

---

## Step 3 — The caster macro

Create `urdf/caster.xacro`. In Phase 1 a caster is a frictionless sphere `fixed` to the chassis — simpler and more stable than a real swivel joint:

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro">

  <xacro:macro name="caster" params="prefix x">
    <link name="${prefix}_caster">
      <visual>
        <origin xyz="0 0 0" rpy="0 0 0"/>
        <geometry>
          <sphere radius="${caster_radius}"/>
        </geometry>
        <material name="caster_grey">
          <color rgba="0.5 0.5 0.5 1.0"/>
        </material>
      </visual>
      <collision>
        <origin xyz="0 0 0" rpy="0 0 0"/>
        <geometry>
          <sphere radius="${caster_radius}"/>
        </geometry>
      </collision>
      <xacro:sphere_inertia m="${caster_mass}" r="${caster_radius}"/>
    </link>

    <joint name="${prefix}_caster_joint" type="fixed">
      <parent link="base_link"/>
      <child link="${prefix}_caster"/>
      <!-- Drop the caster so its bottom sits at the wheel contact plane. -->
      <origin xyz="${x} 0 ${-(wheel_radius - caster_radius)}" rpy="0 0 0"/>
    </joint>
  </xacro:macro>

</robot>
```

The z-offset places the caster's lowest point at the same height as the wheel contact, so the chassis sits level — a wheel-radius vs caster-radius arithmetic that, done wrong, tips the robot.

---

## Step 4 — The top-level robot

Create `urdf/crunchbot.urdf.xacro`. It declares the properties, includes the macro files, builds the chassis, and calls the macros:

```xml
<?xml version="1.0"?>
<robot name="crunchbot" xmlns:xacro="http://www.ros.org/wiki/xacro">

  <!-- ===== Parameters (single source of truth) ===== -->
  <xacro:property name="chassis_length" value="0.40"/>
  <xacro:property name="chassis_width"  value="0.30"/>
  <xacro:property name="chassis_height" value="0.10"/>
  <xacro:property name="chassis_mass"   value="2.0"/>

  <xacro:property name="wheel_radius"     value="0.05"/>
  <xacro:property name="wheel_width"      value="0.04"/>
  <xacro:property name="wheel_mass"       value="0.30"/>
  <xacro:property name="wheel_separation" value="0.36"/>

  <xacro:property name="caster_radius" value="0.025"/>
  <xacro:property name="caster_mass"   value="0.05"/>

  <!-- ===== Includes ===== -->
  <xacro:include filename="$(find crunchbot_description)/urdf/inertials.xacro"/>
  <xacro:include filename="$(find crunchbot_description)/urdf/wheel.xacro"/>
  <xacro:include filename="$(find crunchbot_description)/urdf/caster.xacro"/>

  <!-- ===== Chassis (the root link) ===== -->
  <link name="base_link">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="${chassis_length} ${chassis_width} ${chassis_height}"/>
      </geometry>
      <material name="cinnabar">
        <color rgba="0.86 0.15 0.15 1.0"/>
      </material>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="${chassis_length} ${chassis_width} ${chassis_height}"/>
      </geometry>
    </collision>
    <xacro:box_inertia m="${chassis_mass}"
                       x="${chassis_length}" y="${chassis_width}" z="${chassis_height}"/>
  </link>

  <!-- ===== Wheels and casters ===== -->
  <xacro:wheel prefix="left"  reflect="1"/>
  <xacro:wheel prefix="right" reflect="-1"/>
  <xacro:caster prefix="front" x="${chassis_length/2 - caster_radius}"/>
  <xacro:caster prefix="rear"  x="${-(chassis_length/2 - caster_radius)}"/>

</robot>
```

---

## Step 5 — Expand and parse

```bash
cd ~/crunch_ws && colcon build --packages-select crunchbot_description
source install/setup.bash

# Expand the xacro to plain URDF.
xacro $(ros2 pkg prefix crunchbot_description)/share/crunchbot_description/urdf/crunchbot.urdf.xacro > /tmp/crunchbot.urdf

# Parse it. This catches structural errors before any physics.
check_urdf /tmp/crunchbot.urdf
```

Expected `check_urdf` output:

```
robot name is: crunchbot
---------- Successfully Parsed XML ---------------
root Link: base_link has 4 child(ren)
    child(1):  front_caster
    child(2):  left_wheel
    child(3):  rear_caster
    child(4):  right_wheel
```

Five links, four joints, one root. If `check_urdf` reports more than one root or a missing parent, you have a typo in a `<parent>`/`<child>` name.

---

## Step 6 — Verify the inertias

Confirm the generated tensors match Lecture 1's hand-computed values:

```bash
grep -A4 'inertia ' /tmp/crunchbot.urdf | head -40
```

You should see the chassis with `ixx≈0.01667`, `iyy≈0.02833`, `izz≈0.04167`; each wheel with `izz≈0.000375`; each caster with `ixx=iyy=izz≈1.25e-5`. These are the numbers from the lecture — if yours differ, you typed a dimension wrong.

---

## Step 7 — Visualize in rviz2

Create `launch/display.launch.py`:

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import Command


def generate_launch_description():
    pkg = get_package_share_directory("crunchbot_description")
    xacro_file = os.path.join(pkg, "urdf", "crunchbot.urdf.xacro")
    robot_description = ParameterValue(Command(["xacro ", xacro_file]), value_type=str)

    return LaunchDescription([
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": robot_description}]),
        Node(package="joint_state_publisher_gui", executable="joint_state_publisher_gui"),
        Node(package="rviz2", executable="rviz2", output="screen"),
    ])
```

Run it, add a **RobotModel** display in rviz2 (set its Description Topic to `/robot_description`), set the Fixed Frame to `base_link`, and add a **TF** display:

```bash
ros2 launch crunchbot_description display.launch.py
```

You should see a red chassis, two black wheels, and two grey caster balls. Use the joint-state slider GUI to spin the wheels and confirm they rotate about the correct axis (around the robot's y, rolling forward).

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `crunchbot.urdf.xacro` plus the three macro files exist and build cleanly with `colcon build`.
- [ ] `xacro ... > /tmp/crunchbot.urdf` expands with no errors.
- [ ] `check_urdf /tmp/crunchbot.urdf` reports exactly one root (`base_link`) with four children.
- [ ] The generated inertials match the lecture's values (chassis `izz≈0.0417`, wheel `izz≈0.000375`, caster `≈1.25e-5`).
- [ ] rviz2 shows the full robot, and the joint-state GUI spins the wheels about the rolling axis.
- [ ] No inertia tensor was typed by hand — all came from the macros.

---

## Stretch

- Add a `base_footprint` link (a massless frame on the ground plane directly under `base_link`) joined to `base_link` by a fixed joint at `z = -wheel_radius`. This is the conventional frame Nav2 plans in; you will need it in Phase 3.
- Replace the box chassis collision with a slightly smaller box (1 cm inset on each side) and explain why a marginally smaller collision than visual is sometimes desirable.
- Parameterize the colors as xacro properties so the whole robot can be re-themed from the top of the file.

---

## Hints

<details>
<summary>If xacro fails with "$(find ...) not found"</summary>

You must `source install/setup.bash` after `colcon build` so `ros2 pkg prefix crunchbot_description` resolves. The `$(find ...)` in xacro uses the ament index, which only exists after install.

</details>

<details>
<summary>If the wheels appear flat / lying down in rviz2</summary>

Your wheel joint `<origin rpy>` rotation is wrong. The cylinder's natural axis is its local z; you must rotate it `-π/2` about x (`rpy="-1.5707963 0 0"`) so that axis becomes the robot's y. Check the `wheel.xacro` origin.

</details>

<details>
<summary>If check_urdf reports two roots</summary>

A link with no joint naming it as a child becomes a second root. Every non-root link must be the `<child>` of exactly one joint. Grep your file for the link name and confirm it appears once as a `<child>`.

</details>

---

When this feels comfortable, move to [Exercise 2 — Add a LiDAR and an IMU](./exercise-02-add-lidar-and-imu.py).
