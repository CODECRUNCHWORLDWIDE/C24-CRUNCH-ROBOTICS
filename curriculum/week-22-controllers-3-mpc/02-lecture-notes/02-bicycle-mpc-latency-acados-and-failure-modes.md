# Lecture 2 — The Kinematic-Bicycle MPC, Latency, `acados`, and Failure Modes

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can build a kinematic-bicycle MPC for path tracking, compare it to LQR, profile and budget its solve-time latency, understand the move from `cvxpy` to `acados`/OSQP for deployment, and diagnose the failure modes — infeasibility, timeout, and recursive feasibility — that bite real MPCs.

Lecture 1 built MPC as a QP and added constraints. This lecture makes it a *real path-tracking controller* on a *real vehicle model*, then confronts the thing that actually decides whether an MPC ships: **can you solve it fast enough?** The math is the easy half. The latency is the job.

---

## Part 1 — The kinematic-bicycle model

### 1.1 Why the bicycle model

The diff-drive unicycle from Week 6 is fine for a differential base, but the standard MPC plant — the one in every autonomous-driving course, the F1TENTH stack, and the `acados` examples — is the **kinematic bicycle**. It models a car-like (Ackermann) vehicle with a steering angle, and it's also a good model for a diff-drive base re-parameterized in terms of speed and curvature. It's the right model to learn because it generalizes: master the bicycle MPC and you can track a path on almost any wheeled robot.

The continuous kinematic-bicycle model, with state `[x, y, θ, v]` (position, heading, speed) and input `[a, δ]` (acceleration, steering angle):

```
ẋ = v·cos θ
ẏ = v·sin θ
θ̇ = (v / L)·tan δ          L = wheelbase
v̇ = a
```

The `tan δ` term and the `v·cos θ`/`v·sin θ` terms make it nonlinear, just like the diff-drive. For a QP-MPC we linearize around the reference trajectory each step (the same linearize-then-LQR move from Week 21, now done per-step along the path), giving a time-varying linear model `x_{k+1} = A_k x_k + B_k u_k` over the horizon. (Nonlinear MPC — `acados`, `do-mpc` — skips the linearization and solves the nonlinear program directly with SQP; we get to that in Part 3.)

### 1.2 Path tracking with preview

The reference is a trajectory: a sequence of desired `[x_ref,k, y_ref,k, θ_ref,k, v_ref,k]` over the horizon — the path *ahead* of the robot. This is where MPC's preview shows up concretely: because the cost sums over the whole horizon against the *upcoming* reference, the MPC starts turning *before* it reaches a curve, the way a good driver looks ahead and eases into a bend rather than yanking the wheel at the apex. LQR has no preview — it reacts to the present error only. That look-ahead is the second thing MPC buys (after constraints), and it's why MPC tracks aggressive trajectories (a figure-8, a slalom) noticeably better than LQR even when no constraint is active. You feed the MPC the next `N` reference points; it plans a smooth approach.

### 1.3 The bicycle-MPC QP

Per control step: sample the next `N` reference points along the path, linearize the bicycle dynamics around them to get `A_k`/`B_k`, and assemble the QP exactly as Lecture 1 §2.5 — dynamics as equality constraints, hard bounds on `|v|`, `|δ|`, `|a|`, and the steering-*rate* `|δ_{k+1} − δ_k|`, and the quadratic tracking-plus-effort cost. Solve, apply `[a₀, δ₀]`, advance, re-solve. The steering-rate constraint is the one that makes the bicycle MPC feel like a real vehicle controller — it forbids the instantaneous wheel-snapping that an unconstrained controller would happily command and that no real steering rack can physically do.

---

### 1.4 The bicycle-MPC, sketched in code

To anchor the abstraction, here's the skeleton of one control step — the structure Exercise 3 fleshes out:

```python
def bicycle_mpc_step(state, reference, prev_delta):
    """One control step of the kinematic-bicycle MPC. Returns (a0, delta0, status)."""
    x = cp.Variable((4, N + 1))      # [x, y, theta, v] over the horizon
    u = cp.Variable((2, N))          # [a, delta] over the horizon
    cost, cons = 0, [x[:, 0] == state]
    for k in range(N):
        Ak, Bk, ref_k = linearize_bicycle(reference, k)   # linearize along the path
        cost += cp.quad_form(x[:, k] - ref_k, Q) + cp.quad_form(u[:, k], R)
        cons += [x[:, k + 1] == Ak @ x[:, k] + Bk @ u[:, k]]   # dynamics
        cons += [cp.abs(x[3, k]) <= V_MAX]                     # speed limit
        cons += [cp.abs(u[1, k]) <= DELTA_MAX]                 # steering limit
        prev = prev_delta if k == 0 else u[1, k - 1]
        cons += [cp.abs(u[1, k] - prev) <= DDELTA_MAX]         # steering-RATE limit
    cost += cp.quad_form(x[:, N] - terminal_ref(reference), P_TERM)
    prob = cp.Problem(cp.Minimize(cost), cons)
    prob.solve(solver=cp.OSQP, warm_start=True)
    if u.value is None:
        return None, None, prob.status
    return u[0, 0].value, u[1, 0].value, prob.status
```

Every line maps to a concept: the per-step linearization along the reference (§1.1), the dynamics as equality constraints, the three hard limits including the all-important steering-*rate* limit (§1.3), the terminal cost from the LQR `P`, and — critically — the `if u.value is None` check that turns a failed solve into a status you handle rather than a `None` you send to the wheels. This is the shape of every QP-MPC you'll write; the rest is filling in the model and the weights.

## Part 2 — MPC vs. LQR, honestly

You now have three controllers. When does the MPC's extra cost actually pay?

| | PID | LQR | MPC |
|---|---|---|---|
| Multivariable coupling | hand-tuned, painful | handled (optimal gain) | handled (optimal over horizon) |
| Hard constraints | none | none | **exact** |
| Preview / look-ahead | none | none | **yes (horizon)** |
| Compute | trivial | trivial (precomputed gain) | **online QP solve every step** |
| Tuning surface | 3 gains | `Q`/`R` | `Q`/`R`/`N`/`dt`/terminal/tolerance |
| Where it shines | single loops | coupled, unconstrained | constrained, preview-heavy, near limits |

