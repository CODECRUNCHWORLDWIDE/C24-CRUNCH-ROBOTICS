# Lecture 1 — Ship the Learned Policy With a Leash

> **Reading time:** ~80 minutes. **Hands-on time:** ~60 minutes (you sketch the constraint set for your robot and the action-bounds check that uses it, which Exercise 1 makes rigorous).
> **Outcome:** You can explain why a learned policy is an unverified controller, name the three families of runtime safety scaffold, clamp a trajectory without desynchronizing it, and wire a classical fallback that takes over after exactly three rejections.

For seven weeks you taught a robot to learn. This week you teach it to be *trusted*, which is a different and harder thing. A policy that picks up a mug 92% of the time on a held-out eval set is a research result. A policy you can hand to a panel, run in a shared room, and defend with a hazard log is a shippable robot. The gap between those two is one architecture: **the learned policy with a leash.** This lecture is that architecture, built from the bottom up.

If you remember one sentence from this week, remember this one:

> **A learned policy is an unverified controller. You never ship an unverified controller without a verified thing wrapped around it that can stop it when it is wrong and a verified thing it can fall back to instead.**

---

## 1. Why a learned policy is an unverified controller

Go back to Phase 3. Every controller you built came with an argument that it was safe.

- **PID (Week 20):** you could write the closed-loop transfer function, find the poles, and argue stability and bounded overshoot.
- **LQR (Week 21):** you solved the algebraic Riccati equation; the resulting feedback law is *provably* optimal for the linear-quadratic problem and stable by construction (for a controllable, observable system with the right cost).
- **MPC (Week 22):** you formulated an explicit constraint set — velocity, acceleration, obstacle bounds — and the QP solver returns an action that *satisfies those constraints by construction*, or reports infeasibility.

In every case the controller's safety is a property you can state and check before you run it. The action it emits is bounded, and you know the bound.

A Diffusion Policy, an ACT, or a VLA has **none of that**. It is a function approximator — a noise-prediction network, a transformer, a vision-language model — trained to imitate a dataset or maximize a reward in a simulator. Its output at a *training-distribution* state is excellent. Its output at an *off-distribution* state is whatever the network happens to extrapolate to, and that is:

- **Unbounded.** Nothing in a Diffusion Policy's architecture caps the action at your robot's velocity limit. If the training data never saw a state near a joint limit, the policy can confidently command a velocity that drives straight through it.
- **Confident.** The policy does not know it is off-distribution. A noise-prediction model emits a clean, low-variance action sample at a state it has never seen, the same way it does at a state it has memorized. There is no built-in "I'm not sure" signal unless you build one.
- **Unverifiable in general.** You cannot, in 2026, write down a Lyapunov function for a 100-million-parameter policy and prove it will not run away. The verification tools for that do not exist at the scale and generality of a real learned policy. (Research on neural-network verification and reachability exists; it does not yet cover a VLA on a 6-DOF arm.)

So the policy is the *fast path* — it generalizes, handles multimodal actions, takes language — but it is *unverified*. The leash is the verified control theory you *do* have (clamps, barrier functions, MPC shields, classical planners) wrapped around the policy you *can't* verify. This is not a hack. It is the standard architecture of every serious learned-manipulation deployment, and the reason is structural: you get the generalization of learning and the guarantees of classical control, by composition, when neither alone gives you both.

> **The framing for the rest of the week:** the learned policy proposes; the safety filter disposes; the classical fallback finishes. Three components, three responsibilities, one leash.

---

## 2. The four learned-policy deployment defects

Before the scaffold, know what it is defending against. There are four canonical ways a learned policy fails *in deployment* — not in training, where the loss curve looks fine, but at runtime on a robot. Each maps to a specific guard in the scaffold.

**Defect 1 — The out-of-distribution action.** The policy meets a state its training data never covered and emits a confident, plausible-looking, *wrong* action. The mug is at a pose the demos never showed; the policy reaches 15 cm to the left of it, or worse, commands the gripper *through* the table. This is the single most common deployment failure and the reason the whole leash exists. The guard: action and state bounds that reject the physically-impossible action regardless of how confident the policy is.

