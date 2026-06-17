# Week 17 Homework

Six problems that revisit the week's topics and force the Nav2 architecture into your fingers. The full set should take about **5 hours**. Work in your Week 17 Git repository (the same workspace as the exercises and the `crunchbot_nav` mini-project) so every problem produces at least one commit you can point to in the Phase 3 integration in Week 24.

The headline deliverable is **Problem 4 — the fail-safe declaration**, the first of Phase 3's mandatory per-week fail-safes. Treat it as the artifact a safety reviewer reads, not a journal entry.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`) and your overlay. Have your **week-7 map** loadable and the **week-3 robot** spawnable in Gz Sim — Problems 1, 2, 4, and 6 run a live Nav2 stack against them. If the sim is broken, the standalone scripts from the exercises are your fallback; say so in your writeup.

---

## Problem 1 — The lifecycle audit table

**Problem statement.** Bring up the full Nav2 stack on your week-7 map. For **every** Nav2 server, run `ros2 lifecycle get /<server>` and record the state. Then deliberately break one server (point its plugin at a typo, e.g. `dwb_core::DWBLocalPlannerTYPO`), restart, and record the states again. Build a markdown table in `notes/week-17/lifecycle-audit.md` with one row per server and these columns:

| Server | Loads plugin type | Healthy state | Broken-run state | What broke it |
|---|---|---|---|---|

**Acceptance criteria.**

- `notes/week-17/lifecycle-audit.md` exists with one row per server (at least nine rows).
- The healthy run shows every server `active [3]`.
- The broken run shows the typo'd server stuck below `active`, and you note whether `bt_navigator` was *also* stuck as a consequence.
- Committed.

**Hint.** Loop it: `for n in map_server amcl controller_server planner_server behavior_server bt_navigator smoother_server velocity_smoother waypoint_follower; do printf "%-22s " $n; ros2 lifecycle get /$n; done`. The "what broke it" column comes from the offending server's `ERROR` log line — find it in your launch output.

**Estimated time.** 40 minutes.

---

## Problem 2 — Costmap layer surgery, measured

**Problem statement.** Take your global costmap. In three runs, change the `inflation_layer.inflation_radius` to `0.3`, `0.55`, and `0.9`, clearing the costmap between each. For each, use the Exercise 3 costmap monitor (or `ros2 topic echo`) to record the FREE / INFLATED / LETHAL percentages, and send a goal *through a doorway* to record whether the planner produces a path. Build a table in `notes/week-17/inflation-sweep.md`.

**Acceptance criteria.**

- `notes/week-17/inflation-sweep.md` has a row per radius with the three percentages and a "doorway path?" yes/no.
- You show that as the radius grows, INFLATED rises and FREE falls, and identify the radius at which the doorway becomes impassable.
- A one-sentence conclusion stating the trade-off (clearance vs. reachability) in your own words.
- Committed.

**Hint.** `ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap "{}"` forces a rebuild after a `param set`. If the doorway is wide, you may need a larger radius to block it — measure your doorway width first.

**Estimated time.** 45 minutes.

---

## Problem 3 — Read the navigation BT and predict the recovery

**Problem statement.** Open the default `navigate_to_pose_w_replanning_and_recovery.xml` (find it under `/opt/ros/jazzy/share/nav2_bt_navigator/behavior_trees/`). In `notes/week-17/bt-reading.md`, answer: (a) what is the outermost control node and what does it do? (b) list the recovery subtree's behaviors in order; (c) trace, step by step, what happens when `ComputePathToPose` returns `FAILURE` once, then succeeds; (d) trace what happens when it fails repeatedly until retries are exhausted.

**Acceptance criteria.**

- `notes/week-17/bt-reading.md` answers all four parts with reference to specific node names from the XML.
- Your trace of "fail once then succeed" correctly shows the `RecoveryNode` clearing the costmap and retrying *before* dropping to the recovery subtree.
- Your trace of "fail repeatedly" correctly shows the round-robin recovery behaviors firing and the outer `RecoveryNode` looping.
- Committed.

**Hint.** Match each XML node against the Lecture 2 §2.2 control-node descriptions. The key insight: there are *nested* `RecoveryNode`s — a per-leaf one (clear-and-retry) and an outer one (the full recovery subtree). The robot only spins/backs-up after the per-leaf retries are exhausted.

**Estimated time.** 45 minutes.

---

## Problem 4 — The fail-safe declaration (headline deliverable)

