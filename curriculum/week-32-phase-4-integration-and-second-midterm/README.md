# Week 32 — Phase 4 Integration: Ship the Learned Policy With a Leash, Then Defend It

Welcome to **C24 · Crunch Robotics**, Week 32 — the last week of Phase 4 and the **second midterm**. For seven weeks you taught a robot to manipulate and to *learn*: grasp candidates from a point cloud, Contact-GraspNet picking real objects, behavior cloning and the DAgger fix for covariate shift, PPO and SAC in parallel sim, a Diffusion Policy that ate the multimodal-action problem, an Action Chunking Transformer that deploys at interactive latency, and a fine-tuned OpenVLA that turns an English sentence into a grasp. This week you take your **best** learned policy from that run and do the one thing that separates a research demo from a shippable robot: you **wrap it in a safety filter and a classical fallback**, measure how often the leash actually pulls, and then **defend the whole stack to a panel** against a written rubric.

That is the deliverable, and it is graded twice — once as the Phase 4 milestone (the mini-project, the wrapped policy with a measured intervention rate) and once as the **second midterm architecture review** (a live panel session, 10% of the track per the assessment matrix, where you defend your training pipeline, your eval protocol, your safety wrapper, your fallback path, and your updated hazard log). The first midterm at Week 16 gated perception. This one gates *learning*. A learned policy that works in the notebook but cannot be shipped with a safety case is not a Phase 4 pass — it is a Phase 4 liability.

The first thing to internalize is that **a learned policy is an unverified controller, and you never ship an unverified controller without a leash.** Every controller you built in Phase 3 — PID, LQR, MPC — came with a stability argument. You could write down the closed-loop poles, or the Lyapunov function, or the constraint set, and *prove* the thing would not run away. A Diffusion Policy has no such argument. It is a noise-prediction network trained on a finite dataset, and at a state the data never covered it will emit an action that is confident, plausible-looking, and wrong. The action might drive the gripper through the table, command a base velocity of 4 m/s in a shared room, or reach to a workspace pose that puts the elbow where a person's head is. None of that shows up in a success-rate number on a held-out eval set. It shows up the first time the policy meets a state distribution that differs from training — which, on a real robot in a real room, is *always*. The safety wrapper is the controller-theory you do have when the learned-policy theory you don't have fails.

The second thing to internalize is that **the safety wrapper is a predictive filter, not a reactive clamp.** A naive clamp says "if the commanded velocity exceeds the limit, saturate it." That is necessary but not sufficient, because saturation can itself be unsafe — clamping one joint of a coordinated arm trajectory desynchronizes the others, and clamping a base velocity mid-turn changes the path. The senior pattern is a **predictive safety filter** (the control-barrier-function / MPC-shield family): before the learned action is executed, you *roll it forward* through a model for a short horizon, check whether the predicted trajectory violates any constraint (velocity, acceleration, joint limits, workspace bounds, a keep-out volume around detected people), and if it would, you either project the action to the nearest safe one or *reject it outright* and hand control to the fallback. The filter is a small, verifiable piece of classical control wrapped around an unverifiable learned policy — which is exactly the architecture every serious learned-manipulation deployment ships in 2026.

The third thing to internalize is that **the fallback is a real controller, not an error message.** When the safety filter rejects the learned action three times in a row — the exact number the capstone spec fixes — the robot does not stop and wait for a human. It transitions, via a behavior-tree branch, to a **classical motion planner** (MoveIt2 + OMPL for the arm, a sampling planner for the base) that completes the task the slow, deterministic, verifiable way. The learned policy is the fast path; the classical planner is the safe path; the safety filter is the switch between them. This is the "learned policy with a leash" pattern, and the BT is where the leash is wired. A stack that rejects a bad action but has nowhere to go is a stack that fails the task; a stack that falls back to a planner that finishes it is a stack that ships.

The fourth thing to internalize is that **the intervention rate is the number that matters, and you measure it honestly.** "My policy has 92% success on the eval set" is a research number. "My safety filter rejected 6% of actions and the fallback took over on 3% of episodes" is a *deployment* number, and it is the one a reviewer trusts. A policy with 92% success and a 30% intervention rate is worse than a policy with 85% success and a 2% intervention rate, because the second one is doing the work and the first one is being carried by its fallback. The midterm review will ask you for the intervention rate, the rejection breakdown by constraint, and the distribution of *which* fallback fired — and "it felt safe" does not answer the question. This week you instrument the wrapper to count every clamp, every rejection, every fallback, and you report the distribution, not an adjective.

