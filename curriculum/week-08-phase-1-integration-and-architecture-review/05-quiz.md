# Week 8 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before the milestone review — these are the exact distinctions a reviewer probes. Answer key at the bottom; don't peek.

---

**Q1.** You open an unfamiliar `crunchbot_bringup` package and want to know its operator interface *without reading the source*. Which command do you run first?

- A) `ros2 node list`
- B) `ros2 launch crunchbot_bringup robot.launch.py --show-args`
- C) `ros2 topic list`
- D) `colcon build --packages-select crunchbot_bringup`

---

**Q2.** In a Python launch file you write:

```python
world = LaunchConfiguration('world')
world_path = '/worlds/' + world + '.sdf'
```

This raises a `TypeError` at launch generation. Why?

- A) `LaunchConfiguration` is not imported.
- B) `world` is a deferred substitution object, not a string; you cannot concatenate it with `+`. Compose it with `PathJoinSubstitution([...])` instead, and the launch system resolves it at runtime.
- C) The `world` argument was never declared.
- D) String paths must use `os.path.join`, not `+`.

---

**Q3.** Your `slam.launch.py` includes a node launched with `name='slam_toolbox'`, and your YAML is keyed `slam:` at the top level. After bring-up, none of your tuned parameters took effect — the node ran with all defaults. The cause is:

- A) The YAML file was not installed by `setup.py`.
- B) ROS2 looks up parameters under the node's *runtime name*; your YAML is keyed `slam:` but the node is named `slam_toolbox`, so the parameters silently do not match. Re-key the YAML to `slam_toolbox:`.
- C) `slam_toolbox` ignores YAML files and only accepts inline dicts.
- D) You forgot `--symlink-install`.

---

**Q4.** Two nodes in your bring-up both publish the `odom → base_link` transform — your week-6 odometry node and the Gz `DiffDrive` plugin. What is the observable symptom, and the fix?

- A) No symptom; ROS2 deduplicates transforms automatically. No fix needed.
- B) The TF tree flickers between two slightly-different poses at the combined publish rate, causing rviz jitter and nondeterministic SLAM. Fix: exactly one broadcaster per edge — in sim, let the Gz plugin own it and do not run the week-6 node.
- C) tf2 throws a compile error refusing duplicate broadcasters.
- D) The second broadcaster is ignored; only the first to start publishes.

---

**Q5.** Your robot publishes its laser scan on `/lidar/scan`, but `slam_toolbox` subscribes to `/scan`. Without editing `slam_toolbox`'s source, how do you connect them?

- A) Rename the frame id in the scan message.
- B) Add `remappings=[('/scan', '/lidar/scan')]` to the `slam_toolbox` `Node(...)` so the node's `/scan` is rewritten to `/lidar/scan`.
- C) Set a `scan_frame` parameter.
- D) You must edit `slam_toolbox` to subscribe to `/lidar/scan`.

---

**Q6.** You launch with `namespace:=robot1`. You want `slam_toolbox`'s node name and `/scan` subscription namespaced, but `/tf` and `/tf_static` to stay global (shared across robots). Which mechanism keeps TF global under the namespace?

- A) Set `use_sim_time: false` on the TF broadcaster.
- B) `remappings=[('/tf', '/tf'), ('/tf_static', '/tf_static')]` inside the namespaced group — the leading-slash absolute target prevents `PushRosNamespace` from prefixing the TF topics.
- C) Run the TF broadcaster outside the `GroupAction`.
- D) TF topics are always global; no action is needed.

---

**Q7.** With `namespace:=robot1`, you want robot1's frames to be distinct from robot2's. How do you prefix the *frame ids* (so `base_link` becomes `robot1/base_link`)?

- A) `remappings=[('base_link', 'robot1/base_link')]`.
- B) Set `frame_prefix: 'robot1/'` as a parameter on `robot_state_publisher` (and the corresponding `*_frame` parameters on other broadcasters). Frame ids are message content, set via parameters — not topic remaps.
- C) Add `PushRosNamespace` twice.
- D) Frame ids cannot be prefixed; you must rename them in the URDF.

---

