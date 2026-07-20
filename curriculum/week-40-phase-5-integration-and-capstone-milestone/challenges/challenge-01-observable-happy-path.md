# Challenge 1 — The Observable Happy-Path Pick-and-Place

**Estimated time:** ~2 hours (after the full stack is composed). **No starter file** — you architect this from your own components.

## The challenge

Demonstrate a clean, happy-path, language-conditioned pick-and-place in which **every layer of the autonomy stack is observable in telemetry**, with **no manual intervention**, from the moment the instruction is issued to the moment the object is placed.

The robot takes the instruction *"bring me the red cup from the left bench."* It localizes the cup (perception), drives to the bench (planner + controller), the VLA selects the grasp (policy), the arm executes it under MoveIt2, the safety wrapper supervises throughout, and the cup ends up at the delivery pose. Nobody touches the keyboard after the instruction is issued.

That is the easy half. The hard half — the half this challenge grades — is that a reviewer watching **only your Foxglove dashboard**, with the terminal hidden, can narrate the entire run, layer by layer, in real time. Perception lights up when the cup is detected. The planner's path appears. The controller's pose tracks along it. The policy's grasp pose appears in the policy panel. The safety status stays `clear` (and you can point at the panel that would flash if it didn't). The heartbeat ticks at 1 Hz throughout. If any layer goes dark on the screen, that layer is invisible, and an invisible layer fails the challenge — even if the robot completed the task.

## Why this is the right challenge for Week 40

The Week 40 milestone is explicitly *not* "the robot did a pick-and-place." It is "every layer was observable while it did one, with no manual intervention." This challenge isolates exactly that property and forces you to prove it before the mini-project asks you to sign the milestone against it. Observability is not a nicety you add after the run works — it is the difference between a run you can debug, grade, and survive a chaos drill with, and a run that worked once and can never be explained. A senior robotics engineer instruments first and runs second. This challenge makes you do it in that order.

## What you must build (architect it yourself)

You already have the pieces. The challenge is the wiring:

1. **The composed stack**, brought up under your lifecycle manager in the safety-first order (Lecture 2): sensors → state estimation → perception → planning/control → policy/safety → BT/telemetry.
2. **The pre-flight check** (Exercise 2) wired as a *gate*: the run does not start until pre-flight returns 0. A failed pre-flight aborts loudly; it does not let the run limp forward.
3. **The telemetry spine** (Exercise 3) subscribed to every layer and republishing onto `/telemetry/*` and `/fleet/heartbeat`.
4. **A Foxglove layout**, checked into your repo, with one panel per layer:
   - a **3D panel** showing the base pose, the `tf` tree, the costmap, the detection markers, and the planned path;
   - a **Raw Messages / State panel** for `/telemetry/detections` (the nearest-object summary);
   - a **Raw Messages panel** for `/telemetry/policy` (the VLA grasp pose and accept/reject);
   - a **Raw Messages / Indicator panel** for `/telemetry/safety` (estop, clamps, fallbacks);
   - a **Raw Messages panel** for `/fleet/heartbeat` (id, health, uptime).
5. **A top-level behavior tree** that issues the instruction, ticks perception → Nav2 → VLA → MoveIt2 → place, and dispatches the safety branches — all without a human in the loop.

## Acceptance criteria

Each criterion must be demonstrable by a command you run or a recording you play. If you cannot demonstrate it, it is not met.

- [ ] **Pre-flight gates the run.** `preflight_check` runs first; the run starts only after it exits 0. Demonstrate the abort path too: force one check to fail and show the run refuses to start.
- [ ] **The instruction is the only input.** After "bring me the red cup from the left bench" is issued, no keyboard, `ros2 topic pub`, or `rviz2` action influences the run.
- [ ] **Perception is observable.** When the cup is detected, `/telemetry/detections` updates and the 3D panel shows the detection marker at the cup's `map`-frame position with a confidence ≥ your threshold.
- [ ] **Planning is observable.** The planned base path appears in the 3D panel and `/telemetry/path_summary` reports its waypoint count and length.
- [ ] **Control is observable.** The base pose tracks along the planned path in the 3D panel; `/telemetry/pose` streams continuously.
- [ ] **Policy is observable.** The VLA's selected grasp pose appears in `/telemetry/policy` with `source=vla` and `accepted=True`, before the arm moves.
- [ ] **Safety is observable.** `/telemetry/safety` shows `estop=clear, clamps=0, fallbacks=0` throughout the happy path, and you can point at the panel that would change if a clamp fired.
- [ ] **The heartbeat ticks.** `/fleet/heartbeat` publishes at ~1 Hz (`ros2 topic hz`) with `health=OK` for the whole run.
- [ ] **The task completes.** The cup ends at the delivery pose; the BT reports `SUCCEEDED`.
- [ ] **Zero manual intervention.** You did not touch the keyboard after issuing the instruction. State this explicitly and have it visible in your recording (hide the terminal; the run proceeds anyway).
- [ ] **The narration test passes.** A peer watching only the Foxglove dashboard narrates the run correctly, layer by layer, with no access to logs.

## The narration test, spelled out

Hand a peer your Foxglove dashboard (live, or a recording) with the terminal and logs hidden. Ask them to describe, out loud, what the robot is doing as it does it. A passing narration sounds like:

> "Heartbeat is green at 1 Hz. The robot is idle. Now a detection appeared — there's the red cup at about (1.8, -0.4) with high confidence. A path just popped up to the bench. The base is moving along it. It's arrived. The policy panel shows a VLA grasp pose, accepted. The arm is moving — safety still clear, no clamps. The cup is at the delivery pose. Heartbeat still green."

If your peer can say that without seeing a single log line, every layer is observable and you have met the central criterion. If they say "I can't tell what the policy is doing" or "did it actually detect the cup?", you have a dark layer to wire.

## Deliverable

- A short screen recording (≤ 3 minutes) of the run as seen on the Foxglove dashboard, with the terminal hidden.
- The Foxglove layout file, checked into your repo under `dashboard/milestone-layout.json`.
- A one-paragraph note stating the instruction, confirming zero manual intervention, and naming the peer who passed the narration test.

## Stretch

- Record the run as a `ros2 bag` alongside the video, so the dashboard can be *replayed* from the bag — the artifact a reviewer can re-open and scrub, not just watch.
- Add a synthetic clamp event (nudge a velocity bound) on a *separate* run and show the `/telemetry/safety` panel catch it, to prove the safety layer is not just always-green by construction.

This challenge is the rehearsal for the milestone sign-off and, eight weeks out, for the Week 48 defense. If you can make every layer observable now, the chaos drills at Week 46 — which are *entirely* about detecting and narrating a fault from the dashboard — are a rehearsed play instead of a panic.
