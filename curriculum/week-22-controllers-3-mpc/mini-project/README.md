# Mini-Project — `MpcPathController`: A Constrained, Profiled, Deployable MPC

> Complete the `crunchbot_control` controller suite with a Model Predictive Controller: a constrained kinematic-bicycle MPC that tracks a path while respecting hard velocity, acceleration, and steering-rate limits (and optional obstacle constraints), with warm-starting, a built-in solve-time profiler, an infeasibility-recovery fallback, and a three-way PID/LQR/MPC benchmark — shipped against the same `ros2_control` framework as the other two controllers.

This is the artifact that turns "I solved an MPC QP in a notebook" into "I have a constraint-respecting controller that I've *profiled against a real latency budget*, that recovers when the QP is infeasible, and that I can benchmark against the PID and LQR with one command." After this week your `crunchbot_control` package is a complete, defensible three-controller suite — the centerpiece of the Phase 3 milestone in Week 24, where you defend not just each controller but the *choice* between them.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This MPC completes the controller suite. The Phase 3 milestone in Week 24 grades whether your controllers are framework-citizens *and* whether you can defend the controller choice with data. The capstone (Phase 6) names MPC as a bonus for the base controller; this is that bonus, built and profiled five months early.

---

## What you will build

Three deliverables, added to the existing `crunchbot_control` package:

