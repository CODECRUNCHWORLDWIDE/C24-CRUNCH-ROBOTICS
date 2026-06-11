# Mini-Project — The Phase 4 Milestone: A Wrapped Learned Policy With a Leash

> Deliver your **best learned policy from Weeks 29–31, wrapped in a runtime safety filter and a classical fallback**, completing a constrained pick-and-place with a **measured intervention rate** — and defend the whole stack at the **second-midterm architecture review**. This is the **Phase 4 milestone**: the moment a learned policy stops being a notebook result and becomes a shippable robot. When the milestone is signed and you pass the midterm review, Phase 5 (sim-to-real) opens.

**Estimated time:** ~14 hours (split across Thursday through Sunday in the suggested schedule).

This is the milestone that gates *learning*, the way the Week-16 first midterm gated perception. It is not a new policy — it is your *existing* best policy, made *deployable*. You are not improving the success rate this week; you are adding the leash that lets you ship the success rate you have: the predictive safety filter that catches the confidently-wrong action, the classical fallback that finishes the task when the policy is stuck, and the intervention meter that proves — with numbers, not adjectives — that the leash works. The deliverable is graded as a milestone (10% of the track, per the assessment matrix) and defended live at the second-midterm review (another 10%, shared with the Week-16 review under "architecture-review writeups").

This mini-project **compounds forward.** The safety wrapper you build here is the leash that protects the *transferred* policy in Phase 5 (Week 34, sim-to-real), the safety layer of the full mobile manipulator at Week 40, and one of the three flagship portfolio projects ("the learned-policy + classical-fallback stack") at graduation. Build it well now; you defend it three more times before you graduate.

---

## What you will build

A single composed system, brought up under one launch graph in safety-first order, that executes this run with the leash live and measured:

```bash
# Bring up the policy + filter + fallback + controller under the lifecycle manager.
ros2 launch crunch_policy_stack pick_place.launch.py

# Run the focused eval: N episodes of the constrained pick-and-place, with the
# wrapper and fallback live and the intervention meter counting.
ros2 run crunch_policy_stack eval_episodes --episodes 40
```

The system, for each episode:

1. **Perceives** — the perception + grasp pipeline localizes the object and proposes a grasp.
2. **Proposes** — the learned policy (Diffusion Policy / ACT / VLA) emits the candidate action.
3. **Filters** — the safety filter rolls the action forward, checks the constraint set, and PASSes / CLAMPs / REJECTs. It is active *before* any controller can execute a learned action.
4. **Switches** — on three consecutive rejections, the BT `ReactiveFallback` hands the task to the classical planner (MoveIt2 + OMPL / a sampling planner), which completes it deterministically.
5. **Measures** — the intervention meter counts every clamp, rejection, and fallback, and reports the breakdown at the end of the run.

By the end you have a public repo, a launch graph that brings the wrapped policy up in one command, a measured intervention-rate report, an ablation that proves the leash is load-bearing, an updated hazard log, and a signed milestone plus a passed midterm review.

---

## Why this is a milestone, not a feature

The previous milestones gated phases: the Phase 1 architecture review, the first midterm (perception), the Phase 3 sign-off (planning + control). This one gates *Phase 4* — manipulation and learning. The skill it certifies is the one that separates a research demo from a deployable robot: **you can take an unverified learned controller and make it safe to run, prove it, and defend the architecture to a skeptical panel.** A learned policy with a great success rate and no leash is a Phase 4 *fail*, because it is not shippable. A learned policy with a defensible safety wrapper, a working fallback, and an honest intervention rate is a Phase 4 *pass* — and the seed of the capstone's policy layer.

---

## Package layout

One umbrella package that wraps your existing policy, plus the artifacts you scaffolded this week:

```
crunch_ws/src/
└── crunch_policy_stack/                     # ament_python (the wrapper/integrator)
    ├── crunch_policy_stack/
    │   ├── __init__.py
    │   ├── action_bounds.py                 # Exercise 1: the constraint set + clamps
    │   ├── safety_filter.py                 # Exercise 2: the predictive filter, productionized
    │   ├── fallback_meter.py                # Exercise 3: the 3-strike switch + intervention meter
    │   ├── lifecycle_manager.py             # ordered, safety-first bring-up (filter before controller)
    │   └── eval_episodes.py                 # runs N episodes, drives the meter, prints the report
    ├── bt/
    │   └── pick_place.xml                   # the BT with the ReactiveFallback leash
    ├── launch/
    │   └── pick_place.launch.py             # brings up policy + filter + fallback + controller
    ├── config/
    │   ├── bounds.yaml                      # operator-override layer over action_bounds.py defaults
    │   └── moveit_params.yaml               # the classical fallback (from Week 23)
    ├── safety-case/
    │   └── hazard-log-learned-policy.md     # the learned-policy hazard update (homework P6)
    ├── notes/
    │   ├── intervention-rate.md             # the headline report (homework P4)
    │   ├── ablation.md                      # filter-on vs filter-off (homework P5)
    │   └── midterm-dry-run.md               # the challenge dry run
    ├── setup.py
    └── package.xml
```