**Defect 2 — The multimodal collapse into the mean.** At a state where two good actions exist — go left around the obstacle, or go right — a policy that was trained to minimize mean-squared error to the demos can average them into a *third* action that goes straight into the obstacle. (This is the exact failure Diffusion Policy was designed to avoid by modeling the full action distribution; but a poorly-trained DP, or a Gaussian-MLP BC policy, still does it.) The guard: a confidence gate that samples the policy multiple times and rejects when the action distribution has collapsed or is suspiciously high-variance.

**Defect 3 — The silent-confidence failure.** The policy is wrong *and reports high confidence.* This is the dangerous one, because it defeats naive confidence gating: if you only reject low-confidence actions, a confidently-wrong action sails through. The guard: you cannot trust the policy's self-reported confidence alone; the *physical* bounds (clamps, barrier functions) must catch the wrong action by its *consequences* (it would violate a constraint), not by the policy's opinion of it.

**Defect 4 — The too-loose filter.** Your safety filter exists, but its bounds are so generous that no action ever trips them. The clamps never clamp; the fallback never fires; over forty episodes the wrapper reports zero interventions. This *feels* like success and is actually the worst defect, because the leash is **decorative** — it provides no protection and you have no evidence it works. A wrapper that never fires has never been tested by the thing it exists to catch. The guard against this defect is the *ablation* (Lecture 2): disable the filter, watch the unsafe actions execute, and confirm the filter was catching them.

Hold these four in mind. The scaffold in §3–§6 is built to catch defects 1–3, and the measurement discipline in Lecture 2 is built to catch defect 4.

---

## 3. The safety-scaffold taxonomy

A runtime safety scaffold around a learned policy has three families of guard. You will build all three; they catch different defects.

### 3.1 Action clamps

The cheapest guard: bound the *action itself*, before it touches the controller.

- **Velocity clamp.** The base twist (`geometry_msgs/Twist`) and the arm joint velocities each have a maximum. If the policy commands `linear.x = 4.0` m/s in a room rated for 1.0, the clamp catches it.
- **Acceleration / jerk clamp.** The *change* between consecutive actions is bounded. A policy that commands 0 m/s then 1.5 m/s in one control cycle requests an acceleration the robot cannot deliver and a person cannot anticipate. Bound the delta.
- **Joint-position clamp.** Every commanded joint angle is inside `[q_min, q_max]` with a margin. This is the guard against the policy reaching *through* a joint limit.

Action clamps catch Defect 1 (OOD actions) cheaply and are your first line. But they are not sufficient on their own — see §4 on why naive clamping is dangerous, and §5 on why you need a *predictive* filter on top.

### 3.2 State guards

Bound the *predicted state*, not just the action. The difference matters: an action that is individually in-bounds can still drive the robot to a bad *state*.

- **Workspace bounds.** The arm's end-effector must stay inside a defined operating volume. An action whose execution would put the tool outside it is rejected — even if the joint velocities were all in-bounds.
- **Keep-out volumes.** A dynamic exclusion zone around detected people (from your perception node) or around fragile objects. The arm's *swept volume* for the candidate action must not intersect the keep-out volume. This is the guard that keeps the elbow out of a person's space.
- **Self-collision and environment-collision.** MoveIt2's planning scene already knows the collision geometry; the state guard checks the candidate action against it before execution, the way MoveIt2 checks a planned trajectory — but at runtime, on the *learned* action MoveIt2 didn't plan.

State guards catch the OOD actions that are individually plausible but collectively unsafe — the ones the action clamps miss.

### 3.3 Confidence gates

Bound the *policy's certainty*, with the caveat from Defect 3 that you cannot trust self-reported confidence alone.