1. **`crunchbot_control/mpc.py`** — the pure-Python MPC design module (source of truth for the control law): builds the kinematic-bicycle prediction model, assembles the QP with hard constraints, warm-starts the solver, checks status, and supports a soft-constraint/slack option and obstacle half-planes. No ROS dependency — unit-testable and reusable in the profiler and benchmark.
2. **The `MpcPathController` `ros2_control` plugin** — wraps the MPC, reads state, reads the upcoming reference (N points along the path), solves (warm-started), checks status, *falls back to a safe command on infeasibility/timeout*, and writes the command (or a reference for an inner controller). Loads under the `controller_manager` beside the PID and LQR.
3. **`crunchbot_control/profiler.py` + the extended benchmark** — a solve-time profiler that reports mean/p95/max against a configurable budget, and the three-way PID/LQR/MPC benchmark on the figure-8 (with an obstacle for the MPC, which the others can't handle).

By the end you have ~450–600 additional lines turning the package into a complete three-controller suite with a profiler and a benchmark.

---

## Why the MPC completes the suite

This is the third time you've added a controller to `crunchbot_control`, and by now the pattern is the payoff: **same plugin shape, different control law.** The MPC's `update` reads state, computes a command, writes it — same as the PID and LQR — with two MPC-specific additions: it *solves a QP* (with all the latency care from Lecture 2) and it *checks status and falls back* on failure. Because all three are controllers under one manager, the three-way benchmark is three runtime swaps, not three rewrites. That's the whole reason we built the `ros2_control` plumbing in Week 20 and reused it in Week 21: controller comparison is an experiment, and the Phase 3 reviewer wants to see you run it.

---

## Package layout (additions to `crunchbot_control`)

```
crunchbot_control/
├── crunchbot_control/
│   ├── pid.py                  # (Week 20)
│   ├── lqr.py                  # (Week 21)
│   ├── mpc.py                  # NEW: MPC design — QP build, constraints, warm-start
│   ├── profiler.py             # NEW: solve-time profiler (mean/p95/max vs budget)
│   └── benchmark.py            # EXTENDED: three-way PID/LQR/MPC
├── include/crunchbot_control/
│   └── mpc_path_controller.hpp # NEW
├── src/
│   └── mpc_path_controller.cpp # NEW: the ros2_control plugin (+ fallback)
├── config/
│   └── mpc_path_controller.yaml   # NEW: horizon, dt, limits, weights, budget
└── test/
    ├── test_pid.py             # (Week 20)
    ├── test_lqr.py             # (Week 21)
    └── test_mpc.py             # NEW: feasibility, constraint satisfaction, LQR-equiv
```

If you took the Python path the last two weeks, the `MpcPathController` is again a controller-style node loading its config from YAML, structured so a later C++ promotion is mechanical — but note that the *real* deployment value of MPC is the C++/`acados` fast path, so this is the controller most worth promoting eventually.

---

## Deliverable 1 — `mpc.py` (the design module, no ROS)

The heart and the thing your tests pin down. It must:

- Build the kinematic-bicycle prediction model and linearize it along a reference (Lecture 2 §1).
- Assemble the QP in `cvxpy`: dynamics as equality constraints, hard bounds on velocity/accel/steering/steering-rate as inequality constraints, the quadratic tracking-plus-effort cost with a terminal cost.
- Warm-start between solves and **return the status alongside the command** — never a bare command.
- Support a soft-constraint (slack) option and an obstacle half-plane list.
- Expose the unconstrained-equals-LQR check as a test hook.

Here is the spine; fill in the marked sections:

```python
"""crunchbot_control.mpc — kinematic-bicycle MPC for path tracking. No ROS (cvxpy)."""
from __future__ import annotations

import numpy as np
import cvxpy as cp


class BicycleMPC:
    def __init__(self, N, dt, L, v_max, a_max, delta_max, ddelta_max, Q, R, P_term):
        self.N, self.dt, self.L = N, dt, L
        self.v_max, self.a_max = v_max, a_max
        self.delta_max, self.ddelta_max = delta_max, ddelta_max
        self.Q, self.R, self.P_term = Q, R, P_term
        self._last_u = None      # for warm-start awareness

    def solve(self, state, reference, prev_delta, obstacles=None):
        """Solve the MPC QP. Returns (u0, status). NEVER returns a bare command."""
        N, dt = self.N, self.dt
        x = cp.Variable((4, N + 1))
        u = cp.Variable((2, N))
        cost = 0
        cons = [x[:, 0] == state]
        for k in range(N):
            A, B, ref = self._linearize(reference, k)
            cost += cp.quad_form(x[:, k] - ref, self.Q) + cp.quad_form(u[:, k], self.R)
            cons += [x[:, k + 1] == A @ x[:, k] + B @ u[:, k]]

            # TODO 1: add the hard constraints.
            #   speed:          cons += [cp.abs(x[3, k]) <= self.v_max]
            #   accel:          cons += [cp.abs(u[0, k]) <= self.a_max]
            #   steering angle: cons += [cp.abs(u[1, k]) <= self.delta_max]
            #   steering RATE:  prev = prev_delta if k == 0 else u[1, k-1]
            #                   cons += [cp.abs(u[1, k] - prev) <= self.ddelta_max]

            # TODO 2: if obstacles given, add a linearized half-plane per obstacle
            #   (Lecture 1 4.2): a_k^T [x,y] >= b_k, recomputed from the predicted pos.

        cost += cp.quad_form(x[:, N] - self._terminal_ref(reference), self.P_term)
        prob = cp.Problem(cp.Minimize(cost), cons)
        prob.solve(solver=cp.OSQP, warm_start=True)
        if u.value is None:
            return None, prob.status          # caller MUST handle this
        self._last_u = u.value
        return u[:, 0].value, prob.status

    # _linearize, _terminal_ref: build A/B/ref per step (Lecture 2 1.1).
```

> **Test-pinned behaviors (`test_mpc.py` checks these):**
> 1. **Unconstrained MPC equals LQR** — with no active constraints, a long horizon, and the LQR terminal cost, `u0` matches the LQR command (Exercise 1).
> 2. **Constraints are respected** — on a path demanding more than `v_max`/`ddelta_max`, the commanded trajectory never violates them.
> 3. **Infeasible returns a status, not a crash** — an over-constrained problem returns `(None, "infeasible")`, never an exception or a bare `None` command.

---

## Deliverable 2 — the `MpcPathController` plugin

A controller that wraps `BicycleMPC` and lives in the manager. It must:

- Implement the lifecycle; in `on_configure`, read the horizon, `dt`, limits, weights, and budget from `config/mpc_path_controller.yaml`.
- In `update`: read state, read the upcoming reference, solve (warm-started), **check the status**, and on non-`optimal` *fall back to a safe command* (braking law or hand-off to the LQR — your choice, documented). Write the command. Use the real `period`.
- **Publish the solve time as telemetry** (Lecture 2 §5) — the latency budget is a monitored signal.
- Be loadable and swappable beside the PID and LQR.

The conceptual `update` (the MPC-specific discipline is steps 2–3):

```cpp
controller_interface::return_type
MpcPathController::update(const rclcpp::Time &, const rclcpp::Duration & period)
{
  const auto x0 = read_state();
  const auto ref = *rt_reference_.readFromRT();

  // 2. SOLVE (warm-started), timed.
  auto t0 = clock_.now();
  auto [u0, status] = mpc_.solve(x0, ref, prev_delta_);
  double solve_ms = (clock_.now() - t0).seconds() * 1e3;

  // 3. CHECK + FALLBACK -- the MPC-specific discipline.
  if (status != SolveStatus::OPTIMAL) {
    u0 = safe_fallback(x0);              // braking law / LQR, never "nothing"
    RCLCPP_WARN(get_node()->get_logger(), "MPC %s; using fallback", status_str(status));
  }

  command_interfaces_[0].set_value(u0.a);
  command_interfaces_[1].set_value(u0.delta);
  publish_solve_time(solve_ms);          // telemetry: latency is a first-class signal
  prev_delta_ = u0.delta;
  return controller_interface::return_type::OK;
}
```

---

## Deliverable 3 — the profiler and the three-way benchmark

`profiler.py` reports mean/p95/max solve time against a budget; the extended `benchmark.py` runs all three controllers. They must:

1. Profile the MPC solve over a full figure-8 and report mean/p95/max vs. the configured budget, with a PASS/FAIL on whether p95 fits.
2. Run PID, LQR, and MPC on the same figure-8 (with an obstacle for the MPC) and report RMS cross-track error and RMS effort for each, plus "respects hard v-limit? yes/clips/no."
3. Emit the comparison table and plots for the Phase 3 defense.

```bash
python3 crunchbot_control/profiler.py --controller mpc --budget-ms 50
python3 crunchbot_control/benchmark.py --controllers pid lqr mpc --path figure8 --obstacle
```

Expected shape:

```
PROFILE mpc: N=15 dt=0.05 budget=50ms
  solve: mean 6.2 ms  p95 11.4 ms  max 18.0 ms  -> p95 23% of budget  PASS
BENCHMARK figure-8 (+obstacle for mpc):
  controller  rms_xtrack  rms_effort  respects_v_limit  avoids_obstacle
  pid         0.0__       0.__        clips             no
  lqr         0.0__       0.__        clips             no
  mpc         0.0__       0.__        yes (hard)        yes
  -> MPC is the only controller that respects the limit AND avoids the obstacle.
```

---

## Rules

- **You may** read the ROS2 docs, the `cvxpy`/OSQP/`acados` docs, Nav2 MPPI source, and the lecture notes.
- **You must not** build the MPC QP anywhere except `mpc.py`. The plugin, profiler, and benchmark import from it. If `grep -rn "cp.Problem(" --include=*.py | grep -v mpc.py` returns anything, you've broken the single-source-of-truth rule.
- **You must** check the solver status and have a fallback — a controller that sends a command from a non-`optimal` solve fails this project.
- **You must** profile the solve time (mean/p95/max) and report it against a budget — latency is a graded artifact, not an afterthought.
- **You must** use the real elapsed `period` as `dt` in the plugin's `update`.
- **You must not** depend on anything outside the ROS2 Jazzy desktop install plus `numpy`, `scipy`, `matplotlib`, `cvxpy`, and `pytest`. (`acados`/`do-mpc` are stretch-only so nobody is blocked.)
- Python 3.12 (Ubuntu 24.04 default), `rclpy`/`ros2_control` on Jazzy.

---

## Acceptance criteria

- [ ] The MPC controller lives in the **same `crunchbot_control` repo** as the Week-20 PID and Week-21 LQR.
- [ ] `colcon build --packages-select crunchbot_control` succeeds with no warnings.
- [ ] `mpc.py` builds the constrained QP, warm-starts, returns `(u0, status)`, and supports soft constraints and obstacle half-planes.
- [ ] `grep -rn "cp.Problem(" --include=*.py` finds matches **only** in `mpc.py`.
- [ ] `colcon test --packages-select crunchbot_control` passes, with `test_mpc.py` covering: unconstrained-equals-LQR; constraints respected; infeasible returns a status (no crash, no bare command).
- [ ] The plugin checks status and has a demonstrated fallback; it publishes solve-time telemetry.
- [ ] `profiler.py` reports mean/p95/max vs. a budget with a PASS/FAIL on p95.
- [ ] `benchmark.py` shows the MPC respecting the hard limit and avoiding an obstacle the PID/LQR cannot.
- [ ] A `README.md` update with the latency table, the three-way benchmark, and the controller-choice verdict.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **MPC formulation correctness** | 25 | `mpc.py` builds the QP correctly; unconstrained-equals-LQR holds; hard constraints respected; warm-started. |
| **`ros2_control` integration + fallback** | 20 | Loads beside PID/LQR; uses real `period`; checks status; has a demonstrated infeasibility fallback; publishes latency telemetry. |
| **Latency profiling** | 20 | Profiler reports mean/p95/max vs. budget; the writeup is honest about `cvxpy` overhead and the path to deployment. |
| **Constraints + obstacle** | 15 | Velocity/accel/steering-rate hard constraints bind correctly; the obstacle half-plane keeps the QP convex and routes around. |
| **Single-source-of-truth + benchmark** | 10 | The `grep` check is clean; the three-way benchmark is fair and shows MPC's unique constraint/obstacle capability. |
| **Tests + hygiene** | 10 | `test_mpc.py` covers the three behaviors; `colcon test` green; clean commits; no `build/`/`install/` checked in. |

**90+** is portfolio-grade and a real capstone-bonus controller. **70–89** works but has a soft fallback or an un-profiled solve. **Below 70** means the controller can send a command from an infeasible solve, or the latency was never measured — fix that first, because both are the difference between a demo and a deployment.

---

## Stretch goals

- **Port the hot loop to `acados`.** Reimplement the MPC with `acados` and its RTI scheme; profile against `cvxpy` and quantify the speedup. This is the jump to a genuinely deployable controller.
- **Soft + hard constraint mix.** Make the obstacle's comfort margin soft (slack) and its hard radius hard; show the robot shaves the margin under pressure but never the radius.
- **Terminal set.** Add a terminal constraint set (even an approximate one) and discuss the recursive-feasibility guarantee it buys (Lecture 2 §4.3).
- **CI job.** A GitHub Actions workflow that builds, runs `colcon test`, runs the profiler headless and asserts p95 is under a generous budget, and runs the benchmark.

---

## How this connects to the rest of C24

- **Week 23 (manipulator kinematics)** changes subject to MoveIt2 and the arm — but the arm runs under a `joint_trajectory_controller`, and the predict-optimize-under-constraints mindset returns whenever you respect joint limits and avoid self-collision.
- **Week 24 (Phase 3 integration)** folds `crunchbot_control` — all three controllers — into the integrated launch graph; the Phase 3 milestone grades whether they're framework citizens *and* whether you can defend the choice between them with data. This mini-project's benchmark and latency report are that defense.
- **The capstone (Phase 6)** names MPC as a bonus for the base controller; this profiled, constraint-respecting MPC is that bonus, built and validated months ahead.

When you've finished, push the repo and take the [quiz](../quiz.md).