**Q8.** `slam_toolbox` publishes `/map` with `RELIABLE` + `TRANSIENT_LOCAL` QoS. Your `map_run_timer` node subscribes with the default *sensor* QoS (`BEST_EFFORT`, `KEEP_LAST`, depth 5). What happens?

- A) The subscriber receives the map normally; QoS does not affect delivery.
- B) The subscriber silently never receives a map, because a `BEST_EFFORT` subscriber is incompatible with a `RELIABLE` publisher (the durability/reliability QoS contract is unmet). Fix: match the publisher's `RELIABLE` + `TRANSIENT_LOCAL`.
- C) The subscriber receives only the first map and then nothing.
- D) ROS2 logs a hard error and refuses to start the node.

---

**Q9.** Why does `/map` use `RELIABLE` + `TRANSIENT_LOCAL` while `/scan` uses `BEST_EFFORT` + `KEEP_LAST`?

- A) Maps are bigger, so they need reliability; scans are small, so they don't.
- B) The map is a *latched* state a late-joining subscriber (e.g., rviz2 started after SLAM) must still receive, so it needs `RELIABLE` + `TRANSIENT_LOCAL`. The scan is a high-rate stream where the newest sample matters and a dropped one is replaced milliseconds later, so `BEST_EFFORT` + `KEEP_LAST` is correct and cheaper.
- C) It is an arbitrary convention with no functional reason.
- D) `TRANSIENT_LOCAL` is required for any topic published more than once per second.

---

**Q10.** In `robot.launch.py` you place `SetParameter(name='use_sim_time', value=...)` as the *last* item in the `LaunchDescription` list, after all the includes. What goes wrong?

- A) Nothing; ordering does not matter for `SetParameter`.
- B) `SetParameter` applies to nodes launched *after* it in the description; placed last, it applies to nothing, so nodes default to wall time, their timestamps disagree with the sim `/clock`, and tf2 throws extrapolation errors. Place it first.
- C) It causes a duplicate-parameter error.
- D) It forces every node to wall time regardless of position.

---

**Q11.** You run `ros2 run tf2_tools view_frames` and the resulting PDF shows two disconnected trees: one rooted at `map` (containing only `map` and `odom`) and one rooted at `base_link` (containing the sensor frames). What is most likely wrong?

- A) `slam_toolbox` is not running.
- B) The `odom → base_link` edge is missing — nothing is broadcasting it. Either the Gz `DiffDrive` plugin is misconfigured (wrong frame names or odom publishing disabled) or no odometry source is running. Without that edge, `map`/`odom` and the `base_link` subtree are disconnected.
- C) `robot_state_publisher` is publishing on the wrong topic.
- D) The fixed frame in rviz2 is set wrong.

---

**Q12.** A reviewer asks: "Your wheel odometry drifts ~0.4 m over a 10 m square. Why, and what will you do about it?" Which answer demonstrates the understanding the milestone wants?

- A) "It's a bug in the Gz plugin; I'll file an issue."
- B) "Wheel odometry integrates velocity, so error from wheel slip, wheel-radius miscalibration, and discretization accumulates without bound. Phase 2 fuses the IMU and wheel odometry in an EKF (`robot_localization`) to bound the drift; the raw odometry here is the baseline that motivates that fusion."
- C) "I'll drive slower so it drifts less."
- D) "0.4 m is within spec, so no action is needed."

---

**Q13.** When is a `ComposableNodeContainer` (single-process, intra-process zero-copy) worth the complexity in *this* Phase 1 bring-up?

- A) Always; composition is strictly better than separate processes.
- B) Never in Phase 1: the topics here (2D scan, odometry, a slow-updating map) are low-bandwidth and the nodes are few, so process isolation (crash containment) is worth more than the saved copies. Composition earns its complexity in Phase 2's high-bandwidth perception pipeline (camera images, point clouds).
- C) Only when running more than ten nodes.
- D) Only when `use_sim_time` is true.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — `--show-args` is the launch file's `--help`: it prints every declared argument, its default, and its description, which is the operator interface. You run it *before* running the launch. The other commands tell you about a *running* system, not the interface to start one.

