# Lecture 2 — The minimal robot bring-up pattern: composition, parameters, namespaces, remapping

> **Reading time:** ~75 minutes. **Hands-on time:** ~90 minutes (you scaffold a `*_bringup` package and bring the robot up with one command).

Lecture 1 taught you to read a `launch/` directory. This lecture teaches you to write one that is worth reading. We are going to build, conceptually, the exact package you will ship in this week's mini-project: `crunchbot_bringup`, the foundation package that every later phase extends. The pattern we use is not invented for this course — it is the pattern that `turtlebot4_bringup`, `nav2_bringup`, and essentially every production mobile-robot team independently converge on, because it is the one that survives a team, a year, and a hardware swap. We call it the **minimal robot bring-up pattern**: minimal because it includes exactly what is needed to operate the robot and nothing more, and a *pattern* because once you have built one, every robot you ever bring up looks the same.

By the end of this lecture you can lay out a `*_bringup` package, write a top-level launch file that composes per-subsystem launch files, manage every node's configuration as a YAML file, namespace the entire stack so two robots can coexist, remap topics and TF correctly under namespacing, and decide when to pull nodes into a composable container. These are the four pillars named in the title — composition, parameters, namespaces, remapping — and they are the four things the milestone reviewer will probe.

## 2.1 — The package layout that scales

Start with the directory structure, because it constrains everything else. A `*_bringup` package looks like this:

```text
crunchbot_bringup/
├── package.xml                 ← dependencies and metadata
├── setup.py                    ← (Python pkg) installs launch/, config/, worlds/, rviz/, maps/
├── resource/
│   └── crunchbot_bringup       ← ament resource marker
├── launch/
│   ├── robot.launch.py         ← TOP-LEVEL entry point (the one operators type)
│   ├── description.launch.py   ← robot_state_publisher + URDF (the kinematic claim)
│   ├── gz_sim.launch.py        ← Gz Sim server + spawn + ros_gz_bridge
│   ├── slam.launch.py          ← slam_toolbox
│   └── rviz.launch.py          ← rviz2 with the saved layout
├── config/
│   ├── slam_toolbox.yaml        ← every slam_toolbox parameter
│   ├── ros_gz_bridge.yaml       ← the topic bridge mapping
│   └── twist_mux.yaml           ← (optional) cmd_vel arbitration
├── rviz/
│   └── bringup.rviz             ← the saved rviz2 layout
├── worlds/
│   ├── warehouse.sdf
│   └── house.sdf
├── urdf/
│   └── crunchbot.urdf.xacro     ← the week-3 robot, parameterized
└── maps/
    └── .gitkeep                 ← saved maps land here at runtime
```

The non-negotiable rules of this layout:

- **`launch/` holds one top-level file and N subsystem files.** The top-level file is the only one operators run; the rest are includes. This is the composition pattern from lecture 1, expressed as a directory structure.
- **`config/` holds one YAML per node.** Configuration is data, not code. An operator edits `config/slam_toolbox.yaml`, not a Python launch file, to change the map resolution.
- **`worlds/`, `rviz/`, `urdf/`, `maps/` hold assets**, each found at runtime through `FindPackageShare`, never through an absolute path.
- **`setup.py` installs all of it** into the package's share directory so `FindPackageShare` resolves correctly. This is the step beginners forget, and it produces the maddening "file not found" error where the file is clearly *there* in the source tree but not in the *install* tree.

Here is the `setup.py` `data_files` block that installs the assets — the part that makes `FindPackageShare` work:

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

If you `glob('launch/*.launch.py')` but a teammate names their file `bringup_launch.py` (the older convention without the dot), the glob misses it and `FindPackageShare` cannot find it. Pick one naming convention — we use `<name>.launch.py` — and make your glob match. After any change to `setup.py` you must rebuild: `colcon build --packages-select crunchbot_bringup --symlink-install`. The `--symlink-install` flag is worth memorizing; it symlinks Python files and data so you can edit a launch file and re-run without rebuilding, which saves you minutes of iteration time every hour.

## 2.2 — Pillar 1: Composition