## Learning objectives

By the end of this week, you will be able to:

- **Wrap** any learned policy (Diffusion Policy, ACT, or a fine-tuned VLA) in a runtime safety filter that rejects actions exceeding velocity, acceleration, joint-limit, or workspace bounds before they reach the controller, and that does so within a bounded per-action latency budget.
- **Design** a predictive safety filter — the control-barrier-function / MPC-shield pattern — that rolls a candidate action forward through a model, checks the predicted trajectory against a constraint set, and projects-or-rejects, rather than naively saturating.
- **Wire** a classical-fallback branch into a behavior tree that takes over from the learned policy after exactly three consecutive safety rejections, completing the task with a deterministic, verifiable planner.
- **Measure** the deployment numbers that matter — intervention rate, rejection count by constraint, fallback-trigger distribution, and per-action filter latency — and report them as distributions, not adjectives.
- **Compose** the Phase 4 stack into one graph: perception → grasp/policy → safety filter → controller/fallback → behavior tree, brought up cleanly under a lifecycle manager with the safety filter active before any motion.
- **Update** the hazard log from Week 24 with the new failure modes a learned policy introduces — out-of-distribution actions, silent confidence collapse, reward-hacked behaviors — and map each to a mitigation with an owning artifact.
- **Defend** the learned-policy stack to a panel against the second-midterm rubric: the training pipeline, the eval protocol, the safety wrapper, the fallback path, and the hazard-log update.
- **Diagnose** the four canonical learned-policy deployment defects: the out-of-distribution action, the multimodal-collapse-into-the-mean, the silent-confidence failure, and the fallback that never fires because the filter is too loose.

## Prerequisites

This week assumes you have completed **Weeks 25–31** of C24, or have the equivalent learned-manipulation components already built and tested. Specifically:

- **A best learned policy (Weeks 29–31).** A trained Diffusion Policy, an ACT, or a fine-tuned OpenVLA that completes a constrained pick-and-place at some success rate on a held-out eval set. This week it becomes the *fast path* inside a safety-wrapped stack — not the whole stack.
- **MoveIt2 for the arm (Week 23) and a sampling planner for the base (Weeks 17–18).** The classical fallback is a real planner, and these are it. They bring up cleanly and accept goals through their action interfaces.
- **A behavior tree (Week 19).** BT.CPP authoring, control/decorator/condition nodes, Groot 2. The leash — the switch from learned policy to fallback — is a BT branch, and you write it this week.
- **The Week 24 hazard log and the safety primer.** The hazard-log practice, fail-safe categories, the software E-stop with a 200 ms latch. This week you expand the log with learned-policy-specific hazards.
- **The grasp + perception pipeline (Weeks 25–26).** Contact-GraspNet or a heuristic grasp sampler feeding a perceived object pose, so the policy has a scene to act in.
- **A working ROS2 Jazzy on Ubuntu 24.04**, a Gz Sim (Harmonic) or Isaac Sim install that runs your arm + base, and a GPU that runs your policy at interactive latency (or a documented Path-B substitution).

You do **not** need any new learning architecture this week. Week 32 introduces almost no new policy API. It introduces a new *discipline*: wrapping the unverified thing in a verified thing, measuring how often the wrapper fires, and defending the whole composition to a panel. The hard part is not training — it is making a learned policy *shippable*.

## Topics covered

