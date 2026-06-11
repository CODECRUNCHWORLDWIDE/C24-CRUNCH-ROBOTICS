# Week 32 — Resources

Every resource on this page is **free** and current to 2026. The safe-RL and control-barrier-function literature lives on arXiv (open). The ROS2 Jazzy, MoveIt2, Nav2, and BehaviorTree.CPP docs are open. The policy papers (Diffusion Policy, ACT, OpenVLA) all have open project pages. No paywalled book is required.

Week 32 introduces almost no new policy API — it is a *discipline* week (wrapping, measuring, defending). The references are therefore weighted toward the **safety-filter, safe-RL, and architecture-review** literature, plus the canonical docs for the components you are composing.

## Required reading (work it into your week)

- **Safe Learning in Robotics (Brunke et al., Annual Review 2022)** — the survey that maps the whole field: safety filters, control barrier functions, safe RL, and the learned-policy-with-a-leash pattern. Read §on safety filters and §on certification:
  <https://arxiv.org/abs/2108.06266>
- **Control Barrier Functions: Theory and Applications (Ames et al.)** — the canonical CBF tutorial; read the QP-based safety-filter section, which is the principled version of "project to the nearest safe action":
  <https://arxiv.org/abs/1903.11199>
- **Predictive Safety Filters (Wabersich & Zeilinger)** — the MPC-shield formulation: roll the candidate action forward and project-or-reject. This is Lecture 2 §1 in its original form:
  <https://arxiv.org/abs/2102.07472>
- **BehaviorTree.CPP — Control nodes (Fallback / ReactiveFallback)** — the node that implements the three-rejection leash switch:
  <https://www.behaviortree.dev/docs/nodes-library/control-nodes/>
- **MoveIt2 — the move_group action interface and TOTG time-parameterization** — your classical fallback and the trajectory-level time-rescaling your clamp imitates:
  <https://moveit.picknik.ai/main/index.html>

## The policies you are wrapping (re-reference)

- **Diffusion Policy (Chi et al., 2023)** — the multimodal action-chunk policy; read the action-chunk execution and the receding-horizon section, which is where the safety filter intercepts:
  <https://diffusion-policy.cs.columbia.edu/>
- **Action Chunking with Transformers / ALOHA (Zhao et al.)** — ACT and the temporal-ensembling deployment trick:
  <https://tonyzhaozh.github.io/aloha/>
- **OpenVLA** — the open-weight VLA you fine-tuned; the policy whose grasp pose the filter guards:
  <https://openvla.github.io/>

## Safety filters and safe RL (the heart of the week)

- **CBF reference implementations (HybridRobotics)** — runnable CBF-QP examples to model your projection on:
  <https://github.com/HybridRobotics/CBF>
- **OSQP** — the quadratic-programming solver for the CBF-QP and the MPC-shield; fast, warm-startable, the right tool for a per-action filter:
  <https://osqp.org/>
- **do-mpc** — your Week-22 MPC library, reused here for the roll-forward model in the predictive filter:
  <https://www.do-mpc.com/>
- **Specification gaming / reward hacking (DeepMind)** — the catalog of RL policies exploiting sim artifacts; the source of the reward-hacking hazard in the Lecture-2 hazard-log update:
  <https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/>
- **Out-of-distribution detection for robot policies** — survey material on OOD detection (the principled confidence gate); search "out-of-distribution detection imitation learning robotics 2024":
  general arXiv survey; the sample-variance gate in Lecture 1 §3.3 is the cheap practical version.

## The architecture-review / safety-case framing

- **NASA Software Safety Guidebook (NASA-GB-8719.13)** — hazard analysis and fault detection/isolation/recovery; the intellectual ancestor of the hazard-log update:
  <https://standards.nasa.gov/standard/NASA/NASA-GB-871913>
- **MIL-STD-1629A — FMEA procedure** — severity × occurrence × detectability → RPN; the structure your hazard-log update grows into at Week 41:
  search "MIL-STD-1629A FMEA"; public domain, widely mirrored.