Composition means the top-level launch file *includes* subsystem launch files rather than declaring every node itself. We saw the shape in lecture 1, section 1.6. Here we justify it and detail the mechanics.

Why compose instead of writing one big file? Three reasons, all of which a senior engineer will cite:

1. **Reusability.** The `slam.launch.py` you write here is the same one Phase 3's Nav2 bring-up will include. If SLAM lives in its own file, you include it everywhere; if it is inlined in a monolith, you copy-paste it and the copies drift.
2. **Readability.** A 60-line top-level file that includes four named subsystems is comprehensible in two minutes. A 400-line monolith is not.
3. **Independent testing.** You can run `ros2 launch crunchbot_bringup slam.launch.py` on its own to debug SLAM in isolation, against a bag file, without bringing up Gz Sim. Subsystem files are independently runnable; that is what makes them debuggable.

The mechanics. A subsystem launch file is a normal `generate_launch_description()` that declares *its own* arguments (with defaults) and starts *its own* nodes. The top-level file includes it and threads arguments down. Here is `slam.launch.py` as a complete, correct subsystem file:

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('slam_params_file')

    declare_sim = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use the simulation clock published on /clock.')
    declare_params = DeclareLaunchArgument(
        'slam_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('crunchbot_bringup'), 'config', 'slam_toolbox.yaml']),
        description='Full path to the slam_toolbox parameter file.')

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            params_file,
            {'use_sim_time': use_sim_time},
        ],
    )

    return LaunchDescription([declare_sim, declare_params, slam_node])
```

Three things to notice, because they are the pattern:

- **The subsystem declares its own arguments with defaults.** `slam.launch.py` works standalone (`ros2 launch crunchbot_bringup slam.launch.py`) because its arguments have defaults. When the top-level file includes it, it overrides those defaults via `launch_arguments`. This is the contract: a subsystem is independently runnable *and* composable.
- **`parameters` is a list.** The first entry is the YAML file; the second is an inline dict that overrides `use_sim_time`. ROS2 merges the list left-to-right, so later entries win. The idiom is "file for the bulk, inline dict for the one value the launch needs to control." Never put the whole config in the inline dict.
- **`output='screen'`** sends the node's log to the terminal. For a SLAM node you want to see its output; for a chatty bridge you might set `output='log'`. This is an operator-facing choice.

The top-level file's job is to declare the *operator-facing* arguments (`world`, `slam`, `rviz`, `use_sim_time`) and thread them into the includes. We wrote that file in lecture 1, section 1.6. The division of labor is clean: the top-level file owns the operator interface; each subsystem owns its own nodes and its own internal arguments.

## 2.3 — Pillar 2: Parameters as files

A node's configuration belongs in a YAML file, loaded declaratively, not in `ros2 param set` commands typed after launch. This is the discipline that makes a robot reproducible. The reason is simple: a YAML file is version-controlled, reviewable, diffable, and loaded automatically; a `ros2 param set` command is none of those and is forgotten the moment you close the terminal.

The ROS2 parameter YAML format is specific and trips people up. It is keyed by **node name**, then `ros__parameters`, then the parameters themselves:

```yaml
# config/slam_toolbox.yaml
slam_toolbox:
  ros__parameters:
    # --- Solver ---
    solver_plugin: solver_plugins::CeresSolver
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_trust_strategy: LEVENBERG_MARQUARDT

    # --- Frames (these must match your TF tree exactly) ---
    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan

    # --- Mapping behavior ---
    mode: mapping                 # mapping | localization
    resolution: 0.05              # metres per occupancy-grid cell
    max_laser_range: 12.0         # metres; clip scans beyond this
    minimum_travel_distance: 0.3  # metres before adding a node to the pose graph
    minimum_travel_heading: 0.3   # radians before adding a node
    map_update_interval: 2.0      # seconds between map publishes

    # --- Loop closure ---
    do_loop_closing: true
    loop_search_maximum_distance: 3.0
    loop_match_minimum_response_fine: 0.45

    transform_publish_period: 0.02   # 50 Hz map->odom broadcast
    transform_timeout: 0.2