2. **B** — `LaunchConfiguration('world')` is a deferred substitution object the launch system evaluates at runtime, not a Python string. You cannot `+`-concatenate it. Compose substitutions with `PathJoinSubstitution([FindPackageShare(...), 'worlds', world])` and let the launch system resolve them. This is the single most common launch-file `TypeError`.

3. **B** — ROS2 looks up parameters under the node's *runtime name*. The YAML's top-level key must match `name=` exactly. Keyed `slam:` but named `slam_toolbox`, the parameters apply to a node that does not exist, so the real node runs with defaults. Re-key the YAML to `slam_toolbox:`. (A `/**:` wildcard key exists for cross-cutting params, but node-specific config should be keyed by name.)

4. **B** — Two broadcasters on one edge make the tree flicker between two poses at the combined rate, producing rviz jitter and nondeterministic scan matching. tf2 does *not* dedupe or error; it just publishes both. The rule is exactly one broadcaster per edge. In sim, the Gz `DiffDrive` plugin owns `odom → base_link`; you do not also run the week-6 node.

5. **B** — Topic remapping rewrites the topic a node uses without touching its source: `remappings=[('/scan', '/lidar/scan')]`. Option A confuses frames with topics (a frame id is message content, not an address). There is no `scan_frame` parameter that changes the *topic*.

6. **B** — `remappings=[('/tf', '/tf'), ('/tf_static', '/tf_static')]` looks like a no-op but prevents `PushRosNamespace` from prefixing the TF topics; the leading-slash absolute target pins them to the root. TF topics are global by convention because the tree is shared; only the frame *ids* get prefixed.

7. **B** — Frame ids are fields inside the message (`header.frame_id`), set via parameters: `frame_prefix: 'robot1/'` on `robot_state_publisher`, and the `*_frame` parameters on other broadcasters. They are *not* topic remaps. Topics are addresses; frames are content. Confusing the two is the most-missed point in multi-robot bring-up.

8. **B** — A `BEST_EFFORT` subscriber is incompatible with a `RELIABLE` publisher: ROS2's QoS contract requires the subscriber's reliability to be "at least as strong," so the connection is never established and the subscriber silently receives nothing. This is the canonical silent QoS mismatch from week 5. Match the publisher: `RELIABLE` + `TRANSIENT_LOCAL`.

9. **B** — The map is latched state that a late-joining subscriber must still receive, hence `RELIABLE` + `TRANSIENT_LOCAL` (transient-local means the publisher keeps the last sample for new subscribers). The scan is a high-rate stream where only the newest sample matters and a dropped one is immediately superseded, so `BEST_EFFORT` + `KEEP_LAST` is correct and cheaper. Size is not the reason.

10. **B** — `SetParameter` applies to actions that come *after* it in the launch description. Placed last, it applies to nothing; nodes default `use_sim_time` to false, run on wall time, and their timestamps disagree with the sim `/clock`, producing tf2 extrapolation errors. Place `SetParameter` first.

11. **B** — Two disconnected trees mean a missing edge between them. `map → odom` exists (so SLAM runs) and the `base_link` subtree exists (so `robot_state_publisher` runs), but nothing bridges `odom → base_link`. That edge is the odometry source — the Gz `DiffDrive` plugin in sim — which is misconfigured or absent. Fix the plugin's frame names / odom publishing.

12. **B** — The answer names the *mechanism* of drift (integration of velocity with slip, radius error, and discretization, unbounded over time) and the *remedy* (EKF fusion of IMU + wheel odometry in Phase 2 to bound it), and frames the raw number as the intended baseline. That is the understanding the milestone grades: drift is expected, explainable, and motivates the next phase.

13. **B** — In Phase 1 the topics are low-bandwidth and the nodes are few, so process isolation (a crash in one node does not kill the others) is worth more than the microseconds saved by zero-copy. Composition pays off for high-bandwidth, latency-critical pipelines — Phase 2's camera + point-cloud + detector graph at 30 Hz. Knowing *why you are not using it yet* is itself a senior signal.

</details>

---

If you scored under 10, re-read the lectures for the questions you missed — every one maps to a milestone defense. If you scored 12 or 13, you are ready for the [homework](./06-homework.md) and the architecture review.
