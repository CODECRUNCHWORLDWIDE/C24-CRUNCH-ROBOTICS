# Lecture 1 — Your launch file is your README for operators: reading a `launch/` directory like a senior engineer

> **Reading time:** ~70 minutes. **Hands-on time:** ~60 minutes (you read a real `launch/` directory cold and reconstruct its node graph before running it).

There is a skill that separates a robotics engineer who can *write* ROS2 from one who can *operate* it, and it is almost never taught explicitly: the ability to open a stranger's `launch/` directory and, before running a single command, reconstruct in your head exactly what nodes will start, what topics they will publish, what the TF tree will look like, and where the whole thing will fall over. This lecture teaches that skill. We do it before we teach you to write a good launch file, because the fastest way to learn to write one is to learn to read a hundred of them — and to internalize that **your launch file is the first thing another engineer reads when they inherit your robot.** It is documentation that executes. Write it like documentation.

By the end of this lecture you can take an unfamiliar package — `turtlebot4_bringup`, `nav2_bringup`, or a teammate's `crunchbot_bringup` — find the entry point, trace every `IncludeLaunchDescription`, resolve every substitution by hand, and produce a node-and-topic graph on paper that matches what `ros2 node list` and `ros2 topic list` will show once you actually run it. That is the senior reflex. It is also the exact skill the Phase 1 milestone reviewer uses on *your* package.

## 1.1 — Why the launch file is the operator interface, not an implementation detail

A junior engineer thinks of the launch file as plumbing: a necessary chore that wires nodes together so they can get back to the "real" code in the nodes themselves. This is exactly backwards. For everyone who is not the original author, **the launch file is the interface to the robot.** It answers the only questions an operator actually has:

- What do I type to bring the robot up?
- What can I change without editing code? (Which arguments exist?)
- What is running right now, and in what process?
- If something is wrong, which node do I look at?

The node source code answers none of those. The launch file answers all of them. When a new engineer joins your team and is handed the robot, they do not read your `odom_node.py` first. They read `robot.launch.py`, and from it they build a mental model of the whole system. If that file is a 400-line wall of un-parameterized `Node(...)` calls with hard-coded paths and no comments, you have handed them a puzzle. If it is a clean composition of named includes with declared arguments and a header comment explaining the topology, you have handed them an interface.

This is why the lecture's title is "your launch file is your README for operators." In a well-run robotics shop the launch file and the README co-evolve: the README says *what* the robot does, the launch file says *how to make it do that*, and the arguments declared in the launch file are exactly the knobs documented in the README. When they drift apart, the robot becomes folklore. The discipline this week is keeping them in sync.

## 1.2 — The three launch-file formats, and why we use Python

ROS2 lets you write launch files in three formats: Python, XML, and YAML. You will encounter all three in the wild. The rule is simple and you should adopt it as policy:

> **Use Python for anything with logic. Use XML/YAML only for trivial, static includes.**

XML and YAML launch files are *declarative*: a flat list of nodes and includes with no conditionals, no loops, no computed paths. They are pleasant to read when the launch is genuinely static — "start these four nodes, always, with these fixed parameters." The moment you need a conditional ("start `slam_toolbox` only if `slam:=true`"), a loop ("start one node per robot in a list of namespaces"), or a computed path ("find the config relative to this package's share directory"), the declarative formats either cannot express it or express it through awkward string interpolation. Python launch files are *imperative* Python programs that return a `LaunchDescription` object, so they can do anything Python can do.

Every real `*_bringup` package uses Python launch files for the top level. `nav2_bringup`, `turtlebot4_bringup`, `turtlebot3_bringup` — all Python. You will write Python. We mention XML/YAML only so that when you open a package that uses them, you recognize the format and know it implies "this launch is static."

Here is the smallest possible Python launch file, so the shape is concrete:

```python
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        Node(
            package='demo_nodes_cpp',
            executable='talker',
            name='talker',
        ),
        Node(
            package='demo_nodes_cpp',
            executable='listener',
            name='listener',
        ),
    ])
```

The launch system calls `generate_launch_description()`, gets back a `LaunchDescription` containing two `Node` actions, and starts both. Note the function name is **mandatory** and exact: the launch system looks for `generate_launch_description` by name. Get it wrong and `ros2 launch` reports "launch file does not contain a `generate_launch_description()` method" — the single most common beginner error.