The `crunch_policy_stack` package does **not** re-train or re-implement the policy — it *wraps* the policy you already built and composes it with the filter, the fallback, and the meter. Its own code is the leash: the constraint set, the filter, the switch, the meter, and the ordered bring-up.

---

## Functional requirements

### R1 — One launch graph brings the wrapped policy up

`pick_place.launch.py` brings up, in the safety-first order: the sim + bridge, the perception/grasp pipeline, the learned policy node, the **safety filter** (active before any controller can execute a learned action), the controller and the classical fallback planner, the behavior tree, and the intervention meter. One command. No second terminal of manual `ros2 run` calls.

### R2 — The safety filter is in the action path, and active first

`safety_filter.py` (Exercise 2, productionized) sits between the policy and the controller. **Every** learned action passes through it; no action reaches a controller unfiltered. The lifecycle manager activates the filter *before* the controller can command the robot — the leash goes on first among the things that can move the robot. This is a safety property, verifiable in the bring-up log order.

### R3 — The predictive filter PASSes, CLAMPs, or REJECTs

The filter rolls each candidate action forward through a model over a short horizon and checks the constraint set from `action_bounds.py`: velocity, acceleration, joint limits, workspace bounds, keep-out. It CLAMPs (uniform rescale / projection) a rescalable over-limit action and REJECTs an action with no nearby safe projection (a through-the-table grasp). The filter's per-action p95 latency is measured and is well under the policy's inference latency.

### R4 — The three-rejection fallback switch

`fallback_meter.py` (Exercise 3) tracks consecutive rejections. On the third *consecutive* rejection, the BT `ReactiveFallback` switches from the learned-policy branch to the classical planner, which completes the task. The counter resets on any safe action. The switch is visible in Groot 2.

### R5 — The classical fallback completes the task

The fallback is a *real* planner (MoveIt2 + OMPL for the arm, a sampling planner for the base), not an error message. When it fires, it plans and executes a verified trajectory that respects the constraint set by construction and completes the pick-and-place. An episode where the fallback fires and completes the task counts as a success *and* an intervention — and the report says both.

### R6 — The intervention rate, measured honestly

`eval_episodes.py` runs N episodes (≥ 30) and reports: success rate, clamps by constraint, rejections, fallback-episode rate, and filter p50/p95 latency vs. policy inference time. Report the numbers you get, not the numbers you want. A high success rate with a high fallback rate is disclosed as "the policy is being carried by the planner."

### R7 — The wrapper actually fires (no decorative leash)

Across the eval, the filter must clamp and reject *something*, and the ablation (R8) must show the filter catching real unsafe actions. A wrapper that never fires over the whole eval is the too-loose-filter defect and **caps the milestone**, because it provides no protection while looking like success. If your policy is clean enough that nothing trips the filter naturally, you must demonstrate the filter *can* fire (inject an OOD observation) and report that you did.

### R8 — The ablation proves the leash is load-bearing

`notes/ablation.md` compares filter-on vs. filter-off over the same episodes, naming the unsafe actions that execute with the filter off (table-strikes, over-speed twists, out-of-workspace reaches) that the filter caught with it on. Run in sim only. This is the strongest evidence for the midterm panel.

### R9 — The hazard log is updated for learned controllers

`safety-case/hazard-log-learned-policy.md` (homework P6) lists the learned-policy hazards — OOD action, multimodal collapse, silent confidence, reward hacking, filter latency, too-loose filter — each with a mitigation and an owning artifact. This is the seed of the Week-41 safety case.

---

## Rules

- **You may** reuse your trained policy from Weeks 29–31, your MoveIt2/Nav2 setup, your BT from Week 19, your Week-24 hazard log, and the ROS2 Jazzy / MoveIt2 / BT.CPP docs.
- **You must** target ROS2 **Jazzy** on **Ubuntu 24.04**, with Gz Sim (Harmonic) or Isaac Sim. `rclpy` for the wrapper nodes; `rclcpp` / BT.CPP for the behavior tree (the tree is C++ per Week 19).
- **You must** bring the wrapped policy up with **one launch command** under a lifecycle manager, with the **safety filter active before any controller can command the robot**. A bring-up that lets a learned action reach a controller before the filter is active is a safety defect.
- **You must** put the safety filter in the action path — **no learned action reaches a controller unfiltered.** A policy wired directly to a controller, with the filter as a side-observer, fails R2.
- **You must** treat a wrapper that never fires over the whole eval as the too-loose-filter defect (R7), not a clean run.
- **You must not** hard-code the grasp to bypass the policy, and **you must not** disable the fallback to inflate the success rate — both fail the milestone.

