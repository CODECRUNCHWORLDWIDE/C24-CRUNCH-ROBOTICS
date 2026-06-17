# Lecture 2 — Feedforward, Tuning, and `ros2_control`

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can add a feedforward term that does most of the tracking work, tune a PID three different ways and explain the trade-offs, and ship the whole thing as a `ros2_control` controller plugin instead of a one-off node.

Lecture 1 built a robust PID — the feedback loop that cleans up error. This lecture is about three things that turn a robust feedback loop into a *good controller*: (1) **feedforward**, which does the predictable work so feedback only handles surprises; (2) **tuning**, done with method instead of luck; and (3) **`ros2_control`**, the framework that makes your controller a citizen of the robot's real-time stack instead of a rogue node racing the diff-drive controller for the wheels.

---

## Part 1 — Feedforward: stop making feedback do all the work

### 1.1 The core idea

Feedback is *reactive*: it can only respond to error after the error exists. That's a fundamental limitation — when you're tracking a moving reference, feedback is always chasing, always a step behind, always lagging. Feedforward is *predictive*: it computes a command directly from the **reference**, before any error has occurred, using whatever you know about the plant.

The two-degree-of-freedom controller looks like this:

```
              ┌──────────────┐
   r(t) ──┬──►│ feedforward  │── u_ff ──┐
          │   │   (model)    │          │
          │   └──────────────┘          ▼
          │                            (+)──► u ──►[ plant ]──► y
          │   ┌──────────────┐          ▲
          └──►(−)──► e ──────►│ PID feedback │─ u_fb ┘
              ▲               └──────────────┘
              └────────────────────────────── y
```

The total command is `u = u_ff + u_fb`. The feedforward term `u_ff` is your *best open-loop guess* at the input the plant needs to follow the reference. The feedback term `u_fb` is the PID cleaning up the difference between your guess and reality. **A good feedforward term removes most of the tracking error before the feedback loop ever sees it** — which means you can run gentler feedback gains, get less overshoot, and track a moving target without the chronic lag of pure feedback.

### 1.2 The three feedforward terms

For a typical mechanical system, the feedforward is built from the reference and its derivatives:

```
u_ff = Ks·sign(v_ref) + Kv·v_ref + Ka·a_ref + (gravity/load term)
```

- **Static / friction feedforward** `Ks·sign(v_ref)`. Real actuators have static friction (stiction) and a deadband — below some command, nothing moves. The static term pre-loads the actuator past that deadband in the direction of motion. On a robot arm this also includes **gravity compensation**: the torque needed to hold the arm against gravity at the current configuration, computed from the model. This is the term that lets a well-modeled arm hold its pose with *zero* feedback effort.
- **Velocity feedforward** `Kv·v_ref`. Most actuators have a roughly linear steady-state map from command to velocity. If you want the joint moving at `v_ref`, the steady-state command is approximately `Kv·v_ref` — so just *command it directly* instead of waiting for the feedback loop to discover it through accumulated error. This is the single highest-value feedforward term for trajectory tracking.
- **Acceleration feedforward** `Ka·a_ref`. To *accelerate* the load you need extra command proportional to the desired acceleration (Newton's second law: more torque for more `a`). When your trajectory has a known acceleration profile (every Nav2 and MoveIt2 trajectory does), feeding `a_ref` forward removes the lag during the fast parts of the move.

### 1.3 Where the feedforward gains come from

This is the key conceptual point, and it's the bridge to next week: **feedforward gains come from a *model*, not from tuning.** `Kv` is approximately the inverse of your plant's steady-state gain. `Ka` is approximately the inertia/mass. The gravity term is computed from the kinematic model. You can *identify* these from a simple experiment (command a constant velocity, measure the steady-state command — that ratio is `1/Kv`), or read them off a datasheet, or compute them from a URDF's inertials. Feedback gains you tune by feel; feedforward gains you derive from physics. That division of labor — **feedforward from the model, feedback for the residual** — is exactly the philosophy that LQR (next week) and MPC (the week after) formalize.

### 1.4 Why tracking *needs* feedforward and regulation often doesn't

Back to the regulation/tracking distinction. For **regulation** (hold a fixed yaw), the reference doesn't move, `v_ref = a_ref = 0`, and the only feedforward worth having is the static/gravity term. Feedback alone can hold a setpoint perfectly well (the integral term takes care of the steady offset). For **tracking** (follow a yaw-rate profile around a curve), feedback alone *always lags* — by the time it has built up enough error to respond, the reference has moved on. The velocity and acceleration feedforward terms cancel that lag at the source. This is why path-tracking controllers (Nav2's pure pursuit, the MPC you write in Week 22) are feedforward-dominated: the plan *tells you* the velocity and curvature you should command; feedback only corrects for the model being slightly wrong. **If you take one habit from this week into the rest of the track, take this: when there's a reference trajectory, feed it forward.**