- **The learned-policy-plus-classical-fallback pattern.** Why every serious learned-manipulation deployment ships a fast learned path and a slow verifiable path with a switch between them; where the switch lives (the BT); and why "three rejections" is the spec's chosen threshold.
- **Safety scaffolds around learned policies.** The taxonomy of runtime guards: action clamps (velocity, acceleration, jerk), state guards (joint limits, workspace bounds, keep-out volumes), and confidence gates (reject actions whose source model reports low confidence or whose multimodal distribution has collapsed).
- **Trajectory clamping done right.** Why naive per-action saturation desynchronizes coordinated trajectories; clamping at the trajectory level (rescale time, not amplitude); the difference between clamping a base twist and clamping an arm joint vector.
- **Predictive safety filters.** The control-barrier-function (CBF) and MPC-shield families: roll the candidate action forward through a model, evaluate the constraint set over the predicted horizon, and project-to-nearest-safe or reject. The latency budget of the filter and why it must be cheaper than the policy it wraps.
- **The intervention-rate metric and its breakdown.** Rejection count by constraint, fallback-trigger distribution, per-action filter latency, and why the intervention rate is a better deployment signal than the success rate.
- **The four learned-policy deployment defects.** The out-of-distribution action (confident and wrong at an unseen state), the multimodal-collapse-into-the-mean (a policy that averages two good actions into one bad one), the silent-confidence failure (the model is wrong but reports high confidence), and the too-loose filter (a wrapper whose bounds never trip, so the fallback never fires and the leash is decorative).
- **The hazard-log update for learned controllers.** Expanding the Week 24 log with OOD actions, confidence collapse, and reward-hacked behaviors; mapping each to a runtime mitigation; the FMEA row for "the policy commands a confident but wrong action."
- **The second-midterm architecture review.** The review format, the rubric (training pipeline, eval protocol, safety wrapper, fallback path, hazard log), and how to defend a learned-policy stack to a panel that did not build it.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — though this is a midterm week, so the Sunday review block is non-negotiable. Integration and safety-filter work is best done in long blocks: you need the full stack, the sim, and the introspection tools live at once, and context-switching out of a half-tuned safety filter is the most expensive thing you can do this week.

| Day       | Focus                                                            | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The leash pattern; safety scaffolds; clamps vs predictive filters |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Predictive safety filter (CBF/MPC-shield); roll-forward + reject  |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Compose the stack; wire the fallback BT branch; intervention rate |    1.5h  |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | Measure the wrapper; the four defects; the challenge             |    0.5h  |    0h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Mini-project — the wrapped policy with a measured intervention rate |  0h    |    0h     |     0h     |    0.5h   |   1h     |     3h       |    0.5h    |     5h      |
| Saturday  | Mini-project deep work; hazard-log update; review prep            |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, midterm-review rehearsal, hazard-log polish                |    0h    |    0h     |     0h     |    1h     |   0h     |     3h       |    0h      |     4h      |
| **Total** |                                                                  | **6h**   | **5.5h**  | **2h**     | **3.5h**  | **5h**   | **14h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The safe-RL, control-barrier-function, MPC-shield, learned-policy-deployment, and architecture-review references that matter in 2026 |
| [lecture-notes/01-ship-the-learned-policy-with-a-leash.md](./lecture-notes/01-ship-the-learned-policy-with-a-leash.md) | Why a learned policy is an unverified controller; the safety-scaffold taxonomy; trajectory clamping; the classical-fallback pattern and the three-rejection switch |
| [lecture-notes/02-predictive-safety-filters-and-the-midterm-defense.md](./lecture-notes/02-predictive-safety-filters-and-the-midterm-defense.md) | The CBF / MPC-shield predictive filter; the intervention-rate metric; the four deployment defects; the hazard-log update; defending the stack at the second-midterm review |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-bound-the-action-space.md](./exercises/exercise-01-bound-the-action-space.md) | Guided: build the constraint set for your robot — velocity, acceleration, joint-limit, and workspace bounds — and the action-bounds check that uses it |
| [exercises/exercise-02-runtime-safety-filter.py](./exercises/exercise-02-runtime-safety-filter.py) | Runnable: a predictive safety filter node that rolls a candidate action forward, checks the constraint set, and projects-or-rejects, counting every clamp and rejection |
| [exercises/exercise-03-fallback-and-intervention-rate.py](./exercises/exercise-03-fallback-and-intervention-rate.py) | Runnable: the three-rejection fallback switch and an intervention-rate meter that reports rejections-by-constraint and fallback-trigger distribution |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-defend-the-stack.md](./challenges/challenge-01-defend-the-stack.md) | A dry-run of the second-midterm review: defend your learned-policy stack against the rubric to a peer panel, with the wrapper firing live |
| [quiz.md](./quiz.md) | 13 multiple-choice questions with an answer key |
| [homework.md](./homework.md) | Six practice problems with deliverables and a rubric |
| [mini-project/README.md](./mini-project/README.md) | Full spec for the **Phase 4 milestone** — the wrapped learned policy with a classical fallback and a measured intervention rate |