The honest engineering call: **use the simplest controller that meets the spec.** A PID for the base velocity loop. An LQR when states couple and there are no hard constraints to respect. An MPC when you genuinely need constraint satisfaction (operating near limits, near obstacles, near people) or strong preview (aggressive trajectory tracking). Reaching for MPC when an LQR would do is over-engineering — you've taken on an online solver, a latency budget, and a feasibility-failure mode you didn't need. The flip side: when you *do* need a hard constraint respected exactly, no amount of PID or LQR tuning gets you there, and MPC is the right tool despite its cost. On the figure-8 with hard velocity and steering-rate limits (this week's lab), MPC wins clearly — it respects the limits *and* previews the curve — and that's exactly the situation that justifies it.

---

## Part 3 — Latency: the part that decides deployment

### 3.1 Why `cvxpy` is for learning, not shipping

`cvxpy` is a *modeling* layer. Every time you call `prob.solve()`, it canonicalizes your problem (translates your readable Python into the matrix form OSQP wants), which has real overhead — often milliseconds, sometimes more than the solve itself. For *learning* MPC that's irrelevant; for a 50 Hz control loop (20 ms budget) on an Orin Nano shared with a perception stack, that overhead can blow your budget by itself. This is not a knock on `cvxpy` — it's the right tool for stating the problem and verifying your formulation. It's the wrong tool for the real-time inner loop, and knowing *why* is the difference between an MPC that demos and one that deploys.

### 3.2 Profiling the solve

The first thing you do with any MPC is measure it. Wrap the solve and record the distribution — not just the mean, the **tail**:

```python
import time
import numpy as np

solve_times = []
for t in range(num_steps):
    t0 = time.perf_counter()
    u0, status = solve_mpc(x)
    solve_times.append(time.perf_counter() - t0)
    # ... apply u0, step plant ...

st = np.array(solve_times) * 1e3   # ms
print(f"solve time: mean {st.mean():.1f} ms  p95 {np.percentile(st, 95):.1f} ms  "
      f"max {st.max():.1f} ms")
budget_ms = 20.0
print(f"budget {budget_ms} ms -> p95 is {np.percentile(st, 95)/budget_ms*100:.0f}% of budget")
```

**Why the p95 and max, not the mean?** Because a control loop has a *hard deadline* every period. If the mean solve is 8 ms but the p95 is 25 ms on a 20 ms budget, then one step in twenty misses its deadline — and a missed deadline in a control loop means a stale or dropped command, which on a fast robot is a jerk or worse. You budget for the *tail*, not the average. A controller whose p95 fits the budget is deployable; one whose mean fits but whose tail doesn't is a controller that occasionally fails, which is the worst kind.

### 3.3 What drives the solve time

Three things, and knowing them tells you what to cut when you're over budget:

- **Horizon length `N`.** The QP size grows roughly linearly in `N` (more variables and constraints), and the solve time grows faster than linearly. Halving `N` is the biggest single lever — at the cost of less preview. There's a real trade: enough horizon to see the curve, short enough to solve in time.
- **State/input dimension.** A 4-state bicycle is cheap; a 12-state quadrotor is not. You can't change your robot's dimension, but you can sometimes control a reduced model.
- **Constraint count.** Each obstacle half-plane, each state bound, adds rows. Obstacle-dense environments make the QP bigger every step.

### 3.4 Warm-starting: the free speedup

Successive MPC solves are *almost identical* — the problem at step `t+1` is the step-`t` problem shifted one step forward. So last step's solution, shifted, is an excellent starting guess for this step's solver. **Warm-starting** seeds the solver with it, and OSQP (operator-splitting) converges in a fraction of the iterations from a warm start versus cold. In `cvxpy` it's one flag (`warm_start=True`); in OSQP-direct or `acados` it's built into the architecture. Warm-starting routinely cuts solve time several-fold and is the first optimization you reach for — it costs you nothing and exploits the structure of the receding horizon. The reason MPC is real-time-feasible at all on modest hardware is largely warm-starting: you're never solving from scratch, only correcting.

### 3.4.1 A worked latency budget, end to end

Let's make the budget concrete, because "profile it" is too vague to act on. Suppose you target **50 Hz** base control → a **20 ms** period. The control period is not all yours; it's a budget you split:

| Item | Budget | Notes |
|---|---|---|
| Read state + reference (ROS, TF lookups) | ~2 ms | I/O, not free |
| **MPC solve** | **≤ 12 ms** | the number you profile and fight for |
| Write command + telemetry | ~1 ms | publishing |
| Slack / jitter margin | ~5 ms | never budget to 100% |
| **Total** | **20 ms** | the hard deadline |

So your *real* solve budget is ~12 ms, not 20 — and you budget the **p95**, not the mean, into that 12 ms. If your `cvxpy` MPC profiles at mean 9 ms / p95 22 ms, you are *over budget* despite a comfortable-looking mean: one solve in twenty blows the 12 ms allotment and cascades into the jitter margin or past the deadline. The fixes, in the order you reach for them: (1) warm-start (free, do it always), (2) shorten `N` until p95 fits (costs preview), (3) loosen the solver tolerance (costs accuracy, watch for `optimal_inaccurate`), (4) drop `cvxpy` for OSQP-direct (removes canonicalization overhead), (5) move to `acados` with RTI (bounds the time by construction). You go down that list until p95 fits, and you *document what each step cost* — that documentation is the deliverable in the homework and the challenge, because "I made it fit" without "and here's what I gave up" is half an answer.

The reason this is a first-class engineering artifact and not a footnote: on the Orin Nano the syllabus targets, the GPU is shared with a perception stack eating most of the compute, and the CPU cores the QP solver runs on are contended. A solve that's 4 ms on your idle laptop can be 15 ms on a loaded Orin. So the honest version of "profile it" is "profile it on the *target hardware under realistic load*," and the honest verdict accounts for the fact that your dev-laptop numbers are optimistic. This is exactly the kind of latency realism that separates a controls demo from a shipped controller, and it's why Week 39 (edge ML optimization) and this week share a worldview: on embedded robotics hardware, every millisecond is a design constraint you must measure, not assume.

### 3.5 The move to OSQP-direct and `acados`

When `cvxpy`'s overhead is the bottleneck, you drop to the solver directly or move to a real-time framework:

- **OSQP directly.** Formulate the QP matrices once, update only the parts that change each step (the current state, the reference), and call OSQP's solve. You skip `cvxpy`'s per-step canonicalization entirely. This alone often gets a `cvxpy`-too-slow MPC into budget.
- **`acados`.** The codegen real-time MPC framework that deployed robots ship. You specify the model and cost in Python; `acados` *generates C code* for the specific problem and compiles it, eliminating all interpretation overhead. Crucially, it uses the **real-time iteration (RTI) scheme**: instead of solving the (nonlinear) MPC to convergence each step, it does *one* SQP iteration per control step, exploiting the fact that the warm-started problem is already nearly solved. RTI turns nonlinear MPC into something that runs at hundreds of Hz on embedded hardware. This is how warehouse AMRs and racing drones run MPC in the real world.
- **`do-mpc`.** A higher-level Python framework (the syllabus names it) that wraps the modeling and supports nonlinear MPC; a good middle ground between `cvxpy` clarity and `acados` speed.

The deployment arc is always the same: **prototype in `cvxpy` to get the formulation right, profile it, then port the hot loop to OSQP-direct or `acados` to hit the budget.** Skipping the prototype and starting in `acados` is how you spend a week debugging a code-generation error that was really a formulation bug you'd have caught in `cvxpy` in ten minutes. Skipping the port and shipping `cvxpy` is how your robot misses its deadline in the demo. Do both, in order.

---

## Part 3.6 — A profiling checklist you can run today

Before you trust any MPC's latency, run this checklist. It's the difference between "it felt fast" and "I know its p95 under load."

1. **Measure the right thing.** Time only the solve (`solve_mpc`), not the plotting or the I/O around it. Use `time.perf_counter()`, which is monotonic and high-resolution; never `time.time()`, which can jump.
2. **Measure enough samples.** Profile over a *full* representative run (the whole figure-8, hundreds of steps), not ten solves. The tail only shows up over many samples — a p95 from 20 samples is noise.
3. **Report the distribution.** Mean, p95, max — and ideally a histogram. A bimodal distribution (most solves fast, a few slow) is a warning sign: something occasionally makes the QP harder (an obstacle entering the horizon, a near-infeasible state), and those are exactly the high-stakes moments.
4. **Profile warm-started.** Cold-start times are irrelevant for steady-state operation; warm-started times are what you actually pay. Profile with `warm_start=True` and after the loop has been running a few steps.
5. **Profile on the target, under load.** Your laptop is optimistic. If you can, profile on the Orin (or a representative machine) with the perception stack running, because contended cores and a busy GPU change the numbers materially.
6. **Compare to the budget, with margin.** Don't compare to the full control period; compare to the solve's *slice* of it (Part 3.4.1), and leave jitter margin. p95 at 90% of the slice is not "passing" — it's one bad day from missing.

This checklist is mechanical, takes ten minutes, and is the single most valuable habit you build this week, because an unprofiled MPC is a controller you are *hoping* meets its deadline. Hope is not a real-time guarantee.

## Part 4 — Failure modes

An MPC has failure modes a gain-based controller doesn't, because it's an online optimizer. Know them before they bite you on hardware. The unifying theme: **an MPC is a controller only when paired with a plan for what to do when the optimization fails.** The QP alone is a research artifact; the QP plus detection plus recovery is a controller.

### 4.0 A fallback that always returns a command

Because every recovery path below ends in "fall back to a safe controller," here is what that controller looks like. The rule: it must *never* fail to produce a command, which means it can have no optimization, no constraints that can conflict, nothing that returns `None`.

```python
def safe_fallback(state, v_max, a_max):
    """A braking law that always returns a valid, safe command. No solver, no
    constraints to conflict, no None. Decelerate within the actuator limits and
    hold the wheels straight."""
    x, y, theta, v = state
    a = -np.clip(v / 0.5, -a_max, a_max)   # decelerate toward zero speed
    delta = 0.0                            # straighten the steering
    return a, delta
```

That's it — a few lines, guaranteed to return. The MPC controller is *always* the QP plus this fallback, never the QP alone. When the QP returns `optimal`, you use its command; on anything else, you use the fallback. The fallback doesn't have to be good — it has to be *safe and always available*. A braking law that stops the robot in a straight line is a perfectly good fallback for almost any mobile robot, because "stop safely" is almost always an acceptable degraded behavior. The capstone's "classical fallback when the learned policy fails three times" is this exact pattern at the policy level; here it's at the controller level. Internalize it: **a controller you can't fall back from is a controller that can stop controlling, and on a moving robot that's a hazard, not an edge case.**

### 4.1 Infeasibility

The QP has *no* solution satisfying all constraints — the solver returns `infeasible` and `u₀` is `None`. Causes: a disturbance pushed the state into a corner from which no admissible input keeps every constraint; the constraints are over-tight; the horizon is too short to find a way out. **Detection** is checking `prob.status` every step (Lecture 1 §3.1). **Recovery**, in order of preference:

1. **Soft constraints** (Lecture 1 §4.3) — slack the non-safety-critical constraints so a feasible-with-penalty solution always exists. This is the primary defense; design it in from the start.
2. **A fallback controller** — if even the softened MPC is infeasible (or times out), hand control to a simple, always-available safe controller (a braking law, the LQR, a stop). The capstone's "classical fallback when the learned policy is rejected" pattern is exactly this idea applied to controllers: *always have a controller that cannot fail to produce a command.*
3. **Re-solve with a shrunk horizon** or relaxed bounds — a last-ditch attempt before falling back.

An MPC with no infeasibility recovery is a robot that, the first time the QP is infeasible, sends `None` to the motors and stops controlling. That is not acceptable on anything that moves near people. The recovery path is part of the controller, not an optional extra.

### 4.2 Solver timeout / missed deadline

The solve doesn't finish within the control period. With a hard deadline (a real-time control loop), you cannot wait — you must do *something* at the deadline. Options: use the warm-start guess (last step's plan, shifted — it's a decent input even un-refined), use the RTI scheme (which does exactly one iteration and *always* returns on time by construction), or fall back. The `acados` RTI scheme is popular precisely because it makes the deadline a *guarantee*: one iteration, bounded time, always returns. With `cvxpy` you set a solver iteration cap and accept `optimal_inaccurate`, or you've sized `N` wrong for your hardware.

### 4.3 Recursive feasibility and the terminal set

The subtle, important one. **Recursive feasibility** is the guarantee that *if the MPC is feasible now, it remains feasible at every future step* — that the robot can't optimize itself into a state from which, next step, no feasible plan exists. A naive finite-horizon MPC does *not* have this guarantee: it can cheerfully drive toward a corner that looks fine within the current `N`-step horizon but becomes a trap one step later (the "MPC painted itself into a corner" failure). The rigorous fix is a **terminal constraint set**: require the final predicted state `x_N` to lie in a known *control-invariant* set — a region from which you're guaranteed to be able to stay safe forever. Combined with the LQR terminal cost (Lecture 1 §2.4), the terminal set gives provable stability and recursive feasibility. In practice, for many mobile-robot MPCs, people use a long horizon and good soft constraints instead of a formal terminal set (computing invariant sets is hard), and accept that they're trading rigor for practicality — but you must *know* the guarantee you're giving up, because "my MPC drove into a dead end it can't escape" is a real incident, not a hypothetical.

### 4.4 Model mismatch

The same caveat as LQR (Week 21 §8), amplified: the prediction is only as good as the model. If the real robot's dynamics differ from `A_k`/`B_k`, the MPC's plan is optimal for a robot that doesn't exist, and the re-solve-every-step feedback is what saves you — it corrects the model error continuously, which is *another* reason the receding horizon (apply one, re-plan) matters. MPC tolerates more model error than open-loop trajectory optimization precisely because it re-plans from measured state, but a badly wrong model still degrades it. Nonlinear MPC (`acados`) reduces this by not linearizing at all.

### 4.5 The failure-mode decision tree

When something goes wrong with a running MPC, walk this:

```
MPC misbehaving or not commanding well.
│
├─ prob.status != "optimal"?
│   ├─ "infeasible"   → soften non-safety constraints; if still infeasible,
│   │                    FALL BACK to a safe controller. Never command from None.
│   ├─ timeout / slow → warm-start; shrink N; use RTI/one-iteration; or fall back.
│   └─ "inaccurate"   → tighten solver tolerance if budget allows; else accept & watch.
│
├─ status "optimal" but tracking is poor?
│   ├─ myopic (turns into curves/obstacles too late) → horizon N too short; lengthen it.
│   ├─ chattery command                              → R too low / no rate constraint.
│   └─ steady offset                                 → model bias; add integral state or
│                                                       a disturbance estimate.
│
├─ status "optimal", tracking ok, but it drove into a trap?
│   └─ recursive feasibility lost → add a terminal set / longer horizon / better
│                                    soft constraints. (§4.3)
│
└─ everything ok in sim, bad on hardware?
    └─ model mismatch (§4.4) or LATENCY (Part 3): re-profile on the target under load.
```

Tape this next to the Week 20 and Week 21 controller-design flows. Between the three weeks you now have: a flow for *choosing* a controller (PID/LQR/MPC), and a flow for *debugging* each when it misbehaves. That pair — pick the right tool, diagnose it when it breaks — is the working controls engineer's entire toolkit for a mobile robot.

---

## Part 5 — Shipping MPC in `ros2_control`

The MPC integrates the same way as the PID and LQR — as a controller under the manager — with one common architectural twist: MPC often runs as an **outer loop** that generates a reference (a velocity/curvature command, or a short trajectory) for a faster **inner loop** (a `joint_trajectory_controller` or the diff-drive controller) to track. This split lets the MPC run at a slower rate (say 20 Hz, where the QP fits the budget) while the inner loop runs fast (200 Hz) and smooth. The same `ros2_control` plumbing applies; the `update` solves the QP (with all the latency care above) and writes either a command interface directly or a reference for a chained controller.

```cpp
controller_interface::return_type
MpcPathController::update(const rclcpp::Time &, const rclcpp::Duration & period)
{
  // 1. READ current state and the upcoming reference (N points along the path).
  const auto x0 = read_state();
  const auto ref = *rt_reference_.readFromRT();

  // 2. SOLVE the QP (warm-started). CHECK status. Profile the time.
  auto [u0, status, solve_ms] = mpc_.solve(x0, ref);

  // 3. RECOVER if not optimal: soft-constraint result, or fall back to LQR/stop.
  if (status != SolveStatus::OPTIMAL) { u0 = fallback_command(x0); }

  // 4. WRITE the first input (or the reference for an inner controller).
  command_interfaces_[0].set_value(u0.a);
  command_interfaces_[1].set_value(u0.delta);
  publish_solve_time(solve_ms);   // telemetry: the latency budget is a first-class signal
  return controller_interface::return_type::OK;
}
```

Note steps 2–3: **check the status, have a fallback.** That's the MPC-specific discipline on top of last week's plugin shape. And note that the solve time is *published as telemetry* — on a real deployment the control-loop latency is a monitored signal, because the day it starts creeping toward the budget is the day before it starts missing deadlines.

---

## Part 5.5 — The inner/outer loop split, in depth

The "MPC as outer loop" idea in Part 5 deserves a closer look, because it's the architecture most deployed mobile-robot MPCs actually use and it resolves the latency tension elegantly.

The tension: you want the MPC's foresight and constraint-handling, but you also want a *fast, smooth* command rate to the actuators — and the QP solve is too slow to run at actuator speed. The resolution is a **cascade**:

```
   path / goal                 reference (v, curvature, or short trajectory)
        │                                    │
        ▼                                    ▼
  ┌───────────┐   ~20 Hz, solves QP   ┌──────────────────┐   ~200-1000 Hz
  │  MPC      │ ───────────────────►  │ inner controller │ ─────────────────► motors
  │ (outer)   │   constraints+preview │ (PID / LQR /     │   tracks the ref
  └───────────┘                       │  diff_drive)     │   smoothly & fast
                                      └──────────────────┘
```

The **outer loop** is the MPC: it runs slower (say 20 Hz, where the QP fits the budget), sees far ahead, respects the hard constraints, and emits a *reference* — a velocity and curvature, or a short trajectory snippet — rather than a raw motor command. The **inner loop** is a fast, simple controller (a PID velocity loop, an LQR, or the stock `diff_drive_controller`) running at hundreds of Hz that *tracks* the MPC's reference smoothly. The inner loop fills the gaps between the MPC's slower updates and rejects fast disturbances the MPC's slow rate would miss.

Why this is the right structure: it puts each job at the rate it needs. Constraint reasoning and preview are *planning-like* and tolerate a slower rate (the world doesn't change much in 50 ms). Smooth actuation and fast disturbance rejection are *control-like* and need a high rate. Forcing the QP to run at actuator rate is both unnecessary (the constraints don't need re-checking every millisecond) and infeasible (the solve is too slow). The cascade is how `ros2_control` is *built* to work — chainable controllers, where one controller's output is another's reference interface — and it's why MoveIt2 commands the arm through a `joint_trajectory_controller` rather than computing joint torques directly. You'll see this exact pattern again in Week 23 with the arm: a planner produces a trajectory, a trajectory controller tracks it. MPC slots into the planner-ish outer role naturally.

The practical upshot for your mini-project: if your MPC can't hit the actuator rate (it usually can't with `cvxpy`), don't fight it — run the MPC slower as an outer loop emitting a reference, and let a fast inner controller (your Week 20 PID or Week 21 LQR, already in the package!) track it. That's not a compromise; it's the correct architecture, and it reuses the controllers you already built.

