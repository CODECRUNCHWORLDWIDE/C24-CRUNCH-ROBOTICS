# Exercise 1 — Package weeks 3–7 into one `crunchbot_bringup` package

> **Estimated time:** ~90 minutes. This is the foundation every other exercise, the challenge, and the mini-project builds on. Do it carefully; sloppiness here costs you for the rest of the week.

## Goal

Create the `crunchbot_bringup` ament-Python package, lay out its directories per lecture 2, write a `setup.py` that installs the assets so `FindPackageShare` resolves them, and migrate three artifacts you already have:

- Your **week-3 URDF** (the diff-drive xacro with LiDAR + IMU) → `urdf/crunchbot.urdf.xacro`.
- Your **week-7 `slam_toolbox` config** → `config/slam_toolbox.yaml`.
- A **Gz Sim world** you have driven before → `worlds/warehouse.sdf`.

By the end you have a buildable package with a top-level launch skeleton that runs `robot_state_publisher` against your URDF and nothing else yet. Exercise 2 fills in the rest.

## Why this matters

You spent seven weeks producing fragments scattered across seven directories. A teammate cannot run any of them. This exercise is the moment those fragments become *one installable thing* with a documented command. It is the difference between "I have some ROS2 code" and "I have a robot bring-up package." Every senior robotics codebase has exactly this shape; you are building yours.

## Steps

### Step 1 — Create the package

From your ROS2 workspace `src/` directory:

```bash
cd ~/crunch_ws/src
ros2 pkg create crunchbot_bringup \
    --build-type ament_python \
    --dependencies rclpy launch launch_ros robot_state_publisher xacro slam_toolbox ros_gz_sim ros_gz_bridge
```

This scaffolds `crunchbot_bringup/` with a `package.xml`, a `setup.py`, a `resource/crunchbot_bringup` marker, and a `crunchbot_bringup/` Python module directory. The `--dependencies` list pre-populates `package.xml` with the `<exec_depend>` entries you need.

### Step 2 — Create the asset directories

```bash
cd crunchbot_bringup
mkdir -p launch config rviz worlds urdf maps
touch maps/.gitkeep
```

Your tree should now match lecture 2, section 2.1.

### Step 3 — Migrate your artifacts

Copy in the three files you already have. Rename them to the canonical names so the launch files (and your teammates) can find them:

```bash
cp ~/path/to/week3/robot.urdf.xacro   urdf/crunchbot.urdf.xacro
cp ~/path/to/week7/mapper_params.yaml config/slam_toolbox.yaml
cp ~/path/to/week3/warehouse.sdf       worlds/warehouse.sdf
```

Open `config/slam_toolbox.yaml` and confirm the top-level key is the node's runtime name. You will launch the node with `name='slam_toolbox'`, so the YAML must be keyed `slam_toolbox:` (not `slam:` or `mapper_params:`). Fix it if week 7 used a different key. This is the single most common silent-failure bug; check it now.

### Step 4 — Write `setup.py` `data_files`

Replace the `data_files` list in `setup.py` with the block from lecture 2, section 2.1, so the launch, config, rviz, world, and urdf directories are installed into the package's `share/`:

```python
import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'crunchbot_bringup'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        (os.path.join('share', package_name), ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Crunch Robotics',
    maintainer_email='robotics@crunchlabs.dev',
    description='Foundation bring-up package for the crunchbot: robot, sensors, SLAM, rviz2.',
    license='GPL-3.0-or-later',
    entry_points={'console_scripts': []},
)
```

### Step 5 — Write the `description.launch.py` subsystem file

This is the first subsystem launch file. It runs `robot_state_publisher`, which reads your URDF (expanded from xacro at launch time) and broadcasts the static joint transforms. Create `launch/description.launch.py`:

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_sim = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use the simulation clock published on /clock.')

    urdf_path = PathJoinSubstitution([
        FindPackageShare('crunchbot_bringup'), 'urdf', 'crunchbot.urdf.xacro'])

    # Command runs `xacro <path>` at launch time; its stdout is the expanded URDF XML.
    robot_description = Command(['xacro ', urdf_path])

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
    )

    return LaunchDescription([declare_sim, rsp])