---

## Part 2 — Tuning, three ways

You have a controller with up to six knobs (`Kp`, `Ki`, `Kd`, `Tf`, plus the feedforward gains). How do you set them? Three methods, in increasing order of rigor.

### 2.1 The structured manual loop

Not random poking — a *procedure*. This is what you'll do most often in practice, and it works because it changes one thing at a time and watches the step response.

1. **Zero everything.** `Ki = Kd = 0`. Set up your step-response test (command a step, log setpoint and measurement, plot).
2. **Raise `Kp`** until the response is fast and just *begins* to overshoot a little. If it oscillates and won't stop, you've gone too far — back off to about half.
3. **Add `Kd`** to damp the overshoot. Increase it until the overshoot is gone or within spec and the response is crisp. Too much `Kd` makes it sluggish and noisy — that's your upper limit.
4. **Add `Ki`**, a *little*, only if you have steady-state error to kill. Increase slowly; too much I brings back overshoot and oscillation. The goal is the *minimum* `Ki` that zeroes the offset in acceptable time.
5. **Re-check the whole step response** against your spec (rise, overshoot, settling, steady-state). Iterate.

The discipline is "one gain at a time, look at the plot, name the symptom, name the gain that owns it." Overshoot too high? It's `Kp` (too much) or `Kd` (too little). Settling too slow? `Kp` too low or `Ki` too low. Steady-state offset? `Ki` too low. Chatter? `Kd` too high or filter too weak. Memorize that symptom→gain map; it *is* manual tuning.

### 2.2 Ziegler–Nichols (and why you'll rarely ship it)

The classic heuristic. The **ultimate-gain method**:

1. Set `Ki = Kd = 0`. Raise `Kp` until the system oscillates with a *constant* amplitude (sustained oscillation). Call that gain `Ku` (the ultimate gain) and the oscillation period `Tu`.
2. Read the gains from the Z–N table:

| Controller | `Kp` | `Ki` | `Kd` |
|---|---|---|---|
| P | 0.5·Ku | — | — |
| PI | 0.45·Ku | 0.54·Ku/Tu | — |
| PID | 0.6·Ku | 1.2·Ku/Tu | 0.075·Ku·Tu |

The **honest assessment**: Ziegler–Nichols gives you a *starting point*, fast, from one experiment. But its gains are notoriously **aggressive** — tuned for disturbance rejection with a ~25% overshoot target that is unacceptable for most robots and brutal on actuators. You will almost never ship Z–N gains; you'll use them to get in the right *neighborhood* and then back off `Kp` and `Ki` substantially. It's also dangerous to run a real robot into sustained oscillation to find `Ku` — do it in simulation. Know the method, respect its history, don't trust its numbers.

### 2.3 Optimization-based auto-tuning

The modern way, and the one that scales: define a *cost* over the step response and let an optimizer find the gains that minimize it. Common cost functions, integrated over the response:

- **ISE** (Integral of Squared Error) `∫e² dt` — penalizes large errors hard, tends toward fast but oscillatory.
- **IAE** (Integral of Absolute Error) `∫|e| dt` — gentler, balanced.
- **ITAE** (Integral of Time-weighted Absolute Error) `∫t·|e| dt` — penalizes errors that *persist*, so it produces well-damped responses that settle quickly. The usual default for a clean step response.

You wrap your simulated step response in a function that returns the cost given a gain vector, and minimize it:

```python
import numpy as np
from scipy.optimize import minimize

def simulate_step(gains, plant, dt=0.01, t_end=4.0):
    kp, ki, kd = gains
    pid = ProductionPID(kp, ki, kd, dt, u_min=-5, u_max=5, tf=0.02)
    y, t = 0.0, 0.0
    cost = 0.0
    setpoint = 1.0
    state = plant.reset()
    while t < t_end:
        u = pid.update(setpoint, y)
        y, state = plant.step(u, state, dt)   # your second-order plant
        cost += t * abs(setpoint - y) * dt      # ITAE
        t += dt
    return cost

def itae_cost(gains, plant):
    if any(g < 0 for g in gains):
        return 1e9                              # gains must be non-negative
    return simulate_step(gains, plant)

result = minimize(itae_cost, x0=[1.0, 0.1, 0.05], args=(plant,),
                  method="Nelder-Mead",
                  options={"xatol": 1e-3, "fatol": 1e-3})
kp_opt, ki_opt, kd_opt = result.x
```

`Nelder-Mead` (a derivative-free simplex method) is a fine choice here because the cost is non-smooth and cheap to evaluate. The catch — and it's a real one — is that **the optimizer is only as good as your plant model**. Auto-tuning against a perfect simulation gives gains that may be too hot for the real, friction-and-backlash-ridden hardware. Use auto-tuning to get an excellent starting point on your *model*, then validate and back off on the real robot. The optimizer will also happily hand you gains you'd never ship (enormous `Kd`, or gains that exploit a quirk of your sim) — which is itself instructive about what your cost function actually rewards. You'll do this in the mini-project and compare the auto-tuned gains to your hand-tuned ones.

### 2.4 Identifying the feedforward gains from a simple experiment

Part 1 claimed feedforward gains come from a model. Here's how you actually *get* them on a robot you don't have a clean datasheet for — a one-afternoon system-identification experiment that you'll reuse all the way into Week 22.

To find `Kv` (the velocity feedforward gain), run the actuator open-loop at several constant commands and measure the steady-state velocity each one produces:

```python
# Command u, wait for steady state, record measured velocity. Repeat for several u.
commands = [0.2, 0.4, 0.6, 0.8, 1.0]
steady_velocities = [measure_steady_state_velocity(u) for u in commands]
# The plant's steady-state gain K is the slope velocity/command; Kv = 1/K.
import numpy as np
K = np.polyfit(commands, steady_velocities, 1)[0]   # slope
kv = 1.0 / K
```

The logic: at steady state the plant maps command to velocity by some gain `K` (`v_ss = K·u`). If you *want* velocity `v_ref`, the open-loop command that produces it is `u = v_ref / K = Kv·v_ref` with `Kv = 1/K`. You measured `K`; you inverted it. That's the entire derivation, and it's why the velocity feedforward is "free" once you've characterized the plant — no tuning, just one linear fit.

The same experiment exposes the **static/deadband term**: extrapolate the line back to `v = 0` and the command at which motion *actually starts* (the x-intercept offset) is your stiction/deadband. Pre-load the actuator past it with the `Ks·sign(v_ref)` term and the motor stops having a dead zone around zero command — which is exactly the region where a slow integral would otherwise crawl the robot to its setpoint.

`Ka` (acceleration feedforward) is harder to identify cleanly but follows the same spirit: command a known acceleration profile, measure the extra command needed above the velocity feedforward, and fit the ratio. For most mobile bases `Ka` is small enough to ignore; for a heavy arm or a fast trajectory it earns its place. **The discipline that matters:** every feedforward gain traces back to a measurement or a model parameter you can point at — never to "I tuned it until it looked right." That traceability is what makes feedforward *robust* where feedback is *forgiving*, and it's the mental model that LQR (which derives the *entire* gain matrix from the model and a cost) formalizes next week.

### 2.5 A note on tuning safety

One sentence that has saved more robots than any algorithm: **tune in simulation first, then on hardware with the robot on blocks or in a clear space, then in the real environment — never the other way around.** Ziegler–Nichols literally asks you to drive the system into sustained oscillation; doing that on a 30 kg base in a room with people is how someone gets hurt. The auto-tuner will hand you gains that are optimal for a frictionless sim and dangerous on metal. Every gain you put on real hardware should have been seen first on a plot, and the first hardware run of any new gain set should have a finger on the e-stop. This is not bureaucracy; it is the difference between a controls engineer and an incident report.