## Part 5.6 — A deployment readiness checklist

Before any MPC goes on a robot that moves near people or property, it must pass this checklist. Treat a `no` on any line as a blocker, not a nuisance:

- [ ] **Status checked every step.** The code reads `prob.status` (or the solver's equivalent) on every solve and never sends a command from a non-`optimal` result.
- [ ] **Fallback exists and is tested.** There is a guaranteed-available safe controller (braking law, LQR, or stop) that takes over on infeasibility or timeout, and you have *demonstrated* it firing by forcing a failure.
- [ ] **Latency profiled on the target.** Mean/p95/max solve time measured on the deployment hardware under realistic load, with the p95 inside the solve's slice of the control period.
- [ ] **Warm-starting on.** Successive solves reuse the previous solution; you've confirmed it actually reduces solve time.
- [ ] **Hard vs. soft constraints classified.** Every constraint is deliberately hard (inviolable: actuator max, wall) or soft (preferred: comfort speed), with slack variables on the soft ones so the QP stays feasible.
- [ ] **Constraints are convex.** Obstacle avoidance is a per-step linearized half-plane, not a non-convex disk; the problem is still a QP.
- [ ] **Model validated.** The prediction model has been checked against the real robot's response, and you know roughly how much model error the closed loop tolerates.
- [ ] **Telemetry published.** Solve time and solver status stream to the operator dashboard, so latency creep and infeasibility spikes are visible before they become incidents.
- [ ] **Behavior at the limits inspected.** You've watched the MPC operate with constraints *binding* (near max speed, near an obstacle) and confirmed it degrades gracefully.

This checklist is the difference between an MPC that wins a demo and one that survives a deployment. Every item maps to a failure mode in this lecture; skipping one is choosing to discover that failure mode in production. The mini-project's grading rubric is essentially this checklist, because passing it *is* the skill the week teaches: not "can you write an MPC" (you can, in `cvxpy`, in an afternoon) but "can you write one you'd trust on a robot."

## Part 6 — Recap

You should now be able to:

- Build a kinematic-bicycle MPC for path tracking, with linearization along the reference and hard velocity/steering/steering-rate constraints.
- Explain what MPC buys over LQR (exact constraints, preview) and what it costs (online solve, tuning surface, failure modes), and choose the simplest controller that meets the spec.
- Profile the solve time and budget against the control period using the p95/max, not the mean.
- Use warm-starting, and explain the move from `cvxpy` (prototype) to OSQP-direct/`acados` (deploy), including the RTI scheme.
- Diagnose and recover from infeasibility (soft constraints, fallback), handle solver timeout (RTI, warm-start guess), and explain recursive feasibility and the terminal set.
- Ship MPC as a `ros2_control` controller, often as an outer loop with a fallback and latency telemetry.

Next: the exercises put all of this on your robot — formulate an MPC and verify it equals LQR, watch constraints bind, and track a figure-8 with a profiled bicycle MPC. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- Rawlings, Mayne & Diehl, *Model Predictive Control* — feasibility, stability, terminal sets (Ch. 2): <https://sites.engineering.ucsb.edu/~jbraw/mpc/>
- `acados` documentation — the RTI scheme and the Python interface: <https://docs.acados.org/>
- OSQP — warm-starting and the solver internals: <https://osqp.org/docs/>
- `do-mpc` — the Python MPC framework (nonlinear, higher-level): <https://www.do-mpc.com/en/latest/>
- Nav2 MPPI controller — a deployed predictive controller in the navigation stack: <https://docs.nav2.org/configuration/packages/configuring-mppic.html>
- F1TENTH MPC — a runnable kinematic-bicycle MPC on a real small car: <https://f1tenth.org/learn.html>