- **Sample-variance gate (for Diffusion Policy).** Sample the policy K times at the same observation. If the action samples are tightly clustered, the policy is confident; if they are spread across the action space, the policy is uncertain (or the state is multimodal). Reject — or fall back — when the spread exceeds a threshold. This catches Defect 2 (multimodal collapse) by detecting the multimodality directly.
- **Ensemble disagreement.** If you have multiple policy checkpoints, disagreement between them at a state is a strong OOD signal.
- **OOD detector.** A small model (or a density estimate over the training observations) that flags when the current observation is far from the training distribution. This is the principled version of "the policy hasn't seen this."

The confidence gate is the soft guard — it catches "the policy is unsure," which is correlated with but not identical to "the action is unsafe." The hard guards (clamps, state bounds, the predictive filter in Lecture 2) catch "the action *is* unsafe" regardless of the policy's opinion. You need both, because Defect 3 (confident-and-wrong) defeats the confidence gate alone.

---

## 4. Trajectory clamping done right: rescale time, not amplitude

Here is a trap that catches everyone the first time. You have a learned action — say a base twist, or a vector of arm joint velocities — and one component exceeds its limit. The naive fix is to saturate that component:

```python
# NAIVE and WRONG for coordinated motion:
twist.linear.x = min(twist.linear.x, V_MAX)        # clamp x
twist.angular.z = min(twist.angular.z, W_MAX)      # clamp z independently
```

For a base twist this *changes the path*: clamping `linear.x` but not `angular.z` increases the curvature, so the robot turns more sharply than the policy intended and may clip an obstacle the policy was steering around. For an arm joint-velocity vector it is worse: clamping joint 3 but not joints 1, 2, 4–6 *desynchronizes* the trajectory. The joints no longer reach their waypoints together; the end-effector path warps; a grasp that was aligned is now off by centimeters.

The correct pattern for coordinated motion is **uniform time-rescaling**: if any component exceeds its limit by a factor `f > 1`, scale the *entire* action vector by `1/f`, so the *shape* of the motion is preserved and only its *speed* is reduced.

```python
def clamp_twist_preserving_shape(vx, wz, v_max, w_max):
    """Scale the whole twist down uniformly so the path shape is preserved."""
    f = max(abs(vx) / v_max, abs(wz) / w_max, 1.0)   # worst-case over-limit factor
    return vx / f, wz / f                            # uniform scale; same curvature

def clamp_joint_velocities(qdot, qdot_max):
    """Uniformly rescale a joint-velocity vector so no joint exceeds its limit
    and all joints stay synchronized (same time-scaling, same waypoints)."""
    f = max(max(abs(q) / qd_max for q, qd_max in zip(qdot, qdot_max)), 1.0)
    return [q / f for q in qdot]
```

This is the same principle as MoveIt2's time-parameterization (`TOTG` — Time-Optimal Trajectory Generation) and Nav2's velocity smoother: when you must slow a coordinated motion down, slow *all of it* down together. Clamp the *speed of the trajectory*, never the *amplitude of one channel*. Exercise 1 makes you implement both forms and prove on a curved path that uniform rescaling preserves the path while independent saturation warps it.

> **The rule:** for any multi-DOF action, clamping is a single scalar time-scale applied to the whole vector, not a per-channel saturation. Per-channel saturation is correct only for genuinely independent channels (a single base linear velocity with no coupled turn, a single gripper width).

---

## 5. Why clamps are necessary but not sufficient

Action clamps and state guards are reactive: they look at one action (or one predicted state) and pass/clamp/reject it. They miss two things:

1. **The constraint that's about to be violated, not yet violated.** A base twist that is in-bounds *right now* can still drive the robot into a wall in 0.5 s if it's heading at one. A reactive clamp checks the velocity; it doesn't roll the velocity forward to see where it leads. You need a *predictive* filter that simulates the action's consequences over a short horizon.

2. **The minimally-invasive correction.** When an action is unsafe, you don't always want to *reject* it — sometimes you want the *nearest safe action*, the one closest to what the policy wanted that still satisfies the constraints. A clamp gives you a crude projection (saturate to the boundary); a proper filter gives you the optimal projection (the closest feasible action by some norm).