## The "measured intervention rate" promise

C24 has had a recurring marker since Week 4 — every node that commands the robot stops it on every exit path. Week 32 adds the promise Phase 4 has been building toward:

```
[capstone_pick] policy=diffusion fallback=moveit_ompl episodes=40
[capstone_pick]   success:        37/40 (92.5%)
[capstone_pick]   filter latency: p50=2.1ms  p95=4.8ms  (policy infer p50=31ms)
[capstone_pick]   clamps:         velocity=11  accel=4  workspace=2   (of 1,840 actions)
[capstone_pick]   rejections:     22 actions across 6 episodes
[capstone_pick]   fallback fired: 3 episodes (7.5%)  -> all 3 completed by moveit_ompl
[capstone_pick]   intervention rate (episodes touched by the leash): 7.5%
```

If your wrapper never fires — zero clamps, zero rejections, zero fallbacks over forty episodes — the leash is decorative, not real, and that is a defect, not a clean run. A safety filter whose bounds are so loose they never trip is the **too-loose-filter** defect from Lecture 2, and the panel will catch it. The point of Week 32 is to make this measured-intervention line ordinary, and to make every number on it a measurement you can defend — including, especially, the line that proves the leash actually pulls.

## A note on what's not here

Week 32 wraps the policy, wires the fallback, and defends the stack. It does **not** cover:

- **Sim-to-real transfer.** Closing the gap between your sim policy and a real robot is **Weeks 33–34** (Phase 5). This week the policy runs in the same sim it trained in; the safety wrapper is what makes it *deployable*, not yet *transferred*.
- **The full capstone integration.** Composing the *entire* autonomy stack — nav + perception + VLA + the full mobile manipulator — end to end is the **Week 40** milestone. This week is the *learning* slice of that stack, wrapped and defended.
- **The 20-instruction eval suite.** Scoring twenty language-conditioned instructions is **Week 44**. This week you run a focused eval (tens of episodes on one task) to *measure the intervention rate*, not to score a suite.
- **The portfolio-quality safety case.** You **update the hazard log** this week with learned-policy failure modes; the 8–15-page safety case is the **Week 41** artifact. The hazard-log update is the seed of it.

The point of Week 32 is a sharp, load-bearing skill: take a thing that learned, prove you can stop it when it is wrong, give it somewhere safe to go when you do, measure how often that happens, and defend the whole architecture to someone who will not extend you the benefit of the doubt. That is what makes a learned policy a shippable robot instead of a notebook result.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement the safety filter as a true **control barrier function** with a QP solver (`qpOASES`, `OSQP`, or `cvxpy` for the prototype): minimize the deviation from the learned action subject to the CBF constraint `ḣ(x) ≥ -α·h(x)`, and compare the projected action to the naive-clamp action on a near-violation: <https://github.com/HybridRobotics/CBF>.
- Build a **confidence gate** that reads the Diffusion Policy's action-sample variance (sample the policy K times, measure the spread) and rejects actions where the spread exceeds a threshold — catching the multimodal-collapse defect before it executes.
- Add an **MPC shield**: instead of a one-step CBF, roll the candidate action through your Week-22 `do-mpc` model for a short horizon and reject if any predicted state violates a constraint. Compare its intervention rate to the one-step filter.
- Stand up a **keep-out volume** around a simulated person (a moving collision primitive) and prove the workspace guard rejects any arm action whose predicted swept volume intersects it.
- Run an **ablation**: disable the safety filter and re-run the forty episodes. Document the unsafe actions that now execute — the table-strikes, the over-speed twists — that the filter previously caught. This ablation is the strongest possible evidence for the midterm panel that the leash is load-bearing.

## Up next

Continue to **Week 33 — Gazebo, Gz Sim, and Isaac Sim Compared** once your milestone is signed and you have passed the second-midterm review. Phase 5 opens by asking a question Phase 4 deliberately deferred: your wrapped, defended policy works in sim — but *which* sim, and will it survive contact with the real world? Week 33 compares the simulators you will train and transfer in; Week 34 teaches the domain randomization that closes the sim-to-real gap. The safety wrapper you build this week becomes the leash that protects the *transferred* policy when its real-world state distribution diverges from sim — which is exactly the situation sim-to-real is about. The leash you build for the sim policy is the leash that makes the real one safe.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
