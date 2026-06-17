# Mini-Project — `LqrPathController`: An Optimal Path-Tracking Controller

> Extend last week's `crunchbot_control` package with an LQR path-tracking controller: a `ros2_control` plugin that solves the algebraic Riccati equation from a model and a cost, adds integral action for zero steady-state error, gain-schedules across the speed range, and ships beside the Week-20 PID so the two can be swapped and benchmarked with one CLI command.

This is the artifact that turns "I can call `solve_continuous_are` in a notebook" into "I have an optimal controller living in the robot's real-time stack that I can A/B against the PID on the same hardware." After this week, choosing a controller is an *experiment* with numbers, not a preference — and the package is set up to host MPC next week with the same plumbing.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This controller lives in the **same `crunchbot_control` package** as last week's PID and next week's MPC. The `ros2_control` plumbing is reused verbatim; only the control law changes. The Phase 3 milestone in Week 24 explicitly checks that your controllers are framework-citizens with a defensible *choice* between them. Build the LQR well now; you'll benchmark it against PID this week and against MPC next week.

---

## What you will build

Three deliverables, all added to the existing `crunchbot_control` package:

1. **`crunchbot_control/lqr.py`** — the pure-Python LQR design module (source of truth for the control law): builds the diff-drive error `A`/`B`, designs `Q`/`R` from Bryson tolerances, solves the CARE, runs the three sanity checks, supports integral augmentation (LQI) and gain scheduling. No ROS dependency — unit-testable and reusable in the benchmark harness.
2. **The `LqrPathController` `ros2_control` plugin** — wraps the LQR gain, reads the error state (cross-track + heading) from state interfaces, applies `u = −Kx − k_i·x_i` with anti-windup on the integral state, schedules the gain on the measured speed, and writes the yaw-rate command. Loads under the `controller_manager` beside the PID.
3. **`crunchbot_control/benchmark.py`** — the head-to-head harness: runs PID and LQR (and LQI) against the same curved reference, reports RMS/max cross-track error, RMS heading error, and RMS control effort, and emits the comparison plots and table for your writeup.

By the end you have ~400–550 additional lines that turn the package into a two-controller (soon three-controller) suite with a reproducible benchmark.

---

## Why the LQR drops straight into last week's package

This is the payoff of the `ros2_control` ceremony. The LQR controller has the *same plugin shape* as the PID:

- Same lifecycle (`on_init` → `on_configure` → `on_activate` → `update` → `on_deactivate`).
- Same interface model (read state interfaces, write a command interface, use the real `period` as `dt`).
- Same parameter surface (gains/cost in YAML, law in code).
- Same loading mechanism (`ros2 control load_controller`).

The *only* thing that changes is the body of `update`: instead of three PID terms, it's `u = −Kx`. Because both are controllers under one manager, **comparing them is a runtime swap, not a rewrite** — which is exactly what makes the benchmark fair and exactly what the Phase 3 reviewer wants to see.

---

## Package layout (additions to `crunchbot_control`)

```
crunchbot_control/
├── crunchbot_control/
│   ├── pid.py                  # (from Week 20)
│   ├── lqr.py                  # NEW: LQR design — CARE solve, LQI, scheduling
│   └── benchmark.py            # NEW: PID vs LQR head-to-head harness
├── include/crunchbot_control/
│   └── lqr_path_controller.hpp # NEW
├── src/
│   └── lqr_path_controller.cpp # NEW: the ros2_control plugin
├── config/
│   ├── yaw_rate_controller.yaml   # (PID, from Week 20)
│   └── lqr_path_controller.yaml   # NEW: Bryson tolerances + scheduling grid
└── test/
    ├── test_pid.py             # (from Week 20)
    └── test_lqr.py             # NEW: controllability, P pos-def, stable, gain match
```

If you took the Python path last week, the `LqrPathController` can again be a controller-style node that loads its cost from YAML and uses the same param names — so a later promotion to a real C++ plugin is mechanical.

---

## Deliverable 1 — `lqr.py` (the design module, no ROS)

This is the heart and the thing your tests pin down. It must:

- Build the diff-drive error `A`/`B` for a given `v_ref` (Lecture 1 §2.2).
- Design `Q`/`R` from Bryson tolerances passed in as parameters (not hardcoded magic numbers).
- Solve the CARE with `scipy.linalg.solve_continuous_are` and return `K` and `P`.
- Run the three sanity checks (controllable, `P` positive-definite, closed-loop stable) and *raise* on failure — a bad gain must never silently reach the controller.
- Support integral augmentation (`lqi(...)`) and gain scheduling (`scheduled_gains(speeds, ...)`).

Here is the spine; fill in the marked sections:

```python
"""crunchbot_control.lqr — LQR design for diff-drive path tracking. No ROS."""
from __future__ import annotations

import numpy as np
from scipy.linalg import solve_continuous_are


def diff_drive_error_AB(v_ref: float):
    A = np.array([[0.0, v_ref], [0.0, 0.0]])
    B = np.array([[0.0], [1.0]])
    return A, B


def bryson_QR(e_y_max, e_theta_max, u_max):
    Q = np.diag([1.0 / e_y_max**2, 1.0 / e_theta_max**2])
    R = np.array([[1.0 / u_max**2]])
    return Q, R


def controllability_rank(A, B):
    n = A.shape[0]
    blocks = [B]
    for _ in range(1, n):
        blocks.append(A @ blocks[-1])
    return np.linalg.matrix_rank(np.hstack(blocks))


def solve_lqr(A, B, Q, R):
    """Solve LQR; raise if the design is invalid. Returns (K, P)."""
    n = A.shape[0]
    if controllability_rank(A, B) != n:
        raise ValueError("uncontrollable system — LQR cannot help")

    # TODO 1: solve the CARE and recover K = R^-1 B^T P.
    #   P = solve_continuous_are(A, B, Q, R)
    #   K = np.linalg.inv(R) @ B.T @ P

    # TODO 2: the three sanity checks — raise on any failure.
    #   - P symmetric and positive-definite
    #   - closed-loop eigenvalues of (A - B K) all have negative real part

    return K, P  # noqa: F821  (defined once you fill in TODO 1)


def scheduled_gains(speeds, e_y_max, e_theta_max, u_max):
    """Solve LQR at each speed; return (speeds, gains array) for runtime interp."""
    Q, R = bryson_QR(e_y_max, e_theta_max, u_max)
    gains = []
    for v in speeds:
        A, B = diff_drive_error_AB(v)
        K, _ = solve_lqr(A, B, Q, R)
        gains.append(K.flatten())
    return np.asarray(speeds), np.asarray(gains)
```

> **Test-pinned behaviors (`test_lqr.py` checks these):**
> 1. `solve_lqr` returns a `K` matching `control.lqr` to tolerance.
> 2. `solve_lqr` *raises* on an uncontrollable system (`v_ref = 0`).
> 3. The closed loop `A − BK` is stable for a valid design.
> 4. `lqi` drives a constant disturbance to zero steady-state in simulation; plain LQR does not.

---

## Deliverable 2 — the `LqrPathController` plugin

A controller that wraps the LQR gain and lives in the manager. It must:

- Implement the lifecycle; in `on_configure`, read the Bryson tolerances and the scheduling grid from `config/lqr_path_controller.yaml`, solve the scheduled gains, and store them.
- In `update`: read cross-track and heading error from state interfaces, read the current speed, interpolate the scheduled gain, integrate the cross-track error (with anti-windup), apply `u = −Kx − k_i·x_i`, saturate, and write the yaw-rate command. **Use the real `period.seconds()` as `dt`.**
- Be loadable and swappable: `ros2 control set_controller_state crunchbot_pid inactive && ros2 control set_controller_state crunchbot_lqr active` switches from PID to LQR on the running robot.

The conceptual `update` (same five-step shape as the PID, different law):

```cpp
controller_interface::return_type
LqrPathController::update(const rclcpp::Time &, const rclcpp::Duration & period)
{
  Eigen::Vector2d x;
  x << state_interfaces_[0].get_value(),       // cross-track error
       state_interfaces_[1].get_value();       // heading error
  const double v = *rt_speed_.readFromRT();
  const Eigen::RowVector2d K = scheduled_gain(v);   // interpolate (Lecture 2 §3)

  const double dt = period.seconds();
  x_i_ += (-x(0)) * dt;                         // integrate cross-track error
  x_i_ = std::clamp(x_i_, i_min_, i_max_);      // anti-windup

  double u = -(K * x)(0) - k_integral_ * x_i_;  // u = -Kx - k_i x_i
  u = std::clamp(u, u_min_, u_max_);
  command_interfaces_[0].set_value(u);
  return controller_interface::return_type::OK;
}
```

---

## Deliverable 3 — the benchmark harness

`benchmark.py` makes the LQR-vs-PID comparison reproducible. It must:

1. Run PID, LQR, and LQI against the *same* curved reference (use a figure-8 or sinusoid), same start offset, same speed, same saturation.
2. Compute RMS and max cross-track error, RMS heading error, and RMS control effort for each.
3. Emit the comparison table and the tracking plots for your writeup.
4. Optionally inject a constant disturbance to demonstrate LQI's zero-steady-state advantage over plain LQR.

```bash
python3 crunchbot_control/benchmark.py --controllers pid lqr lqi --path figure8
```

Expected shape of the output:

```
BENCHMARK on figure-8, v=0.5, start 0.3 m off-path, |omega|<=1.5
  controller  rms_xtrack  max_xtrack  rms_heading  rms_effort
  pid         0.0__ m      0.__ m      0.__ rad     0.__ rad/s
  lqr         0.0__ m      0.__ m      0.__ rad     0.__ rad/s   <- lower xtrack
  lqi         0.0__ m      0.__ m      0.__ rad     0.__ rad/s   <- zero ss under bias
  -> LQR cross-track RMS is 1.__x lower than PID; effort comparable.
```

---

## Rules

- **You may** read the ROS2 docs, the `ros2_control` docs, `python-control` source, and the lecture notes.
- **You must not** call `solve_continuous_are` anywhere except `lqr.py`. The plugin and benchmark import from it. If `grep -rn "solve_continuous_are" --include=*.py | grep -v lqr.py` returns anything, you've broken the single-source-of-truth rule.
- **You must** run the three sanity checks in `solve_lqr` and *raise* on failure — a gain that fails a check never reaches a robot.
- **You must** use the real elapsed `period` as `dt` in the plugin's `update`.
- **You must not** depend on anything outside the ROS2 Jazzy desktop install plus `numpy`, `scipy`, `matplotlib`, `control`, and `pytest`.
- Python 3.12 (Ubuntu 24.04 default), `rclpy`/`ros2_control` on Jazzy.

---

## Acceptance criteria

- [ ] The LQR controller lives in the **same `crunchbot_control` repo** as the Week-20 PID.
- [ ] `colcon build --packages-select crunchbot_control` succeeds with no warnings.
- [ ] `lqr.py` solves the CARE, raises on uncontrollable systems, supports LQI and scheduling.
- [ ] `grep -rn "solve_continuous_are" --include=*.py` finds matches **only** in `lqr.py`.
- [ ] `colcon test --packages-select crunchbot_control` passes, with `test_lqr.py` covering: gain matches `control.lqr`; raises on `v_ref=0`; closed loop stable; LQI rejects a disturbance.
- [ ] `ros2 control list_controllers` shows both `pid` and `lqr`; switching between them on the running robot works.
- [ ] `benchmark.py` produces the comparison table and plots; on the curved path the LQR's RMS cross-track error is lower than the PID's at comparable effort (or the writeup honestly explains why not).
- [ ] A `README.md` update with the benchmark table, the cost design, and the controller-choice verdict.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **LQR design correctness** | 25 | `lqr.py` solves the CARE, recovers `K = R⁻¹BᵀP`, runs all three sanity checks and raises on failure; Bryson cost design. |
| **`ros2_control` integration** | 20 | The LQR loads beside the PID, uses the real `period`, reads/writes interfaces, switches at runtime. |
| **Integral action + scheduling** | 20 | LQI rejects a disturbance to zero steady-state; gain scheduling interpolates solved gains and beats a fixed gain across the speed range. |
| **Single-source-of-truth discipline** | 10 | The `grep` check is clean; plugin and benchmark import from `lqr.py`; cost in YAML, law in code. |
| **Benchmark + verdict** | 15 | The harness is fair (same conditions both controllers); the table is real; the verdict is honest about where LQR does and doesn't win. |
| **Tests + hygiene** | 10 | `test_lqr.py` covers the four behaviors; `colcon test` green; clean commits; no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to host MPC next week. **70–89** works but has a soft sanity check or an unfair benchmark. **Below 70** means the LQR isn't actually verified before deployment or the comparison isn't fair — fix that first.

---

## Stretch goals

- **LQR on a Kalman-estimated state.** Wire a Kalman filter (the LQR/LQE dual, Lecture 2 §5) onto noisy measurements and feed the LQR the estimate — a live demonstration of the separation principle on your robot.
- **Discrete-time LQR.** Add a `solve_discrete_are` path for slow loops and let the YAML select continuous vs. discrete. Quantify when the difference matters.
- **Finite-horizon LQR.** Implement the backward Riccati recursion and watch the time-varying gain converge to the steady-state gain — the conceptual bridge to next week's MPC.
- **CI job.** A GitHub Actions workflow that builds, runs `colcon test`, and runs the benchmark headless, asserting the LQR passes its sanity checks and the comparison table is produced.

---

## How this connects to the rest of C24

- **Week 22 (MPC)** adds the MPC controller to *this same package*. MPC handles the hard constraints LQR can't, and often runs as an outer loop generating the reference an inner controller tracks. The benchmark harness extends to a three-way PID/LQR/MPC comparison.
- **Week 24 (integration)** folds `crunchbot_control` into the integrated launch graph; the Phase 3 milestone grades whether your controllers are framework citizens *and* whether you can defend the choice between them. This mini-project's benchmark is that defense, built three weeks early.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