---

## Part 3 — `ros2_control`: shipping a controller the right way

So far you've imagined a node that subscribes to the IMU and publishes `/cmd_vel`. That's fine for a lab exercise. It is *not* how production robots run controllers, and here's why it matters.

### 3.1 The problem a controller node creates

If your PID node publishes `/cmd_vel`, it's competing with every other thing that wants to publish `/cmd_vel` — Nav2, the joystick teleop, the safety stop. There's no arbitration, no real-time guarantee, no clean way to switch which controller is active, and the loop runs at whatever rate your ROS executor happens to schedule it, jittering under load. For a safety-relevant control loop, "whenever the executor gets around to it" is not good enough.

### 3.2 The `ros2_control` model

`ros2_control` solves this with a clean architecture:

```
┌──────────────────────────────────────────────────────────┐
│                   controller_manager                       │
│   (owns the real-time update loop; loads/switches          │
│    controllers; arbitrates interface access)               │
│                                                            │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │ your PID    │   │ diff_drive  │   │ joint_state │      │
│   │ controller  │   │ controller  │   │ broadcaster │      │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│          │  command/state interfaces  │              │      │
└──────────┼─────────────────┼──────────┼──────────────┘
           ▼                 ▼          ▼
   ┌──────────────────────────────────────────────────┐
   │        hardware_interface (the robot or sim)       │
   │   command_interfaces: wheel velocity, joint effort │
   │   state_interfaces:    wheel position, velocity    │
   └──────────────────────────────────────────────────┘
```

The pieces:

- **`hardware_interface`** — the abstraction over the actual robot (or `gz_ros2_control` for the sim). It exposes **`command_interface`s** (things you can write — e.g. `wheel_left/velocity`) and **`state_interface`s** (things you can read — e.g. `wheel_left/position`). Your controller never talks to a motor driver directly; it reads and writes named interfaces.
- **`controller_manager`** — one process that owns the *real-time control loop*, loads controllers as plugins, claims interfaces on their behalf (so two controllers can't both command the same wheel), and lets you load / activate / deactivate / switch controllers at runtime via the `ros2 control` CLI.
- **A controller** is a **plugin** (a class implementing `controller_interface::ControllerInterface`) with a defined lifecycle: `on_init` → `on_configure` → `on_activate` → `update(time, period)` (called every control tick, in the real-time loop) → `on_deactivate`. Your PID math lives in `update`.

### 3.3 What `update` looks like

Conceptually (C++ is the production language for the real-time path; the shape is what matters):

```cpp
controller_interface::return_type
MyPidController::update(const rclcpp::Time & time, const rclcpp::Duration & period)
{
  // 1. READ the current state from a state interface.
  const double measured = state_interfaces_[0].get_value();   // e.g. measured yaw rate

  // 2. READ the current reference (from a subscribed command, realtime-buffered).
  const double setpoint = *rt_command_ptr_.readFromRT();

  // 3. COMPUTE: feedforward + PID, using the REAL elapsed period for dt.
  const double dt = period.seconds();
  const double u_ff = kv_ * setpoint;                          // velocity feedforward
  const double u_fb = pid_.computeCommand(setpoint - measured, period);  // control_toolbox
  const double u = u_ff + u_fb;

  // 4. WRITE the command to a command interface (the manager guarantees we own it).
  command_interfaces_[0].set_value(u);
  return controller_interface::return_type::OK;
}
```

Three things to notice. First, `period` is *handed to you* — use it as your `dt`, don't assume a fixed rate. Second, you read state and write command through *named interfaces*, not topics — the manager has guaranteed you exclusive access, so there's no `/cmd_vel` race. Third, the reference comes in over a **realtime-safe buffer** (`realtime_tools::RealtimeBuffer`), because the `update` loop must never block on a mutex or allocate — it runs in the real-time thread. That last point is the cultural difference between a control loop and an ordinary ROS node: **no allocation, no blocking, no surprises in `update`.**

### 3.4 The stock controllers, and when to write your own

`ros2_controllers` ships batteries-included controllers you should use before writing your own:

- **`diff_drive_controller`** — consumes `/cmd_vel`, does the diff-drive inverse kinematics (Week 6), and commands wheel velocity interfaces. For *driving the base* you use this, not a hand-rolled node.
- **`joint_trajectory_controller`** — tracks a trajectory on a set of joints (this is what MoveIt2 commands the arm through), with optional per-joint PID + feedforward. This is the controller your Week 23 arm runs under.
- **`pid_controller`** — a chainable generic PID, configured entirely from YAML. For many single-loop jobs this is all you need.

You write your *own* controller when your control law isn't one of these — a custom yaw-rate regulator, a specialized admittance controller, the LQR you'll write next week, or the MPC the week after (which often runs as a controller that *generates* the reference for an inner `joint_trajectory_controller`). The mini-project this week has you write one real custom controller plugin so you understand the lifecycle from the inside — and so that when you wrap LQR and MPC in the same framework in the next two weeks, the plumbing is already familiar.

### 3.5 Loading and running it

You configure controllers in a YAML, and drive them with the `ros2 control` CLI:

```bash
# What's loaded and what state is it in?
ros2 control list_controllers

# Load and activate your controller against the running manager.
ros2 control load_controller --set-state active crunchbot_yaw_pid

# Inspect the available hardware interfaces (what you can read/write).
ros2 control list_hardware_interfaces
```

The fact that you can *switch* controllers at runtime — deactivate the PID, activate the LQR, compare them on the same hardware without recompiling — is exactly why this framework is worth the upfront ceremony. Next week, comparing LQR to this week's PID is one `ros2 control` command, not a code change.

---

## Part 4 — Putting it together: the controller-design decision flow

When you face a new control problem on the robot, walk this:

```
What am I controlling, and is there a reference trajectory?
│
├─ Is one of the stock controllers a fit?
│   (driving the base → diff_drive_controller;
│    arm trajectory → joint_trajectory_controller)
│   ├─ Yes → use it. Configure its PID + feedforward in YAML. Done.
│   └─ No  → write a custom controller plugin ↓
│
├─ Is there a moving reference (tracking) or a fixed one (regulation)?
│   ├─ Tracking   → feedforward is mandatory. u_ff = Kv·v_ref (+Ka·a_ref).
│   │              Feedback (PID) only cleans up the residual.
│   └─ Regulation → static/gravity feedforward only; PID does the work.
│
├─ Build the feedback PID with ALL THREE fixes (Lecture 1):
│   anti-windup, derivative-on-measurement, derivative filter.
│
├─ Tune: hand-tune to get close, optionally auto-tune on the model,
│   ALWAYS validate on hardware and back off if it's hot.
│
└─ Verify against a SPEC: rise / overshoot / settling / steady-state.
    A controller without a measured spec is a guess.
```

Tape this next to the symptom→gain map from §2.1. Between the two, you can take any single-loop control problem on the robot from blank file to in-spec, shipped plugin.

---

## Part 4.5 — Cascaded control: the structure under everything

One architectural idea ties this week to the next two and to nearly every real robot: **cascaded control.** Instead of one controller doing everything, you nest loops — a fast inner loop and a slower outer loop, each with its own job.

The canonical example is a robot base: an *inner* velocity loop (a PID that makes the wheel actually spin at the commanded velocity, running fast) wrapped by an *outer* position/heading loop (the controller that decides what velocity to command, running slower). The outer loop's *output* is the inner loop's *setpoint*. This is everywhere — every multirotor flight controller is a cascade (position → velocity → attitude → rate, each an inner loop of the one above), every arm joint is a cascade (position → velocity → torque).

Why cascade instead of one big controller? Three reasons. First, **each loop solves a simpler problem**: the inner velocity loop only has to make the wheel track a velocity, which is a clean single-loop PID; the outer loop gets to *assume* the inner loop works and command velocities, not worry about motor dynamics. Second, **the inner loop rejects fast disturbances** (a bump, a load change) before they ever reach the outer loop, which runs too slowly to catch them. Third, **you can tune them independently** — tune the inner loop first (so it tracks velocity well), then tune the outer loop *assuming* the inner one is solid. The rule is that the inner loop must be *significantly faster* than the outer (a factor of ~5–10 in bandwidth) so the outer loop can treat the inner one as "instantaneous and correct."

This matters this week because your `ros2_control` plugin is usually an *inner* loop — the `diff_drive_controller` is the inner velocity loop; Nav2 is the outer loop commanding it `/cmd_vel`. And it matters for the next two weeks because LQR and MPC slot into the *outer* role naturally (they decide what to command), while a fast PID stays inner. When MPC (Week 22) runs at 20 Hz as an outer loop feeding a 200 Hz inner controller, that's a cascade, and the inner controller is exactly the kind of thing you built this week. Recognizing the cascade structure is what lets you decompose a scary "control the whole robot" problem into a stack of tractable single-purpose loops.

## Part 5 — Recap

You should now be able to:

- Explain the two-degree-of-freedom (feedforward + feedback) structure and why feedforward removes tracking error before feedback engages.
- Build the static, velocity, and acceleration feedforward terms, and explain that their gains come from the *model*, not from tuning.
- Connect regulation vs. tracking to whether feedforward is mandatory.
- Tune a PID three ways — the structured manual loop, Ziegler–Nichols (and why you back off its gains), and optimization against an ITAE cost — and state the trade-offs of each.
- Explain the `ros2_control` model — `command_interface` / `state_interface`, the `controller_manager`, the real-time `update` loop — and why a controller is a plugin, not a `/cmd_vel`-publishing node.
- Pick a stock controller when one fits, and write a custom plugin when none does.

Next: the exercises put all of this on your robot — tune a plant to spec, reproduce-and-fix wind-up and kick, and close a real yaw-rate loop with feedforward. Continue to [the exercises](../03-exercises/00-overview.md).

---

## A closing note: the symptom→gain map, one more time

Because it's the most useful single artifact from this week, here it is consolidated — tape it next to your monitor and consult it every time a step response looks wrong:

| Symptom on the plot | Most likely cause | First thing to change |
|---|---|---|
| Slow rise, sluggish | `Kp` too low | raise `Kp` |
| Overshoots, then settles | `Kp` too high or `Kd` too low | add/raise `Kd`, or lower `Kp` |
| Oscillates, won't settle | `Kp` way too high, or `Ki` too high | lower `Kp`; check `Ki` |
| Settles near but not on target | `Ki` too low (or zero) | add/raise `Ki` |
| Overshoots worse on bigger steps | integrator wind-up | add/fix anti-windup (not detune) |
| Command spikes when target changes | derivative kick | derivative on measurement |
| Command chatters / motor whines | `Kd` too high, filter too weak | filter the derivative harder |
| Lags a moving reference | no feedforward | add velocity feedforward |

Notice that two of these rows — wind-up and kick — are *not* fixed by tuning gains at all; they're fixed by the structural changes from Lecture 1. That's the deepest lesson of the week: a misbehaving controller is sometimes a tuning problem and sometimes a *structure* problem, and the senior move is knowing which. Detuning `Ki` to fix wind-up-induced overshoot treats the symptom and ruins your steady-state error; adding anti-windup treats the cause and keeps everything. Diagnose the cause, then reach for the right fix — gain or structure.

## References

- *Feedback Systems* (Åström & Murray), Ch. 11 — feedforward §11.4, two-DOF §11.4–11.5: <https://fbswiki.org/wiki/index.php/Main_Page>
- `ros2_control` — writing a new controller (the plugin lifecycle): <https://control.ros.org/jazzy/doc/ros2_controllers/doc/writing_new_controller.html>
- `diff_drive_controller` userdoc: <https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html>
- `joint_trajectory_controller` userdoc: <https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html>
- `gz_ros2_control` — running `ros2_control` against Gz Sim: <https://github.com/ros-controls/gz_ros2_control>
- Ziegler–Nichols tuning rules (with caveats): <https://en.wikipedia.org/wiki/Ziegler%E2%80%93Nichols_method>
- `scipy.optimize.minimize` (auto-tuning): <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html>