```

Note the space after `xacro` in `Command(['xacro ', urdf_path])` — without it the command becomes `xacro/abs/path` and fails. This is a classic typo; the space is load-bearing.

### Step 6 — Write a minimal top-level skeleton

Create `launch/robot.launch.py` that, for now, just includes `description.launch.py`. You will grow it in exercise 2.

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg = FindPackageShare('crunchbot_bringup')
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_sim = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use the Gz Sim /clock instead of wall time.')

    description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg, 'launch', 'description.launch.py'])),
        launch_arguments={'use_sim_time': use_sim_time}.items())

    return LaunchDescription([
        SetParameter(name='use_sim_time', value=use_sim_time),
        declare_sim,
        description,
    ])
```

### Step 7 — Build and verify

```bash
cd ~/crunch_ws
colcon build --packages-select crunchbot_bringup --symlink-install
source install/setup.bash
ros2 launch crunchbot_bringup robot.launch.py --show-args
ros2 launch crunchbot_bringup robot.launch.py
```

In another terminal:

```bash
ros2 node list                  # expect /robot_state_publisher
ros2 topic list                 # expect /robot_description, /tf_static, /tf, /joint_states
ros2 run tf2_tools view_frames  # expect base_link + the sensor frames, all static for now
```

## Expected output

`--show-args` prints your one declared argument:

```text
Arguments (pass arguments as '<name>:=<value>'):

    'use_sim_time':
        Use the Gz Sim /clock instead of wall time.
        (default: 'true')
```

The launch itself prints the `robot_state_publisher` startup line and then sits quietly. `ros2 node list` shows exactly one node:

```text
/robot_state_publisher
```

And `view_frames` produces a `frames.pdf` showing `base_link` connected to `laser`, `imu`, and the wheel frames via static transforms — no `odom` or `map` yet (those arrive in exercise 2 when you add the Gz controller and SLAM).

## Acceptance criteria

- [ ] `crunchbot_bringup` builds cleanly with `colcon build --symlink-install` (no warnings, no errors).
- [ ] The package tree matches lecture 2 section 2.1 (`launch/`, `config/`, `rviz/`, `worlds/`, `urdf/`, `maps/`).
- [ ] `config/slam_toolbox.yaml` is keyed by the node name `slam_toolbox:`.
- [ ] `ros2 launch crunchbot_bringup robot.launch.py --show-args` lists the `use_sim_time` argument with its description.
- [ ] `ros2 launch crunchbot_bringup robot.launch.py` starts `robot_state_publisher` and nothing else.
- [ ] `view_frames` shows a connected static tree under `base_link`.
- [ ] No absolute paths appear anywhere in `launch/` (every path is a `FindPackageShare` + `PathJoinSubstitution`).

## Hints

<details>
<summary>Hint 1 — colcon builds but the launch says "file not found"</summary>

You added the file to `launch/` but forgot to rebuild after editing `setup.py`, or your `glob` does not match the filename. The install tree (`install/crunchbot_bringup/share/...`) is what `FindPackageShare` reads, not your `src/` tree. Run `colcon build --symlink-install` again and confirm the file appears under `install/crunchbot_bringup/share/crunchbot_bringup/launch/`. With `--symlink-install`, edits to existing launch files take effect without rebuilding, but *new* files require a rebuild so the glob picks them up.
</details>

<details>
<summary>Hint 2 — robot_state_publisher fails with an XML parse error</summary>

`Command(['xacro ', urdf_path])` failed. Run `xacro urdf/crunchbot.urdf.xacro` by hand from the package directory and read the error — it is a xacro problem (a missing macro, an undefined property), not a launch problem. Fix the URDF, then re-launch. Remember the space after `xacro` in the Command list.
</details>

<details>
<summary>Hint 3 — view_frames shows base_link but no sensor frames</summary>

Your URDF's `<joint>` elements connecting `base_link` to `laser`/`imu` are missing, or `robot_state_publisher` is not receiving `/joint_states`. For *static* (fixed) joints, `robot_state_publisher` publishes them on `/tf_static` without needing `/joint_states`. If the fixed joints are missing from the tree, they are missing from the URDF — check that each sensor link has a `<joint type="fixed">` to `base_link`.
</details>

## Submission

Commit the `crunchbot_bringup` package to your Week 8 repository at `exercises/crunchbot_bringup/`. Exercises 2 and 3 and the mini-project all extend this same package, so keep it as your working copy.