Both of these are what the **predictive safety filter** in Lecture 2 provides: roll the candidate forward through a model, evaluate the constraint set over the predicted horizon, and project-to-nearest-safe (the control-barrier-function / MPC-shield pattern). For this lecture, hold the intuition: clamps are the floor, the predictive filter is the structure on top, and together they are the *hard* guard that catches the confidently-wrong action by its consequences.

---

## 6. The classical fallback: a real controller, not an error message

The filter rejects an action. Now what? Three wrong answers and one right one.

- **Wrong: stop and wait for a human.** A robot that halts every time the policy emits a bad action is not autonomous; it is a teleoperation rig with extra steps. And in a shared space, stopping mid-task can itself be unsafe (blocking a doorway, dropping a held object).
- **Wrong: re-query the policy and hope.** If the policy was off-distribution once, it is probably off-distribution again at the same state. Re-querying is a coin flip that often loops.
- **Wrong: execute the clamped action anyway.** A clamped OOD action is still an OOD action with its speed reduced. Slower-wrong is still wrong.
- **Right: fall back to a classical planner.** When the learned policy is rejected enough times, hand the task to a *verifiable* controller — MoveIt2 + OMPL for the arm, a sampling planner for the base — that completes the task the slow, deterministic, constraint-respecting way. The classical planner is slower and less general than the learned policy, but it is *verified*: it respects the constraint set by construction.

This is the **learned policy with a leash**: the policy is the fast path, the classical planner is the safe path, the filter is the switch. The capstone spec fixes the switch threshold at **three consecutive rejections** — exactly three, not "a few." Why three?

- **One rejection is noise.** A single OOD action can be a transient — a momentary bad observation, a one-frame perception glitch. Falling back on the first rejection makes the fallback fire constantly, and you lose the policy's generalization for nothing.
- **Three consecutive rejections is a pattern.** Three in a row means the policy is *stuck* off-distribution — it keeps proposing unsafe actions at this state, so the state is genuinely outside what the policy can handle, and the classical planner should take over.
- **The count resets on a safe action.** If the policy proposes a rejected action, then a safe one, the counter resets to zero. The fallback fires only on a *run* of three, which is the signature of being genuinely stuck.

The switch lives in the **behavior tree** (Week 19), because the BT is your audit-able task structure. A `Fallback` (a.k.a. `ReactiveFallback`) node ticks the learned-policy branch first; if that branch returns `FAILURE` (because the safety filter rejected three in a row), the BT ticks the classical-planner branch instead. In Groot 2 you can *see* the leash: the tree is the documentation of "what happens when the policy is rejected."

```xml
<!-- capstone_pick_place.xml (excerpt): the leash, as a BT branch -->
<ReactiveFallback name="grasp_with_leash">
    <!-- Fast path: the learned policy, guarded by the safety filter.
         Returns FAILURE after 3 consecutive safety rejections. -->
    <SafetyGuardedPolicy name="learned_grasp"
                         policy="diffusion"
                         max_consecutive_rejections="3"/>
    <!-- Safe path: the classical planner finishes the task deterministically. -->
    <Sequence name="classical_fallback">
        <ComputeGraspMoveIt name="plan_grasp"/>
        <ExecuteTrajectory  name="execute_grasp"/>
    </Sequence>
</ReactiveFallback>
```

Read the tree: the `ReactiveFallback` is the leash. The first child is the learned policy with its filter; the second is the classical planner. The tree ticks the policy until it fails (three rejections), then ticks the planner. The whole pattern is *one BT node deep*, auditable, and visible in Groot 2 — which is exactly why the spec puts the BT "at the top."

---

## 7. The intervention rate: the number that matters

Here is the metric that separates a research demo from a deployment, and the one the midterm panel will ask for first.