---

## Acceptance criteria

- [ ] A public repo named `c24-week-32-crunch-policy-stack-<yourhandle>`.
- [ ] `colcon build` of `crunch_policy_stack` and its dependencies succeeds with no errors.
- [ ] `ros2 launch crunch_policy_stack pick_place.launch.py` brings the wrapped policy up in one command; the lifecycle log shows the **safety filter active before the controller**.
- [ ] The safety filter is in the action path; `ros2 topic info /policy/filtered_action -v` shows it is the controller's input, not the raw policy.
- [ ] Over an eval of ≥ 30 episodes, the filter clamps and rejects actions, and the BT fallback fires on at least the stuck-policy episodes (demonstrated, or via an injected OOD observation if the policy is too clean).
- [ ] `eval_episodes.py` reports the intervention-rate breakdown (success, clamps-by-constraint, rejections, fallback rate, latency) and it is recorded in the repo README.
- [ ] `notes/ablation.md` shows the filter-on-vs-off comparison with at least one named unsafe action caught.
- [ ] The BT `ReactiveFallback` is viewable in Groot 2 and the three-rejection switch is demonstrated.
- [ ] `safety-case/hazard-log-learned-policy.md` lists ≥ 6 learned-policy hazards with mitigations and owning artifacts.
- [ ] You **pass the second-midterm architecture review** (defend the five artifacts live; see the challenge for the dry run).

---

## Grading rubric (100 points)

| Area | Points | What earns them |
|------|-------:|-----------------|
| **One-command bring-up + safety-first order** | 10 | Whole wrapped policy up in one launch; filter active before the controller; verifiable in the log. |
| **Filter in the action path** | 15 | Every learned action filtered; filter is the controller's input; PASS/CLAMP/REJECT all demonstrated. |
| **Predictive filter correctness** | 15 | Roll-forward + constraint check; correct uniform-rescale clamp; rejects the through-the-table action; p95 latency under the policy's. |
| **Three-rejection fallback** | 15 | `ReactiveFallback` in Groot 2; switch on 3 consecutive rejections; counter resets; the classical planner completes the task. |
| **Intervention rate, measured** | 15 | Five numbers with methods over ≥ 30 episodes; fallback rate disclosed honestly. |
| **The ablation** | 10 | Filter-on-vs-off; named unsafe action caught; sim-only. |
| **Hazard-log update** | 10 | Six+ learned-policy hazards with mitigations and owning artifacts; reward-hacking → eval bridge. |
| **The midterm defense** | 10 | The five artifacts defended live; intervention rate as the headline; the rubric read as a contract. |

A submission whose filter never fires (too-loose defect), or whose policy is wired directly to a controller bypassing the filter, or whose fallback is disabled to inflate the success rate, **caps at 50 points** regardless of polish. The leash being *real* — the filter in the path, firing, with a fallback that completes the task — is the milestone's load-bearing property, and the rubric weights it accordingly.

---

## How this compounds into the rest of the track

| Week | What it does with the wrapped policy |
|------|--------------------------------------|
| **33 — Sim comparison** | The wrapped policy is one of the workloads you compare across Gz Sim and Isaac Sim. |
| **34 — Domain randomization + sim-to-real** | The leash protects the *transferred* policy when its real-world state distribution diverges from sim — exactly the situation DR is about. |
| **37 — VLA as policy** | The VLA's grasp pose passes through this same safety filter before execution. |
| **40 — Full integration** | This wrapper is the safety layer of the full mobile manipulator; the filter and fallback are wired into the capstone stack. |
| **41 — Safety case** | The learned-policy hazard log becomes part of the portfolio-quality 8–15-page safety case. |
| **48 — Portfolio + defense** | "The learned-policy + classical-fallback stack" is one of the three flagship portfolio projects. |

Build it once, wrap it well, measure it honestly, defend it cleanly, and it carries you to graduation as both a capstone layer and a portfolio piece. That is why this is a milestone and not a feature.

---

## Submission

Push to your public repo, tag it `week-32-milestone`, and open the repo's README with: the policy you wrapped, the intervention-rate breakdown (the five numbers), the ablation result, and a one-line confirmation that the filter fires and the fallback completes the task. In your cohort channel, post the repo link and the screen recording of the live rejection and live fallback. Schedule the second-midterm architecture review: the panel watches the wrapper fire, watches the fallback switch, reads your intervention rate and ablation, probes your hazard log, and signs — or sends you back to the artifact that didn't hold up. The signed milestone *and* the passed review are the gate into Phase 5. Eight weeks of Phase 4 done; sixteen weeks left.