## 1.3 — The reading algorithm: how a senior engineer parses a `launch/` directory

When you open an unfamiliar `launch/` directory, you do not read files top to bottom in alphabetical order. You execute a deliberate algorithm. Internalize it; you will run it on every package you ever inherit.

### Step 1 — Find the entry point

A `launch/` directory usually contains several files, but only one or two are meant to be run directly; the rest are includes. The entry point is the file an operator actually types. Heuristics to find it:

- It is named for the *system*, not a subsystem: `robot.launch.py`, `bringup.launch.py`, `tb4.launch.py` — not `lidar.launch.py` or `slam.launch.py`.
- It declares the most `DeclareLaunchArgument` actions — the entry point owns the operator-facing knobs.
- It is the one referenced in the package `README` and in `setup.py`'s `data_files` as the documented command.
- It contains `IncludeLaunchDescription` calls pointing at the *other* files in the directory. Includers are entry points; includees are subsystems.

For `nav2_bringup`, the entry point is `tb3_simulation_launch.py` (or `bringup_launch.py` for the hardware path). For `turtlebot4_bringup`, it is `standard.launch.py`. Find this file first. Everything else hangs off it.

### Step 2 — Read the declared arguments first

The block of `DeclareLaunchArgument` calls at the top of the entry point is the robot's command-line interface. Read it before you read anything else. It tells you, in one place:

- What is configurable (`world`, `slam`, `rviz`, `namespace`, `use_sim_time`, `params_file`).
- The defaults (so you know what `ros2 launch pkg robot.launch.py` does with no arguments).
- The description strings (a good launch file documents each argument inline).

You can dump this list without reading the file at all:

```bash
ros2 launch crunchbot_bringup robot.launch.py --show-args
```

This prints every declared argument, its default, and its description. **Run this on any unfamiliar launch file before you run the launch itself.** It is the equivalent of `--help` for a CLI. A launch file whose `--show-args` output is empty or undocumented is a launch file written by someone who did not think about operators.

### Step 3 — Trace the includes into a tree

Now follow every `IncludeLaunchDescription`. Each one points at another launch file (resolved through a substitution — more on those in a moment) and passes `launch_arguments` down into it. Draw the include tree:

```text
robot.launch.py                      (entry point)
├── description.launch.py            (robot_state_publisher + URDF)
├── gz_sim.launch.py                 (Gz Sim server + spawn + ros_gz bridge)
├── slam.launch.py        [if slam]  (slam_toolbox)
└── rviz.launch.py        [if rviz]  (rviz2 with saved config)
```

The `[if ...]` annotations come from the `condition=IfCondition(LaunchConfiguration('slam'))` on the include. Note them — they tell you which subsystems are optional. An include with no condition always runs; an include with an `IfCondition`/`UnlessCondition` runs only under that flag.

### Step 4 — Resolve the substitutions by hand

This is the step that separates people who *think* they can read launch files from people who actually can. Launch files are full of `LaunchConfiguration`, `PathJoinSubstitution`, `FindPackageShare`, `TextSubstitution`, and `Command`. These are **not** evaluated when you read the file; they are *deferred* objects that the launch system evaluates at runtime. To read the file, you evaluate them in your head.