Your eval set gives you a **success rate**: of N episodes, how many completed the task. That number is necessary but *not sufficient*, because it does not tell you *who did the work*. A policy with 92% success and a fallback that fired on 40% of episodes is being *carried* by its classical planner; the learned policy is barely contributing. A policy with 85% success and a 2% intervention rate is doing the work itself and only handing off when genuinely stuck. The second is the better deployment even though its success number is lower.

So you measure the **intervention rate** and its breakdown:

- **Clamp count, by constraint.** How many actions were clamped, split by which bound tripped (velocity, acceleration, workspace). A high velocity-clamp count means the policy is systematically commanding over-speed actions — a *training* problem the wrapper is papering over.
- **Rejection count.** How many actions the filter rejected outright (could not be safely projected). Rejections, unlike clamps, are the actions that count toward the three-strike fallback.
- **Fallback-trigger distribution.** On what fraction of *episodes* did the fallback fire, and on which subtasks (the grasp? the place? the approach?). Concentration tells you where the policy is weak.
- **Per-action filter latency.** The filter must be *cheaper* than the policy it wraps — if the policy infers in 31 ms and the filter takes 40 ms, you have doubled your control latency and the robot is sluggish. Report `p50` and `p95` filter latency next to the policy inference time.

This is the data the "measured intervention rate" promise in the README shows, and it is the data you defend at the midterm. "It felt safe" is not an answer; "the filter rejected 22 actions across 6 episodes, the fallback fired on 3, all 3 completed, and the filter's p95 latency is 4.8 ms against a 31 ms policy" is. Exercise 3 builds the meter; the mini-project reports the numbers; Lecture 2 §2 develops why each one matters.

---

## 8. Composing the Phase 4 stack

The leash is not a node; it is an *architecture* across several nodes, brought up in a safety-first order (the same principle you'll apply at Week 40's full integration). For the Phase 4 slice:

1. **Perception + grasp.** The perception node detects the object; the grasp pipeline (Contact-GraspNet or heuristic) and/or the VLA proposes a grasp pose. This is the policy's *input*.
2. **The learned policy.** Diffusion Policy / ACT / VLA emits the candidate action (a grasp pose, an action chunk, or a twist).
3. **The safety filter.** Sits *between* the policy and the controller. Every action passes through it; it clamps, projects, or rejects. **It must be active before any controller can execute a learned action** — the filter is the leash, and the leash goes on first among the things that can move the robot.
4. **The controller / fallback.** The accepted action goes to the arm controller (MoveIt2-managed) or base controller (PID). On three rejections, the BT switches to the classical planner.
5. **The behavior tree.** At the top, dispatching the policy branch and the fallback branch, and wiring the safety branches (E-stop, soft-stop).

The ordering is a *safety property*, not a convenience: a bring-up that activates the policy-to-controller path before the safety filter is active is a bring-up where, for a moment, an unverified action can reach the motors unguarded. The lifecycle manager encodes the order — filter active, *then* the controller can command — and the pre-flight discipline (Week 40) verifies it. For this week, the rule is simpler: **the filter node is in the action path between policy and controller, always, and it is up before the policy is allowed to emit an action that moves the robot.**

---

## 9. Worked example: the action path, end to end

Let's trace one action through the stack so the composition is concrete. The robot has been told "pick up the red mug." Perception has localized the mug; the Diffusion Policy is about to propose a grasp action.