```

The keying rule is non-negotiable and the cause of most "my parameters did nothing" bugs: **the top-level key must be the node's runtime name.** If you launch the node with `name='slam_toolbox'` but your YAML is keyed `slam`, the parameters silently do not apply — ROS2 looks up parameters under the node's name and finds nothing under `slam`. The node runs with all defaults and you wonder why your `resolution` was ignored. The fix is to make the YAML key and the launch `name=` identical. (There is a `/**:` wildcard key that applies to any node name; use it sparingly, for cross-cutting parameters like `use_sim_time`, not for node-specific config.)

The `use_sim_time` discipline deserves its own paragraph because it is a guaranteed milestone question. In a Gz Sim bring-up, the simulator publishes time on `/clock`, and *every* node must use that clock instead of wall time, or their timestamps disagree and your TF lookups throw extrapolation errors. The correct pattern is to set `use_sim_time: true` on every node — via the inline dict in each `Node(...)`, or globally with a `SetParameter('use_sim_time', True)` action at the top of the launch file:

```python
from launch_ros.actions import SetParameter
# Place first in the LaunchDescription list; applies to every node launched after it.
SetParameter(name='use_sim_time', value=LaunchConfiguration('use_sim_time'))
```

`SetParameter` is the clean way to enforce `use_sim_time` across the whole bring-up without repeating the inline dict in every node. When you defend your stack, "I set `use_sim_time` globally with `SetParameter` so no node can accidentally run on wall time" is a strong answer.

Command-line overrides round out the pattern. An operator can override any declared launch argument, and any single parameter, from the command line:

```bash
# Override a launch argument (the clean, intended way):
ros2 launch crunchbot_bringup robot.launch.py world:=house slam:=false

# Override a single parameter file by pointing at a different YAML:
ros2 launch crunchbot_bringup robot.launch.py \
    slam_params_file:=/path/to/experiment_slam.yaml
```

The first form changes a launch argument; the second swaps an entire parameter file. Both are reproducible because both can be written down in a README. The anti-pattern — bringing the robot up, then typing `ros2 param set /slam_toolbox resolution 0.1` — changes the running system in a way nobody can reproduce. Do not do it except for live debugging, and never as the way you configure the robot.

## 2.4 — Pillar 3: Namespaces

A namespace is a prefix applied to every node name, topic, and service in a group, so that `/scan` becomes `/robot1/scan`. You do not need namespaces to bring up one robot — and for a single-robot bring-up, namespacing adds friction you should not pay yet. But the multi-robot work in Phase 5 *requires* it, and a bring-up package that cannot be namespaced has to be rewritten when that day comes. So we build the package namespace-ready from the start, even though the default namespace is empty.

Namespacing in launch is done with `PushRosNamespace` inside a `GroupAction`:

```python
from launch.actions import GroupAction
from launch_ros.actions import PushRosNamespace

robot_group = GroupAction([
    PushRosNamespace(LaunchConfiguration('namespace')),
    # every Node and IncludeLaunchDescription inside this group is namespaced
    description_include,
    gz_include,
    slam_include,
])
```

`PushRosNamespace` applies the namespace to *everything in the group that comes after it*. With `namespace:=robot1`, the SLAM node becomes `/robot1/slam_toolbox`, its `/scan` subscription becomes `/robot1/scan`, and so on. With `namespace:=` (empty, the default), nothing is prefixed and the robot comes up at the root, exactly as a single-robot bring-up wants.

The subtlety that catches everyone is **TF under namespacing.** The `/tf` and `/tf_static` topics are, by ROS2 convention, *global* — they live at the root, not under a namespace, because the TF tree is a single shared structure. But `PushRosNamespace` will, by default, push `/tf` to `/robot1/tf`, which breaks the shared tree. The standard fix is to remap `tf` and `tf_static` back to the global topics inside the group, while *prefixing the frame names themselves* so the two robots' frames do not collide. We cover the remapping mechanics in the next section; for now, internalize the rule:

> **Namespacing prefixes node names and topics, but the TF *topics* (`/tf`, `/tf_static`) stay global, while the TF *frame ids* get prefixed (`robot1/base_link`).** Topics are namespaced; the tree is shared; frames are prefixed.

This distinction — topic namespacing versus frame prefixing — is the single most-missed point in multi-robot bring-up, and it is why we introduce namespaces now even for a single robot: so that when Phase 5 asks for two robots, your package already does the right thing and you only change one argument.

## 2.5 — Pillar 4: Remapping

Remapping rewrites a node's topic, service, and frame names without touching the node's source code. It is how you reconcile a node that hard-codes `/cmd_vel` with a robot that expects `/diff_drive_controller/cmd_vel`, and it is how you keep TF global under namespacing.

The `remappings` keyword on `Node` takes a list of `(from, to)` tuples:

```python
Node(
    package='slam_toolbox',
    executable='async_slam_toolbox_node',
    name='slam_toolbox',
    parameters=[params_file, {'use_sim_time': use_sim_time}],
    remappings=[
        ('/scan', '/lidar/scan'),       # the node subscribes to /scan; our robot publishes /lidar/scan
        ('/map', '/slam/map'),          # publish the map on a non-default name
    ],
)
```

There are two distinct kinds of remapping, and conflating them is the source of much confusion:

1. **Topic remapping** rewrites the topic a node publishes or subscribes. `('/scan', '/lidar/scan')` means "wherever this node would have used `/scan`, use `/lidar/scan` instead." This is for reconciling topic-name mismatches between nodes written by different people.

2. **The TF-global remap under namespacing.** Inside a namespaced group, you remap `tf` and `tf_static` so they do not get the namespace prefix:

```python
GroupAction([
    PushRosNamespace('robot1'),
    Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{'robot_description': robot_desc,
                     'frame_prefix': 'robot1/',   # prefix the FRAME ids
                     'use_sim_time': use_sim_time}],
        remappings=[('/tf', '/tf'), ('/tf_static', '/tf_static')],  # keep TF topics GLOBAL
    ),
])
```

The `remappings=[('/tf', '/tf'), ('/tf_static', '/tf_static')]` looks like a no-op, but it is not: it *prevents* `PushRosNamespace` from rewriting `tf` to `robot1/tf`. The leading slash makes the target absolute, so the topic stays at the root regardless of the namespace. Meanwhile `frame_prefix: 'robot1/'` prefixes the *frame ids* the node broadcasts, so `base_link` becomes `robot1/base_link`. Result: both robots publish onto the one global `/tf` topic, but their frames have distinct names and do not collide. This is exactly the rule from section 2.4, expressed as launch syntax.

**Frame renaming is not topic remapping.** A topic remap changes which topic a message flows on. A frame id is a *field inside the message* (the `header.frame_id`), and you change it through a parameter (`frame_prefix` on `robot_state_publisher`, or the `*_frame` parameters on `slam_toolbox`), not through `remappings`. Mixing these up — trying to "remap" a frame, or trying to set a topic name via a frame parameter — is a common beginner error. Topics are addresses; frames are content. The reviewer may probe this distinction directly.

## 2.6 — Composable nodes: when one process beats many

By default, every `Node` in a launch file starts as its own OS process. That is the right default — process isolation means one crashing node does not take down the others. But for high-bandwidth topics (camera images, point clouds, dense scans), the cost of serializing a message, copying it across the process boundary through DDS, and deserializing it on the other side is real, and at 30 FPS it can dominate your latency budget. Composable nodes solve this: multiple nodes loaded into one process can pass messages by pointer (intra-process zero-copy) instead of serializing.

You declare a container and load composable nodes into it:

```python
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

container = ComposableNodeContainer(
    name='perception_container',
    namespace='',
    package='rclcpp_components',
    executable='component_container_mt',   # _mt = multi-threaded executor
    composable_node_descriptions=[
        ComposableNode(
            package='depth_image_proc',
            plugin='depth_image_proc::PointCloudXyzNode',
            name='point_cloud_xyz',
            extra_arguments=[{'use_intra_process_comms': True}],
        ),
        ComposableNode(
            package='image_proc',
            plugin='image_proc::RectifyNode',
            name='rectify',
            extra_arguments=[{'use_intra_process_comms': True}],
        ),
    ],
)
```

The `use_intra_process_comms: True` is the line that buys you zero-copy: when both ends of a topic live in the same container and use intra-process comms, ROS2 passes a shared pointer instead of serializing. For a 1080p image at 30 Hz this is the difference between a few microseconds and a few milliseconds per frame.

The honest engineering judgment, which you should be able to state at the milestone: **composition is worth it for high-bandwidth, low-latency pipelines, and not worth it otherwise.** For a Phase 1 bring-up — robot description, a diff-drive controller, `slam_toolbox`, rviz2 — the topics are low-bandwidth (a 2D scan, odometry, a slowly-updating map) and the processes are few, so standard separate-process nodes are correct: you get crash isolation for free and lose nothing measurable. You will reach for composition in Phase 2, when the depth camera and the YOLO detector push hundreds of megabytes per second and you need the 30 ms cycle. For now, know the pattern, know *why* you are not using it yet, and be ready to say so: "I did not compose the Phase 1 nodes because the topics are low-bandwidth and process isolation is worth more than the saved copies here; composition earns its complexity in Phase 2's perception pipeline." That answer demonstrates judgment, which is what the review grades.

## 2.7 — Avoiding the duplicate-broadcaster trap

The single most common way a Phase 1 bring-up fails the TF defense is a duplicate TF broadcaster. It happens like this: in week 6 you wrote an odometry node that publishes `odom → base_link`. In week 3 your Gz Sim diff-drive plugin *also* publishes `odom → base_link`. When you compose both into one bring-up, two nodes broadcast the same edge, and the TF tree flickers between two slightly-different poses at whatever rate each publishes. `view_frames` may even look fine (it shows the edge exists); the flicker only shows up as jitter in rviz2 and as nondeterministic SLAM behavior.

The rule is absolute: **exactly one broadcaster per TF edge.** For a sim bring-up you have a choice — let the Gz diff-drive plugin publish `odom → base_link`, or let your week-6 node publish it — but not both. The clean Phase 1 answer is to let the Gz `DiffDrive` plugin (configured with `<odom_publish_frequency>` and the `odom`/`base_link` frame names) own `odom → base_link`, and to *not* run your week-6 node in the sim bring-up (you keep it for the hardware path in Phase 6). Then:

- `robot_state_publisher` broadcasts the static joints from the URDF: `base_link → laser`, `base_link → imu`, `base_link → left_wheel`, etc.
- The Gz `DiffDrive` plugin broadcasts the dynamic `odom → base_link`.
- `slam_toolbox` broadcasts `map → odom`.

Three broadcasters, three disjoint sets of edges, one connected tree rooted at `map`. No edge has two owners. When the reviewer asks "who publishes `odom → base_link`?", the answer is one node, named, and you can prove there is no second one with:

```bash
# Each broadcaster announces itself; grep for the edge to confirm a single owner.
ros2 topic echo /tf --field transforms[0].child_frame_id --once
ros2 run tf2_ros tf2_monitor odom base_link   # reports the publishing rate and source
```

`tf2_monitor odom base_link` prints the average rate and, critically, will show an anomalous rate or warn if multiple authorities are writing the edge. Run it during milestone prep; a clean single-authority report is exactly the evidence the TF defense wants.

## 2.8 — Putting it together: the bring-up contract

The minimal bring-up pattern, distilled into a contract you can recite at the milestone:

1. **One command brings the robot up.** `ros2 launch crunchbot_bringup robot.launch.py`. No second terminal, no forgotten `ros2 run`, no machine-specific environment setup beyond what the README documents.
2. **The top-level file composes named subsystems.** It declares operator arguments and includes per-subsystem launch files; it declares no nodes of its own.
3. **Every node's config is a YAML file** under `config/`, keyed by the node's runtime name, loaded via `parameters=[file, {use_sim_time}]`.
4. **`use_sim_time` is enforced globally** with `SetParameter`, so no node can run on the wrong clock.
5. **The package is namespace-ready** (`PushRosNamespace` in a `GroupAction`, TF topics kept global, frame ids prefixed), even though the default namespace is empty.
6. **Topic mismatches are reconciled with `remappings`**, not by editing node source.
7. **Exactly one node broadcasts each TF edge.** The tree is connected, rooted at `map`, with no duplicate authorities.
8. **No absolute paths.** Every asset is found through `FindPackageShare`.

Satisfy this contract and your bring-up will run on a teammate's machine, namespace cleanly into a two-robot world in Phase 5, and pass the TF and QoS defenses at the milestone. Violate any one item and you have planted a bug that surfaces the day someone who is not you tries to run your robot.

## 2.9 — The reflexes to internalize this week

- **One top-level launch file, N subsystem files.** The top-level composes; it does not declare nodes.
- **One YAML per node, keyed by the node's runtime name.** Inline dicts are reserved for `use_sim_time` and one-off overrides.
- **`SetParameter('use_sim_time', ...)` once, at the top.** Never let a node default to wall time in a sim bring-up.
- **`FindPackageShare` for every path.** A `/home/` in a launch file is a machine-specific bug.
- **Build namespace-ready from day one.** `PushRosNamespace` in a `GroupAction`, TF topics global, frame ids prefixed. The default namespace is empty, but the machinery is there.
- **Topics are addresses; frames are content.** Remap topics; set frame ids via parameters. Never confuse the two.
- **One broadcaster per TF edge.** Run `tf2_monitor` to prove it.
- **Composition is for high-bandwidth pipelines.** Phase 1 does not need it; know why, and say so.
- **`colcon build --symlink-install`** so launch and config edits do not require a rebuild.

## 2.10 — What we did not cover (Phase 3 picks it up)

This lecture built the *foundation* bring-up: robot, sensors, SLAM, visualization. It deliberately stopped before the navigation and manipulation stacks. The lifecycle-manager pattern (where Nav2 brings its nodes up through the managed-node lifecycle in a controlled order), the behavior-tree-driven navigation launch, and the multi-controller namespace discipline for running Nav2 and MoveIt2 in one graph are all Phase 3 material (weeks 17 and 24). They *extend* this package rather than replace it — which is exactly why we built it as a reusable, namespace-ready, composition-based foundation. The mini-project this week is the foundation. Everything later is an include added to it.

---

## Lecture 2 — checklist before moving on

- [ ] I can lay out a `*_bringup` package with `launch/`, `config/`, `worlds/`, `rviz/`, `urdf/`, `maps/`.
- [ ] I can write `setup.py` `data_files` that install the assets so `FindPackageShare` finds them.
- [ ] I can write a top-level launch file that composes per-subsystem includes and threads arguments down.
- [ ] I can write a node parameter YAML keyed by the node's runtime name, and explain why a key mismatch silently fails.
- [ ] I can enforce `use_sim_time` globally with `SetParameter`.
- [ ] I can namespace a bring-up with `PushRosNamespace` and keep `/tf` global while prefixing frame ids.
- [ ] I can explain the difference between topic remapping and frame renaming.
- [ ] I can state when composable-node containers are worth it and why Phase 1 does not need them.
- [ ] I can guarantee exactly one TF broadcaster per edge and prove it with `tf2_monitor`.

If any box is unchecked, return to that section. The mini-project assumes you can build this package from scratch.

---

**References cited in this lecture**

- ROS2 Jazzy — "Creating a launch file": <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html>
- ROS2 Jazzy — "Using parameters in a class (Python)": <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html>
- ROS2 Jazzy — "Composing multiple nodes in a single process": <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>
- ROS2 Jazzy — "Launch files migration guide" (namespaces, remapping): <https://docs.ros.org/en/jazzy/How-To-Guides/Launch-files-migration-guide.html>
- `slam_toolbox` — configuration reference: <https://github.com/SteveMacenski/slam_toolbox>
- `turtlebot4_bringup` — the reference package layout: <https://github.com/turtlebot/turtlebot4>
- REP 105 — "Coordinate Frames for Mobile Platforms": <https://www.ros.org/reps/rep-0105.html>