- **Google SRE Book — Postmortem Culture** — the blameless-postmortem discipline that frames how you report an intervention or a fallback honestly:
  <https://sre.google/sre-book/postmortem-culture/>
- **ISO 13482:2014 — Personal care robots (summary)** — the shared-space-safety framing your hazard log targets:
  <https://www.iso.org/standard/53820.html>

## The components you are composing (re-reference)

- **Nav2 documentation** (the base sampling planner that is the base fallback): <https://docs.nav2.org/>
- **MoveIt2 documentation** (the arm fallback planner, OMPL, the planning scene): <https://moveit.picknik.ai/main/index.html>
- **BehaviorTree.CPP and Groot 2** (the leash, visualized): <https://www.behaviortree.dev/>
- **`ros_gz` bridge** (the ROS2 ↔ Gz Sim bridge): <https://github.com/gazebosim/ros_gz>
- **vision_msgs** (the detection messages the perception layer publishes): <https://github.com/ros-perception/vision_msgs>

## Talks worth your time (free, no signup)

- **"Safe Learning for Robotics"** — search the **ROSCon 2024/2025** and the **Robot Learning Workshop (CoRL)** playlists for the safety-filter and safe-RL talks; the CBF-shield talks are the most relevant.
- **Aaron Ames — Control Barrier Functions** lecture series (on YouTube) — the canonical CBF lectures from the field's originators.
- **"Deploying Learned Policies on Real Robots"** — search CoRL / RSS deployment talks; the recurring theme is exactly this week's: the leash, the fallback, and the intervention rate.

## Tools you'll use this week

- **`OSQP` / `cvxpy`** — the QP for the CBF projection (cvxpy for the prototype, OSQP for the deployment).
- **`do-mpc`** — the roll-forward model for the predictive filter.
- **Groot 2** — to *watch* the fallback fire: the `ReactiveFallback` switching from the policy branch to the classical branch.
- **`ros2 topic echo /policy/filtered_action` / `/safety/status`** — to watch the filter's verdicts live.
- **PlotJuggler** — to plot filter latency and the intervention counters over an eval run.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Learned policy** | A trained network (DP, ACT, VLA) that maps observations to actions. *Unverified.* |
| **Safety filter** | A verified guard between the policy and the controller that clamps, projects, or rejects each action. |
| **Action clamp** | Bounding the action (velocity, accel, joint) before it executes. The cheap reactive guard. |
| **State guard** | Bounding the *predicted state* (workspace, keep-out, collision), not just the action. |
| **Confidence gate** | Rejecting actions where the policy is uncertain (high sample variance / OOD). |
| **Predictive filter** | Roll the action forward through a model, check the horizon, project-or-reject. |
| **CBF** | Control barrier function — `h(x) ≥ 0` is safe; the filter QP keeps `ḣ ≥ -α·h`. |
| **MPC shield** | A predictive filter using an MPC-style roll-forward over a short horizon. |
| **Projection** | The nearest safe action to what the policy wanted (the optimal clamp). |
| **Rejection** | An action with no nearby safe projection; counts toward the fallback. |
| **Classical fallback** | A verified planner (MoveIt2/OMPL, sampling) that takes over after 3 rejections. |
| **Three-strike switch** | The BT fires the fallback after exactly 3 *consecutive* rejections; resets on a safe action. |
| **Intervention rate** | The fraction of *episodes* the leash touched (the deployment signal). |
| **Ablation** | Disabling the filter to prove it was catching real unsafe actions (against Defect 4). |
| **OOD action** | A confident, wrong action at a state the training data never covered (Defect 1). |
| **Reward hacking** | An RL policy exploiting a sim artifact that doesn't transfer (a learned-policy hazard). |
| **Too-loose filter** | A wrapper whose bounds never trip — decorative, not protective (Defect 4). |

---

*If a link 404s, please open an issue so we can replace it. arXiv IDs are stable; the project pages occasionally move — search the title.*