1. **Policy proposes.** The DP emits an action chunk — eight steps of end-effector delta-poses — to approach and grasp. The first step is a delta of `(+0.05, -0.02, -0.30)` m. (The `-0.30` in z is suspicious: that's 30 cm down in one step.)

2. **Action clamp.** The per-step Cartesian velocity limit is 0.10 m/step. The proposed step's magnitude is `sqrt(0.05² + 0.02² + 0.30²) ≈ 0.306` m — over the limit by `f ≈ 3.06`. Uniform rescale: the whole delta scales by `1/3.06`, giving `(+0.016, -0.007, -0.098)` — same *direction*, capped *speed*. The clamp counter `velocity` increments.

3. **State guard.** Roll the (clamped) action forward: the end-effector would move to a pose 9.8 cm below its current height. Is that inside the workspace volume? Check against `z_min`. Suppose `z_min` is the table surface and the clamped step stays 3 cm above it — *pass*. (If it had gone below the table, the state guard would *reject*, because no speed-scaling makes "through the table" safe.)

4. **Predictive filter (Lecture 2).** Roll the action through the model over the chunk horizon; check the swept volume against the keep-out around the (empty) operator zone — pass. The action is accepted, possibly projected to the nearest feasible action if it grazed a constraint.

5. **Controller executes.** The accepted, clamped action goes to MoveIt2's controller. The arm moves.

6. **Meter updates.** `clamps.velocity += 1`, `rejections += 0`, `actions += 1`. The intervention meter now reads "1 velocity clamp of 1 action."

Now suppose steps 2–4 had *rejected* three actions in a row (the policy stuck, proposing through-the-table grasps repeatedly). The `SafetyGuardedPolicy` BT node returns `FAILURE` on the third; the `ReactiveFallback` ticks the classical branch; MoveIt2 + OMPL plans a verified grasp trajectory that respects the table constraint by construction; the arm completes the grasp the slow, safe way; `fallback_fired += 1`. The task succeeds — not by the learned policy, but by the leash doing its job. That episode counts as a success *and* as an intervention, and the honest report says both.

That trace is the whole architecture in one action. The policy proposes, the scaffold disposes, the fallback finishes, the meter counts. Build it once and every learned policy you ever deploy gets the same treatment.

---

## 10. Recap

You should now be able to:

- Explain why a learned policy is an **unverified controller** — unbounded, confident, unverifiable — and why that demands a leash.
- Name the **four deployment defects** — OOD action, multimodal collapse, silent-confidence failure, too-loose filter — and which guard catches each.
- Name the **three scaffold families** — action clamps, state guards, confidence gates — and what each catches.
- **Clamp a trajectory correctly** by uniform time-rescaling, never per-channel saturation, and explain why saturation warps a coordinated motion.
- Wire a **classical fallback** as a BT `ReactiveFallback` branch that takes over after **exactly three consecutive rejections**, with the counter resetting on a safe action.
- Define the **intervention rate** and its breakdown (clamps by constraint, rejections, fallback distribution, filter latency) and explain why it beats the success rate as a deployment signal.

Lecture 2 builds the *predictive* safety filter — the control-barrier-function / MPC-shield that rolls an action forward and projects-or-rejects — develops the intervention-rate measurement in full, expands the hazard log for learned controllers, and prepares you to defend the whole stack at the second-midterm review. The clamp is the floor; the predictive filter is the structure; the defense is where you prove it all holds. Continue to [Lecture 2 — Predictive Safety Filters and the Midterm Defense](./02-predictive-safety-filters-and-the-midterm-defense.md).

---

## References

- *Safe Learning in Robotics (Brunke et al., Annual Review of Control 2022)* — the survey of safety filters, CBFs, and safe RL: <https://arxiv.org/abs/2108.06266>
- *Control Barrier Functions: Theory and Applications (Ames et al.)* — the canonical CBF tutorial: <https://arxiv.org/abs/1903.11199>
- *Diffusion Policy (Chi et al., 2023)* — the policy you are wrapping; §on action-chunk execution: <https://diffusion-policy.cs.columbia.edu/>
- *Action Chunking with Transformers (Zhao et al., ALOHA)* — the temporal-ensembling deployment pattern: <https://tonyzhaozh.github.io/aloha/>
- *MoveIt2 Time-Optimal Trajectory Generation (TOTG)* — the trajectory-level time-rescaling your clamp imitates: <https://moveit.picknik.ai/main/index.html>
- *BehaviorTree.CPP — ReactiveFallback and control nodes*: <https://www.behaviortree.dev/docs/nodes-library/control-nodes/>
- C24 capstone specification — `SYLLABUS.md`, the safety property (200 ms E-stop, clamps, three-rejection fallback).