- `LaunchConfiguration('world')` → the runtime value of the `world` argument (its default, unless overridden). If the default is `'warehouse'`, this resolves to the string `warehouse`.
- `FindPackageShare('crunchbot_bringup')` → the absolute path to the installed share directory, e.g. `/opt/ros/ws/install/crunchbot_bringup/share/crunchbot_bringup`.
- `PathJoinSubstitution([FindPackageShare('crunchbot_bringup'), 'worlds', LaunchConfiguration('world')])` → `.../share/crunchbot_bringup/worlds/warehouse` (with the `world` arg's value spliced in).
- `Command(['xacro ', urdf_path])` → the *output* of running `xacro` on the file at runtime; i.e., the expanded URDF XML as a string. This is how `robot_state_publisher` gets its `robot_description` parameter.

When you read a launch file, mentally substitute every deferred object with its resolved value. The senior reflex is to do this automatically — you see `PathJoinSubstitution([FindPackageShare(...), ...])` and your brain renders the absolute path without conscious effort. Until that is automatic, do it explicitly, on paper, the first few times.

### Step 5 — Reconstruct the runtime graph

Now you have the full picture. Write down, for the default arguments:

1. **Every node** that will start (package, executable, name, namespace).
2. **Every topic** each node publishes and subscribes (from the node's known interface plus any `remappings`).
3. **The TF tree** — which node broadcasts which transform.
4. **The process layout** — which nodes share a `ComposableNodeContainer` and which are standalone.

You can check your reconstruction against reality after you run it:

```bash
ros2 node list          # did the nodes you predicted appear?
ros2 topic list          # do the topics match?
ros2 run tf2_tools view_frames   # does the TF tree match your drawing?
```

If your paper reconstruction matches the live system, you have read the launch file correctly. If it does not, find where your mental substitution went wrong — that is the bug in your reading, and it is exactly the kind of mistake that bites you when you edit a launch file you did not fully understand.

## 1.4 — The substitution system in depth

Substitutions are the part of the launch system that trips up everyone the first time, because they invert the normal Python evaluation order you expect. Let us be precise about what is happening.

When `generate_launch_description()` runs, it returns a *description* of what to launch. It does not launch anything yet. The `LaunchConfiguration('world')` you wrote is an *object* representing "the value of the `world` argument, to be looked up later." The launch system collects all these deferred objects into the `LaunchDescription`, then enters its execution phase, where it resolves arguments (from defaults and command-line overrides), then evaluates every substitution against those resolved values, then starts the nodes.

This two-phase model is why you cannot write:

```python
# WRONG: this does not do what you think.
world = LaunchConfiguration('world')
world_path = '/worlds/' + world + '.sdf'   # TypeError: can't concat str and LaunchConfiguration
```

`world` is not a string; it is a substitution object. You cannot string-concatenate it. You compose substitutions instead:

```python
# RIGHT: compose substitutions; the launch system evaluates them at runtime.
from launch.substitutions import PathJoinSubstitution, TextSubstitution
from launch_ros.substitutions import FindPackageShare

world_path = PathJoinSubstitution([
    FindPackageShare('crunchbot_bringup'),
    'worlds',
    LaunchConfiguration('world'),   # resolves to e.g. 'warehouse'
])
```

The substitutions you will use constantly:

| Substitution | What it resolves to |
|---|---|
| `LaunchConfiguration('x')` | The runtime value of launch argument `x`. |
| `FindPackageShare('pkg')` | Absolute path to `pkg`'s installed `share/` directory. |
| `PathJoinSubstitution([a, b, c])` | OS-correct path join of the resolved parts. |
| `TextSubstitution(text='foo')` | A literal string (used to mix literals with other substitutions). |
| `Command(['xacro ', path])` | The stdout of running the command at launch time. |
| `EnvironmentVariable('GZ_SIM_RESOURCE_PATH')` | The value of an environment variable. |
| `PythonExpression(['"', cfg, '" == "true"'])` | A Python expression evaluated against resolved substitutions; useful in conditions. |

The reason this matters for *reading* is that an unfamiliar launch file is mostly substitutions, and you cannot reconstruct the runtime graph without resolving them. The reason it matters for *writing* is that nine out of ten "my launch file throws a `TypeError`" bugs are someone trying to treat a substitution like a string.

## 1.5 — Conditions: how optional subsystems are expressed

A bring-up launch file almost always has optional subsystems — run SLAM or not, run rviz or not, use sim time or real time. These are expressed with `condition=` on an action:

```python
from launch.conditions import IfCondition, UnlessCondition

slam = LaunchConfiguration('slam')

IncludeLaunchDescription(
    PythonLaunchDescriptionSource(PathJoinSubstitution([
        FindPackageShare('crunchbot_bringup'), 'launch', 'slam.launch.py',
    ])),
    condition=IfCondition(slam),   # include slam.launch.py only when slam:=true
    launch_arguments={'use_sim_time': LaunchConfiguration('use_sim_time')}.items(),
)
```

When you read a launch file, every action either has no condition (always runs) or has an `IfCondition`/`UnlessCondition` (runs only under a flag). Catalog the conditions as you trace the includes; they are the difference between "what runs by default" and "what *can* run." A reviewer who asks "what happens with `slam:=false`?" is checking whether you understand your own conditions. The answer should be immediate: "the `slam.launch.py` include is gated by `IfCondition(slam)`, so with `slam:=false` no `slam_toolbox` node starts, no `/map` topic is published, and the TF tree is missing the `map → odom` link that `slam_toolbox` would otherwise broadcast."

`IfCondition` and `UnlessCondition` take a substitution that must resolve to a truthy/falsy string. ROS2 accepts `true`/`false`, `1`/`0`, `True`/`False`, `yes`/`no`. Stick to `true`/`false` for consistency; it is what every reference package uses.

## 1.6 — A worked reading: dissecting a real bring-up include tree

Let us walk the algorithm on a concrete file so the steps are not abstract. Below is a representative top-level launch file in the shape your mini-project will produce. Read it the way the algorithm says.

```python
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg = FindPackageShare('crunchbot_bringup')

    declare_world = DeclareLaunchArgument(
        'world', default_value='warehouse',
        description='World name under worlds/ to load in Gz Sim.')
    declare_slam = DeclareLaunchArgument(
        'slam', default_value='true',
        description='Start slam_toolbox in mapping mode.')
    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='true',
        description='Start rviz2 with the saved bringup layout.')
    declare_sim = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use the Gz Sim /clock instead of wall time.')

    use_sim_time = LaunchConfiguration('use_sim_time')

    description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg, 'launch', 'description.launch.py'])),
        launch_arguments={'use_sim_time': use_sim_time}.items())

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg, 'launch', 'gz_sim.launch.py'])),
        launch_arguments={'world': LaunchConfiguration('world')}.items())

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg, 'launch', 'slam.launch.py'])),
        condition=IfCondition(LaunchConfiguration('slam')),
        launch_arguments={'use_sim_time': use_sim_time}.items())

    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg, 'launch', 'rviz.launch.py'])),
        condition=IfCondition(LaunchConfiguration('rviz')),
        launch_arguments={'use_sim_time': use_sim_time}.items())

    return LaunchDescription([
        declare_world, declare_slam, declare_rviz, declare_sim,
        description, gz, slam, rviz,
    ])
```

Run the algorithm:

1. **Entry point?** Yes — it declares four arguments and includes four other files. This is the operator's command.
2. **Declared arguments?** `world` (default `warehouse`), `slam` (default `true`), `rviz` (default `true`), `use_sim_time` (default `true`). The command-line interface is exactly these four knobs.
3. **Include tree?** Four includes: `description` (always), `gz_sim` (always), `slam` (`if slam`), `rviz` (`if rviz`).
4. **Resolve substitutions?** `PathJoinSubstitution([pkg, 'launch', 'description.launch.py'])` → `.../share/crunchbot_bringup/launch/description.launch.py`, and so on. `use_sim_time` threads `true` into every include.
5. **Runtime graph (default args)?** `robot_state_publisher` (from `description`), the Gz Sim server + spawn + `ros_gz_bridge` (from `gz_sim`), `slam_toolbox` (from `slam`, since default `true`), `rviz2` (from `rviz`, since default `true`). TF: `robot_state_publisher` broadcasts the URDF's static joints and `base_link → laser`/`base_link → imu`; the diff-drive controller (inside `gz_sim`) broadcasts `odom → base_link`; `slam_toolbox` broadcasts `map → odom`. Full tree rooted at `map`.

You have just read a launch file without running it. That is the skill. Now confirm it:

```bash
ros2 launch crunchbot_bringup robot.launch.py --show-args
# (read the four args, confirm they match your step 2)
ros2 launch crunchbot_bringup robot.launch.py &
ros2 node list                                   # confirm step 5's nodes
ros2 run tf2_tools view_frames                   # confirm the TF tree
```

## 1.7 — The smells: what a senior engineer flags on first read

Reading is also judging. As you parse a `launch/` directory you are building a quality opinion. Here are the smells that make a senior engineer wince, in rough order of severity. Your milestone reviewer is trained to spot every one of them in your package.

1. **Hard-coded absolute paths.** `parameters=['/home/jeanstephane/ws/config/slam.yaml']` does not work on any machine but the author's. The fix is `PathJoinSubstitution([FindPackageShare(pkg), 'config', 'slam.yaml'])`. This is the single most common reason a launch file fails on a teammate's machine.

2. **Parameters set inline as dictionaries instead of files.** `parameters=[{'resolution': 0.05, 'max_laser_range': 12.0, ...twenty more...}]` buries the configuration in Python. The fix is one YAML file per node, loaded as `parameters=[config_path]`. Inline dicts are fine for one or two values (like `use_sim_time`); a node's full configuration belongs in a file an operator can edit without touching code.

3. **No declared arguments.** A launch file with zero `DeclareLaunchArgument` calls has no operator interface — every choice is baked in, and changing the world means editing the file. The fix is to lift every choice an operator might make into a declared argument with a sensible default.

4. **`use_sim_time` not threaded consistently.** If half your nodes use sim time and half use wall time, your TF lookups will throw extrapolation errors that look like a tf2 bug but are actually a clock-mismatch bug. Every node in a sim bring-up must get `use_sim_time: true`. A launch file that sets it on some nodes and not others is a latent failure.

5. **Duplicate TF broadcasters.** Two nodes both publishing `odom → base_link` (e.g., the Gz diff-drive plugin *and* a leftover week-6 odometry node) produce a TF tree that flickers between two poses. The fix is exactly one broadcaster per edge. We cover this in lecture 2 and it is a guaranteed milestone question.

6. **A monolithic 400-line launch file.** Everything in one file with no includes is unreadable and unreusable. The fix is composition: one top-level file that includes per-subsystem files. A reviewer should be able to read your top-level file in two minutes and know the whole topology.

7. **Undocumented arguments.** `DeclareLaunchArgument('mode', default_value='2')` with no `description` and no obvious meaning. What is mode 2? The fix is a `description=` on every argument, and a README that lists them.

When you finish reading a launch directory, you should be able to state its quality in one sentence: "Clean composition, every argument documented, parameters in files, single TF broadcaster per edge" — or — "Monolithic, hard-coded paths, inline params, would not run on my machine." The milestone trains you to produce the first sentence about your own package.

## 1.8 — Reading the event system: ordering, lifecycle, and "what starts after what"

There is one more thing a senior engineer reads in a launch file that a beginner skips entirely: the **event handlers**. The launch system is not just a flat list of "start these nodes" — it is an event-driven runtime where actions can be made to depend on other actions. When you read a `launch/` directory, you must notice these dependencies, because they encode the *order* in which the system comes up, and order is where bring-up bugs hide.

The launch event you will see most is `RegisterEventHandler` with an `OnProcessStart`, `OnProcessExit`, or `OnExecutionComplete` handler. It means "do not run action B until event X happens to action A." A common, correct use in a robot bring-up is "do not spawn the robot into Gz Sim until the Gz server process has actually started," because spawning into a server that is not up yet fails silently:

```python
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node

# Start the Gz server, then spawn the robot ONLY after the server is up.
gz_server = ExecuteProcess(cmd=['gz', 'sim', '-r', world_path], output='screen')

spawn_robot = Node(
    package='ros_gz_sim', executable='create',
    arguments=['-name', 'crunchbot', '-topic', 'robot_description'],
    output='screen')

spawn_after_server = RegisterEventHandler(
    OnProcessStart(target_action=gz_server, on_start=[spawn_robot]))
```

When you read this, the senior interpretation is immediate: "`spawn_robot` does not run at launch time; it runs *after* `gz_server` reports it has started. The author understood the race between server startup and spawn, and ordered around it." A launch file that spawns the robot unconditionally at the top, with no event handler gating it on the server, has a latent race — it works on a fast machine and fails on a slow one. That intermittent "the robot sometimes does not spawn" bug is, almost always, a missing `OnProcessStart` handler. Noticing its absence is a senior reading skill.

The other event you will encounter is `OnProcessExit`, used for sequencing teardown or for "run the map-save step after the mapping process finishes." When you trace a launch file, catalog every `RegisterEventHandler` alongside the includes and conditions:

- **No event handlers** → everything starts at once, in description order, with no inter-action ordering. Fine for independent nodes; a bug if anything races (like the Gz spawn).
- **`OnProcessStart` handlers** → "B waits for A to start." Read these as the author's startup-ordering decisions.
- **`OnProcessExit` handlers** → "B runs when A exits." Read these as teardown or post-step sequencing.

Lifecycle nodes (the managed-node pattern from week 4) add a second ordering layer you will meet properly in Phase 3: Nav2's `lifecycle_manager` brings its nodes through `configure → activate` in a controlled sequence, and the launch file *configures the manager*, not the nodes directly. You will not write lifecycle bring-up this week — Phase 1's nodes are not lifecycle-managed — but when you read `nav2_bringup` you will see a `Node(package='nav2_lifecycle_manager', ...)` with an `autostart` parameter and a `node_names` list, and you should recognize it as "this launch file delegates startup *ordering* to a lifecycle manager rather than to launch event handlers." That recognition is the difference between reading the file and understanding it.

For your Phase 1 bring-up the practical rule is narrow: **gate the Gz spawn on the Gz server start with `OnProcessStart`.** That single event handler is the one piece of the event system your mini-project actually needs, and its absence is the most common reason a bring-up "sometimes" fails to spawn the robot. Everything else — `OnProcessExit` sequencing, lifecycle managers — is reading practice for the packages you inherit and for the phases ahead.

## 1.9 — The reflexes to internalize this week

You will read and write a lot of launch files in the next two days. Build these reflexes:

- **`--show-args` before you run.** Always. It is the robot's `--help`. A launch file you cannot `--show-args` your way around is a launch file you do not understand yet.
- **Trace includes into a tree on paper before editing.** You cannot safely edit a launch file whose include tree you have not reconstructed.
- **Resolve substitutions in your head.** `PathJoinSubstitution([FindPackageShare(...), ...])` should render to an absolute path automatically. Practice until it does.
- **Catalog the conditions.** Know, for every action, whether it always runs or runs under a flag. "What happens with `slam:=false`?" should have an instant answer.
- **One config file per node.** Parameters live in YAML, not in inline Python dicts. The dict is reserved for `use_sim_time` and the occasional one-off.
- **No absolute paths, ever.** Everything is relative to a `FindPackageShare`. If you type `/home/` into a launch file, you have introduced a machine-specific bug.
- **The launch file and the README co-evolve.** Every argument you declare is a knob you document. When they drift, the robot becomes folklore.

These reflexes are the entire methodology of operating a ROS2 robot as a team rather than as an individual. Lecture 2 teaches you to *write* the bring-up package; this lecture taught you to *read* one, because you cannot write a good one until you can recognize a good one.

## 1.10 — What we did not cover (lecture 2 picks it up)

This lecture was about reading and judging an existing `launch/` directory. It deliberately did not cover the *construction* details: how to structure a `*_bringup` package's directories, how `setup.py` installs the launch and config files so `FindPackageShare` finds them, how namespaces and remapping let one launch file serve two robots, and when composable-node containers are worth the complexity. That is lecture 2 and the mini-project. For now, you have the reading skill — go read `turtlebot4_bringup` and `nav2_bringup` with the algorithm in section 1.3, and write a one-paragraph quality verdict for each. That reading is the prerequisite for writing your own.

---

## Lecture 1 — checklist before moving on

- [ ] I can find the entry-point launch file in an unfamiliar `launch/` directory using the section 1.3 heuristics.
- [ ] I can run `--show-args` on any launch file and read its operator interface.
- [ ] I can trace `IncludeLaunchDescription` calls into an include tree and annotate the conditional includes.
- [ ] I can resolve `LaunchConfiguration`, `FindPackageShare`, and `PathJoinSubstitution` to concrete values by hand.
- [ ] I can reconstruct the node list, topic list, and TF tree from a launch file *before* running it, and verify with `ros2 node list` / `view_frames`.
- [ ] I can name the seven launch-file smells from section 1.7 and propose the fix for each.
- [ ] I have actually read the `turtlebot4_bringup` or `nav2_bringup` `launch/` directory with the algorithm and written a one-paragraph verdict.

If any box is unchecked, return to that section. Lecture 2 assumes you can read a launch file fluently, because you are about to write one.

---

**References cited in this lecture**

- ROS2 Jazzy — "Creating a launch file": <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html>
- ROS2 Jazzy — "Using substitutions": <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-Substitutions.html>
- ROS2 Jazzy — "Launch file different formats": <https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html>
- `nav2_bringup` — the gold-standard launch composition: <https://github.com/ros-navigation/navigation2/tree/main/nav2_bringup>
- `turtlebot4_bringup` — the reference `*_bringup` package: <https://github.com/turtlebot/turtlebot4>
- REP 105 — "Coordinate Frames for Mobile Platforms": <https://www.ros.org/reps/rep-0105.html>