**Problem statement.** This is the syllabus deliverable: *what does the robot do if the planner crashes mid-goal?* Reproduce the fault (deactivate or kill `planner_server` mid-goal while Exercise 2's client runs), capture the behavior, and write a one-page fail-safe declaration at `notes/week-17/failsafe-planner-crash.md` against this template:

1. **Hazard** — one sentence: what physically goes wrong if the planner crashes and nothing intervenes (the robot coasts on a stale plan).
2. **Detection** — how the fault is detected, and the *latency* of detection (the feedback-timeout value, the bond timeout, the action result status). Quote the actual log line from your run.
3. **Response** — what the robot does when the fault is detected (publish zero `Twist`, route through the velocity smoother, alert the operator), and the latency from detection to the base actually stopping.
4. **Why the BT alone is insufficient** — explain that a crashed server hangs the BT leaf in `RUNNING` with no `FAILURE` to recover from.
5. **Residual risk** — what this fail-safe does *not* cover (e.g., a crash during the stop itself, a wedged-but-not-dead planner that still publishes stale plans).
6. **Test evidence** — the command you ran to inject the fault and the observed before/after `/cmd_vel`.

**Acceptance criteria.**

- `notes/week-17/failsafe-planner-crash.md` exists, fits on roughly one page (350–550 words), and hits all six headings.
- The detection section states a *concrete* latency and quotes a real diagnostic line.
- The "why the BT alone is insufficient" section is mechanically correct (crash → silent → no `FAILURE`).
- The residual-risk section names at least one real gap, not "none."
- Committed.

**Hint.** Run Exercise 2's client, then `ros2 lifecycle set /planner_server deactivate` (or kill the process) after the first feedback line. The client's feedback-timeout fail-safe fires after `FEEDBACK_TIMEOUT_S`. Quote that `FAIL-SAFE engaged` line. For the residual risk, the honest gap is: the client stops the base, but if it *too* dies, nothing does — which is why a real robot also has a hardware E-stop (Week 24).

**Estimated time.** 1 hour.

---

## Problem 5 — Swap the planner and compare

**Problem statement.** Run a goal under the default `NavfnPlanner`. Then change `planner_server.GridBased.plugin` to `nav2_smac_planner/SmacPlannerHybrid`, restart, and run the *same* goal. Capture both `/plan` paths (screenshot from rviz2 or echo the poses) and compare path shape, especially turning behavior. Record in `notes/week-17/planner-swap.md`.

**Acceptance criteria.**

- `notes/week-17/planner-swap.md` shows both planners' paths for the same start/goal.
- You note at least one concrete difference (Hybrid-A* respects a minimum turning radius and produces smoother, car-like curves; NavFn produces grid-aligned, sharper paths).
- You state which planner suits a diff-drive robot vs. an Ackermann robot and why. (Previews Week 18.)
- Committed.

**Hint.** Hybrid-A* needs a few extra params (`motion_model_for_search: "DUBIN"` or `"REEDS_SHEPP"`, `minimum_turning_radius`). Crib them from the Nav2 SMAC planner docs. On a diff-drive robot that can spin in place, NavFn is often fine; the turning-radius constraint matters for cars.

**Estimated time.** 40 minutes.

---

## Problem 6 — Wire a pre-flight health check

**Problem statement.** Write a script `crunchbot_nav/scripts/nav2_health.sh` that, against a running stack: (a) runs `ros2 lifecycle get` on every Nav2 server and flags any not `active [3]`; (b) confirms `tf2_echo map base_link` returns a transform; (c) confirms `/global_costmap/costmap` is non-empty (has lethal cells). It must exit `0` when all checks pass and non-zero when any fails. Prove it by running it against a healthy stack (exit 0) and a stack with one server deactivated (exit non-zero).

**Acceptance criteria.**

- Running against a healthy stack prints a pass summary and `echo $?` shows `0`.
- Running against a stack with one server deactivated prints which check failed and `echo $?` shows non-zero.
- Both runs captured in `notes/week-17/health-check.md`.
- Committed.

**Hint.** The exit code is what makes it a pre-launch gate, not a pretty printer — accumulate failures and `exit 1` at the end if any. For the costmap-non-empty check, `ros2 topic echo /global_costmap/costmap --once` and grep for a `100` in the data, or call your Exercise 3 monitor once. To break one server: `ros2 lifecycle set /planner_server deactivate`.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Lifecycle audit table | 40 min |
| 2 — Costmap inflation sweep | 45 min |
| 3 — Read the navigation BT | 45 min |
| 4 — Fail-safe declaration (headline) | 1 h 0 min |
| 5 — Planner swap and compare | 40 min |
| 6 — Pre-flight health check | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_nav` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 24's integration imports it. Then take the [quiz](./05-quiz.md) with your notes closed.
