# Mini-Project — `crunchbot_control`: A Production PID + Feedforward Controller

> Build a reusable, shippable controller package for the crunchbot: a `ros2_control` controller plugin implementing PID with all three fixes (anti-windup, derivative-on-measurement, derivative filter) plus a velocity feedforward term, a parameter surface for the gains, and an offline tuning harness that auto-tunes against a step-response spec and replays your tuned gains on the robot.

This is the artifact that turns "I can write a PID in a notebook" into "I shipped a controller that lives in the robot's real-time stack and that next week's LQR can be swapped against with one CLI command." After this week, control gains are a *configured*, *tuned*, *tested* thing — not magic numbers copy-pasted into a node.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This package is where **Week 21's LQR** and **Week 22's MPC** will also live as controllers. The `ros2_control` plumbing you build here — the plugin lifecycle, the parameter surface, the gain-loading — is reused verbatim; only the control law changes. The Phase 3 milestone in Week 24 explicitly checks that your controllers are framework-citizens with a defensible tuning story. Build it well now; you'll extend it twice and defend it once.

---

## What you will build

A small package `crunchbot_control` with three deliverables:

1. **`crunchbot_control/pid.py`** — the pure-Python `ProductionPID` class (the source of truth for the control law): PID with back-calculation anti-windup, derivative-on-measurement, and a first-order derivative filter, plus a velocity feedforward hook. No ROS dependency — so it's unit-testable and reusable in the offline harness.
2. **The `ros2_control` plugin** — a controller (`crunchbot_control::YawRateController` in C++, *or* a Python equivalent driving `/cmd_vel` if you're staying in Python this week) that wraps the PID, exposes the gains as parameters, reads a yaw/yaw-rate state, and writes an angular-velocity command. It loads under the `controller_manager` and switches at runtime.
3. **`crunchbot_control/tuning_harness.py`** — an offline tool that simulates the closed loop, auto-tunes the gains against an ITAE cost and a step-response spec, writes the winning gains to the controller's params YAML, and produces the step-response plots and metrics that go in your tuning log.

By the end you have a public repo of ~350–500 lines (excluding tests) that any future crunchbot package can load as a controller, and that you can re-tune for new dynamics by running one harness command.

---

## Why a plugin and not a node

You could write a node that subscribes to the IMU and publishes `/cmd_vel`. For this week's *exercises*, that's fine. As the *robot's controller*, it's wrong, and the reasons are the whole point of Lecture 2 §3:

- **Arbitration.** A `/cmd_vel`-publishing node races Nav2, teleop, and the safety stop for the same topic, with no arbitration. The `controller_manager` guarantees exclusive access to the wheel `command_interface`s — two controllers physically cannot fight over the wheels.
- **Real-time loop.** A node runs whenever the executor schedules it, jittering under load. The manager runs the `update` loop in a real-time thread at a guaranteed rate and hands you the true elapsed `period`.
- **Runtime switching.** With the plugin model you `ros2 control load_controller --set-state active` to swap controllers without recompiling. Next week, comparing LQR to this PID is one command. With a node, it's a code change and a relaunch.

YAML is the right place for *gains* (operators tune them per robot). The *control law* lives in code. That division — law in code, gains in params — is the senior-shop convention in 2026 and exactly what this project enforces.

---

## Package layout

```
crunchbot_control/
├── package.xml
├── CMakeLists.txt              # (C++ plugin) OR setup.py for the pure-python path
├── crunchbot_control_plugins.xml   # pluginlib export of the controller
├── include/crunchbot_control/
│   └── yaw_rate_controller.hpp
├── src/
│   └── yaw_rate_controller.cpp # the ros2_control plugin (update loop)
├── crunchbot_control/          # pure-python module (law + harness + tests)
│   ├── __init__.py
│   ├── pid.py                  # ProductionPID — the control law, no ROS
│   ├── feedforward.py          # the static/velocity/accel feedforward terms
│   └── tuning_harness.py       # offline auto-tune + plots + params writer
├── config/
│   └── yaw_rate_controller.yaml  # the gains + limits (operator-tunable)
├── launch/
│   └── controller.launch.py    # bring up the manager + load the controller
└── test/
    ├── test_pid.py             # unit tests: anti-windup, no-kick, dt-correctness
    └── test_feedforward.py     # unit tests: feedforward term values
```

If you stay in Python this week (legitimate — the C++ plugin is a stretch many take in Week 24), replace the C++ controller with a `controller`-style node that still loads its gains from `config/yaw_rate_controller.yaml` and still exposes the same parameter names, so the swap to a real plugin later is mechanical.

---

## Deliverable 1 — `pid.py` (the control law, no ROS)

This is the heart of the project and the thing your tests pin down. It must:

- Implement `ProductionPID` exactly as Lecture 1 §7: proportional on error, integral on error with **back-calculation anti-windup**, derivative on **measurement** (not error), with a **first-order filter** on the derivative.
- Take `dt` per-update if provided (so it works with the real `period` from `ros2_control`) and fall back to a nominal `dt`.
- Saturate the output to `[u_min, u_max]` and never wind the integral past what the actuator can justify.
- Have a clean `reset()` for bumpless re-activation.

Here is the spine to start from; fill in the marked sections yourself:

```python
"""crunchbot_control.pid — the shippable control law. No ROS dependency."""
from __future__ import annotations


class ProductionPID:
    def __init__(self, kp, ki, kd, dt, u_min, u_max, tf=0.0, kb=None):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.dt = dt
        self.u_min, self.u_max = u_min, u_max
        self.alpha = dt / (tf + dt) if tf > 0 else 1.0
        self.kb = kb if kb is not None else (1.0 / ki if ki > 0 else 0.0)
        self.integral = 0.0
        self.prev_meas = 0.0
        self.deriv_filt = 0.0

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_meas = 0.0
        self.deriv_filt = 0.0

    def update(self, setpoint, measurement, dt=None) -> float:
        h = dt if dt is not None and dt > 0 else self.dt
        error = setpoint - measurement

        p = self.kp * error

        # TODO 1: derivative ON MEASUREMENT, then first-order low-pass filter.
        #   raw_d = -(measurement - self.prev_meas) / h
        #   alpha = h / (tf + h)  if you want dt-correct filtering; self.alpha is fine
        #   for a fixed loop. self.deriv_filt += alpha * (raw_d - self.deriv_filt)
        #   d = self.kd * self.deriv_filt

        # TODO 2: unsaturated output, saturate, then back-calculation anti-windup.
        #   u_unsat = p + self.ki * self.integral + d
        #   u = max(self.u_min, min(self.u_max, u_unsat))
        #   self.integral += (error + self.kb * (u - u_unsat)) * h

        self.prev_meas = measurement
        return u  # noqa: F821  (defined once you fill in TODO 2)
```

> **Test-pinned behaviors (these are what `test_pid.py` checks):**
> 1. **dt-correctness** — the same gains at 50 Hz and 200 Hz produce nearly identical step responses (Problem 1).
> 2. **anti-windup** — on a large saturating step, the integral never exceeds the value consistent with `u_max`, and the overshoot stays bounded.
> 3. **no kick** — a setpoint step produces no spike in `u` (because the derivative is on the measurement).

---

## Deliverable 2 — the `ros2_control` plugin

A controller that wraps `ProductionPID` and lives in the manager. It must:

- Implement the lifecycle: `on_init` (declare params), `on_configure` (read gains, construct the PID), `on_activate` (reset the PID, claim interfaces), `update(time, period)` (the control tick), `on_deactivate`.
- In `update`: read the measured yaw/yaw-rate from a **state interface**, read the reference from a realtime-safe buffer (a subscribed `/yaw_setpoint`), compute `u_ff + u_fb`, and write `u` to the angular-velocity **command interface**. **Use the real `period.seconds()` as `dt`.**
- Export the gains (`kp`, `ki`, `kd`, `tf`, `kv`, `u_min`, `u_max`) as parameters, read from `config/yaw_rate_controller.yaml`.
- Be loadable: `ros2 control load_controller --set-state active crunchbot_yaw_rate_controller` brings it up against a running manager.

The conceptual `update` shape (C++; the Python-path equivalent does the same in a timer callback, with the documented caveat that it isn't truly real-time):

```cpp
controller_interface::return_type
YawRateController::update(const rclcpp::Time &, const rclcpp::Duration & period)
{
  const double measured_yaw = state_interfaces_[0].get_value();
  const double setpoint = *rt_setpoint_.readFromRT();
  const double dt = period.seconds();

  const double ref_rate = (setpoint - prev_setpoint_) / dt;
  const double u_ff = kv_ * ref_rate;                       // velocity feedforward
  const double u_fb = pid_.update(setpoint, measured_yaw, dt);  // PID with all 3 fixes
  double u = u_ff + u_fb;
  u = std::clamp(u, u_min_, u_max_);

  command_interfaces_[0].set_value(u);                      // angular velocity command
  prev_setpoint_ = setpoint;
  return controller_interface::return_type::OK;
}
```

> **The `gz_ros2_control` bridge** is how this plugin actually moves the Gz Sim wheels (resources.md links it). Your `<ros2_control>` tag in the robot xacro declares the interfaces; the controller claims them.

---

## Deliverable 3 — the tuning harness

`tuning_harness.py` is the offline tool that makes tuning reproducible instead of a vibe. It must:

1. Simulate the closed loop (`ProductionPID` + a plant model — the second-order plant from Exercise 1 or your identified yaw plant) for a given gain vector and setpoint.
2. Compute the four step-response metrics (`analyze_step` from Exercise 1).
3. Auto-tune `Kp`, `Ki`, `Kd` with `scipy.optimize.minimize` over an ITAE cost summed across the three setpoints (45°/90°/180°), so the optimizer can't cheat by acing one and failing another.
4. **Write the winning gains into `config/yaw_rate_controller.yaml`** so the controller picks them up on next load — closing the loop from "tuned in sim" to "running on the robot."
5. Emit the three step-response plots and the metrics table for the tuning log.

```bash
# Auto-tune and write the gains the controller will load:
python3 crunchbot_control/tuning_harness.py --autotune --write-config

# Just score the current config's gains and emit plots:
python3 crunchbot_control/tuning_harness.py --score --plot
```

Expected shape of the harness output:

```
TUNING crunchbot_control yaw_rate_controller
  optimizer: Nelder-Mead over ITAE summed across [45, 90, 180] deg
  found: Kp=7.91  Ki=3.84  Kd=1.18  (tf=0.02, kv=1.0)
  setpoint  rise    overshoot  settling  ss_error  verdict
  45 deg    0.52 s   6.1 %      1.21 s    0.21 deg  PASS
  90 deg    0.55 s   8.4 %      1.40 s    0.28 deg  PASS
  180 deg   0.61 s  11.2 %      1.92 s    0.33 deg  PASS
  wrote config/yaw_rate_controller.yaml
```

---

## Rules

- **You may** read the ROS2 docs, the `ros2_control` docs, `control_toolbox` source, and the lecture notes.
- **You must not** hand-roll PID math anywhere except `pid.py`. The plugin and the harness both import `ProductionPID`. If `grep -rn "integral +=" --include=*.py | grep -v pid.py` returns anything, you've broken the single-source-of-truth rule.
- **You must** use the real elapsed `period` as `dt` in the plugin's `update`, not a hardcoded constant.
- **You must not** depend on anything outside the ROS2 Jazzy desktop install plus `numpy`, `scipy`, `matplotlib`, and `pytest`.
- Python 3.12 (Ubuntu 24.04 default), `rclpy`/`ros2_control` on Jazzy.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-20-crunchbot-control-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_control` succeeds with no warnings.
- [ ] `pid.py` implements all three fixes (anti-windup, derivative-on-measurement, filter) and takes `dt` per-update.
- [ ] `grep -rn "integral +=" --include=*.py` finds matches **only** in `pid.py`.
- [ ] `colcon test --packages-select crunchbot_control` passes, with at least:
  - `test_pid.py`: dt-correctness (50 vs 200 Hz), anti-windup (bounded integral on a saturating step), no-kick (no `u` spike on a setpoint step).
  - `test_feedforward.py`: the velocity/accel feedforward terms return the expected values.
- [ ] `ros2 control list_controllers` shows your controller; loading and activating it drives the robot (or sim) to a `/yaw_setpoint`.
- [ ] `tuning_harness.py --autotune --write-config` produces a passing metrics table and writes the gains YAML.
- [ ] A `README.md` in the repo root with the run commands, the final gains, the metrics table, and a paragraph on why the law lives in code and the gains live in YAML.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Control-law correctness** | 25 | `pid.py` implements all three fixes correctly; the anti-windup is real back-calculation; `dt` is handled per-update; no kick. |
| **`ros2_control` integration** | 25 | The controller loads under the manager, uses the real `period`, reads state and writes command through interfaces (not `/cmd_vel`), and switches at runtime. |
| **Single-source-of-truth discipline** | 15 | The `grep` check is clean; plugin and harness import `ProductionPID`; gains in YAML, law in code. |
| **Tuning harness** | 20 | Auto-tunes against a multi-setpoint ITAE cost; writes the gains YAML; emits the metrics table and plots; results pass the spec. |
| **Tests** | 10 | Unit tests cover dt-correctness, anti-windup, and no-kick; `colcon test` green. |
| **Docs & hygiene** | 5 | Clear README, no inline PID math outside `pid.py`, sensible commits, no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to host LQR and MPC in Weeks 21–22. **70–89** works but has drift or a soft anti-windup. **Below 70** means the controller isn't actually a framework citizen or the anti-windup isn't real — fix that first.

---

## Stretch goals

- **Write the real C++ plugin** (if you took the Python path) and confirm `ros2 control list_controllers` shows it. This is the Week 24 stretch pulled forward.
- **Gain scheduling.** Schedule the gains on error magnitude (Challenge 1 stretch) and expose the schedule as parameters. Prove it beats the single gain set across the 45/90/180 range.
- **Chainable controller.** Make the controller *chainable* (it exposes a reference interface another controller can write) so an outer position loop can command the inner yaw-rate loop — the cascade structure used in every flight controller and the structure MPC will use in Week 22.
- **CI job.** A GitHub Actions workflow that builds the package, runs `colcon test`, and runs the tuning harness headless, asserting the metrics pass. Green check on every push.

---

## How this connects to the rest of C24

- **Week 21 (LQR)** adds an `LqrYawController` to *this* package — same plugin plumbing, same param/YAML surface, a different control law solved from a model. You'll `ros2 control` swap between PID and LQR and compare on the same robot.
- **Week 22 (MPC)** adds the MPC controller here too, often as an outer loop that *generates* the reference this PID tracks. The feedforward habit you built carries straight in.
- **Week 24 (integration)** folds `crunchbot_control` into the integrated launch graph and the Phase 3 milestone grades whether your controllers are framework citizens with a defensible tuning story. This mini-project is that story, built four weeks early. Push it, keep the repo, extend it twice.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
