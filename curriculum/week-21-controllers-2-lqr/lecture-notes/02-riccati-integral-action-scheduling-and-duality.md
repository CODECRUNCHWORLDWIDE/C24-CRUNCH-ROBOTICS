# Lecture 2 — Solving the Riccati Equation, Integral Action, Gain Scheduling, and the LQR/LQE Duality

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can solve the algebraic Riccati equation for the optimal gain, add integral action for zero steady-state error, schedule gains across operating points, ship the controller as a `ros2_control` plugin, and explain why the Kalman filter is LQR's mathematical twin.

Lecture 1 gave you the four ingredients: `A`, `B`, `Q`, `R`. This lecture turns them into a gain, makes that gain track a reference without offset, makes it work across the robot's whole speed range, puts it in the real-time stack, and reveals that the same machinery you just learned for *control* also solves *estimation*. Four parts, each a thing you'll do in the exercises and the mini-project.

---

## Part 1 — The algebraic Riccati equation and the optimal gain

### 1.1 Where the gain comes from

Minimizing the LQR cost `J = ∫(xᵀQx + uᵀRu) dt` over all feedback laws is a calculus-of-variations problem. We will not derive it from scratch (the curious should read Bertsekas or the Underactuated Robotics LQR chapter — the dynamic-programming derivation is beautiful), but here is the result, which is all you need to *use* LQR:

The optimal control is **linear state feedback**, `u = −Kx`, where the gain is:

```
K = R⁻¹ Bᵀ P
```

and `P` is the unique symmetric positive-definite solution of the **continuous-time algebraic Riccati equation (CARE)**:

```
AᵀP + PA − PBR⁻¹BᵀP + Q = 0
```

That quadratic-in-`P` matrix equation is the Riccati equation. You **never** solve it by hand — it's a nonlinear matrix equation and solving it numerically is a solved problem with a robust, well-conditioned algorithm (the Schur method). `scipy` ships it.

### 1.2 The solve, in three lines

```python
import numpy as np
from scipy.linalg import solve_continuous_are

def lqr(A, B, Q, R):
    """Continuous-time infinite-horizon LQR. Returns gain K and Riccati solution P."""
    P = solve_continuous_are(A, B, Q, R)      # solve the CARE
    K = np.linalg.inv(R) @ B.T @ P            # K = R^-1 B^T P
    return K, P

A = np.array([[0.0, 0.5], [0.0, 0.0]])         # diff-drive error dynamics, v_ref=0.5
B = np.array([[0.0], [1.0]])
Q = np.diag([100.0, 25.0])                     # Bryson: 1/0.1^2, 1/0.2^2
R = np.array([[1.0]])

K, P = lqr(A, B, Q, R)
print("K =", K)            # e.g. [[10.0, 6.7]] — one gain per state
```

That's it. `K` is a `1×2` matrix here (one input, two states) — the optimal feedback gain on cross-track error and heading error. The control law is `u = −K @ (x − x_ref)`.

### 1.3 The three sanity checks (run them every time)

A gain from a solver is not a gain you trust until it passes three checks. Make them a reflex:

```python
# 1. P is symmetric positive-definite (the solution is valid).
assert np.allclose(P, P.T), "P not symmetric — solve failed"
assert np.all(np.linalg.eigvals(P) > 0), "P not positive-definite"

# 2. The closed loop is stable: eigenvalues of (A - B K) all have negative real part.
cl_eig = np.linalg.eigvals(A - B @ K)
assert np.all(np.real(cl_eig) < 0), f"closed loop UNSTABLE: {cl_eig}"
print("closed-loop eigenvalues:", cl_eig)      # all in the left half plane

# 3. (From Lecture 1) the system was controllable before you ever solved.
```

If `P` isn't positive-definite, your `Q` is probably not positive-semidefinite or your problem isn't controllable. If any closed-loop eigenvalue has non-negative real part, *do not put this gain on a robot* — something in your model or cost is wrong. These three checks catch essentially every "my LQR is behaving insanely" bug before it reaches hardware. Cross-check the whole thing against `python-control`'s `lqr` (Exercise 2) and you've belt-and-suspendered it.

### 1.4 Discrete-time LQR (when your loop is slow)

Your controller runs at a sample rate, not continuously. For fast loops (say 100+ Hz relative to the dynamics) the continuous gain is fine. For slower loops, solve the **discrete** Riccati equation against the discretized model:

```python
from scipy.linalg import solve_discrete_are
from scipy.signal import cont2discrete

# Discretize (A, B) at the control period dt.
Ad, Bd, *_ = cont2discrete((A, B, np.eye(A.shape[0]), 0), dt=0.02)
Pd = solve_discrete_are(Ad, Bd, Q, R)
Kd = np.linalg.inv(R + Bd.T @ Pd @ Bd) @ (Bd.T @ Pd @ Ad)
```

Note the discrete gain formula is different (`K = (R + BᵀPB)⁻¹BᵀPA`). For this week's fast loops the continuous solve is the default; know the discrete one exists and matters when `dt` is large relative to the dynamics.

---

## Part 2 — Integral action: zero steady-state error

### 2.1 The problem with pure LQR

Pure LQR is a **regulator** — it drives the state to zero, optimally. But like a P-only controller (Week 20 §2.1), it leaves **steady-state error** against a persistent disturbance. If there's a constant disturbance (a wheel-radius miscalibration, a steady crosswind, a slope), the LQR settles at the error where the feedback push balances the disturbance — a permanent offset. LQR has no memory; nothing accumulates to cancel a constant disturbance. Sound familiar? It's the exact same gap PID fills with its integral term.

### 2.2 The fix: state augmentation (LQI)

The fix is the same idea as PID's I term, expressed in state-space: **augment the state with the integral of the tracking error**, then run LQR on the bigger system. Define a new state `x_i` with `ẋ_i = e = (reference − measured output)`, stack it onto the original state, and form the augmented dynamics:

```
augmented state:  x_aug = [ x  ]      x_i = ∫ (r − y) dt
                          [ x_i]

       d/dt [ x  ]   [ A   0 ] [ x  ]   [ B ]        [ 0 ]
            [ x_i] = [-C   0 ] [ x_i] + [ 0 ] u  +   [ I ] r
                      └── A_aug ──┘       └B_aug┘
```

Now run ordinary LQR on `(A_aug, B_aug)` with an augmented `Q` whose extra diagonal entry penalizes accumulated error. The resulting controller has an integral term baked in — it drives steady-state error to zero exactly the way PID's I term does, and you tune "how aggressively it integrates" through the augmented `Q` entry instead of a separate `Ki`.

```python
def lqi(A, B, C, Q, R):
    """LQR with integral action. C selects the tracked output. Returns K_aug."""
    n, m = A.shape[0], B.shape[1]
    p = C.shape[0]
    A_aug = np.block([[A, np.zeros((n, p))],
                      [-C, np.zeros((p, p))]])
    B_aug = np.vstack([B, np.zeros((p, m))])
    K_aug, _ = lqr(A_aug, B_aug, Q, R)         # Q is now (n+p) x (n+p)
    return K_aug         # split into [K_state | K_integral] when you apply it
```

The control law becomes `u = −K_state·x − K_integral·x_i`, with `x_i` integrated each tick. This is the LQI controller, and it's what you ship when steady-state accuracy matters — which on a path-tracking robot, it does. Apply anti-windup to `x_i` exactly as you did to PID's integral last week; a saturating actuator winds up an LQI integrator just as readily.

---

## Part 3 — Gain scheduling: one controller across the envelope

Recall from Lecture 1 that the linearization — and therefore `A`, and therefore `K` — depends on the operating point. The diff-drive error dynamics had `v_ref` sitting inside `A`. So the gain that's optimal at 0.5 m/s is *not* optimal at 1.5 m/s. One fixed `K` is a compromise across the speed range.

**Gain scheduling** is the principled fix: solve LQR at several operating points, store the gains, and interpolate at runtime based on the current operating point.

```python
import numpy as np

# Solve LQR at a grid of reference speeds.
speeds = np.array([0.2, 0.5, 1.0, 1.5])
gains = []
for v in speeds:
    A = np.array([[0.0, v], [0.0, 0.0]])
    B = np.array([[0.0], [1.0]])
    K, _ = lqr(A, B, Q, R)
    gains.append(K.flatten())
gains = np.array(gains)          # shape (4, 2): one gain row per speed

def scheduled_gain(v_current):
    """Linearly interpolate the LQR gain for the current speed."""
    k0 = np.interp(v_current, speeds, gains[:, 0])
    k1 = np.interp(v_current, speeds, gains[:, 1])
    return np.array([[k0, k1]])
```

At each control tick you read the current speed, interpolate the gain, and use it. This is the rigorous version of last week's hand-rolled gain scheduling (Week 20 Challenge 1) — instead of guessing which gains to use when, you *solve* for the optimal gain at each operating point and interpolate between solved points. Schedule on whatever parameter moves the dynamics: speed for a base, payload mass or arm configuration for a manipulator. Keep the grid fine enough that interpolation between adjacent points is accurate, coarse enough that you're not solving a hundred Riccati equations.

> **A caution:** gain scheduling assumes the operating point moves *slowly* relative to the dynamics. If your speed changes faster than the controller can adapt, scheduling can misbehave, and you're in territory where MPC (next week, which re-optimizes every step) is the cleaner tool. For a base whose speed changes over seconds, scheduling is fine and standard.

---

## Part 4 — Shipping LQR as a `ros2_control` plugin

Here's the payoff of having built the `ros2_control` plumbing last week: **the LQR controller is the same plugin shape as the PID, with the control law swapped.** Everything you learned in Week 20 §3 — the lifecycle, command/state interfaces, the real-time `update`, loading via the manager — applies unchanged.

```cpp
controller_interface::return_type
LqrPathController::update(const rclcpp::Time &, const rclcpp::Duration & period)
{
  // 1. READ the error state from state interfaces (cross-track + heading error).
  Eigen::Vector2d x;
  x << state_interfaces_[0].get_value(),    // cross-track error e_y
       state_interfaces_[1].get_value();    // heading error e_theta

  // 2. SCHEDULE the gain for the current speed (Part 3).
  const double v = *rt_speed_.readFromRT();
  const Eigen::RowVector2d K = scheduled_gain(v);

  // 3. INTEGRAL state update with anti-windup (Part 2).
  const double dt = period.seconds();
  x_i_ += (0.0 - x(0)) * dt;                 // integrate cross-track error
  // ... anti-windup clamp on x_i_ ...

  // 4. CONTROL LAW: u = -K x - k_i x_i, then saturate.
  double u = -(K * x)(0) - k_integral_ * x_i_;
  u = std::clamp(u, u_min_, u_max_);

  // 5. WRITE the yaw-rate correction to the command interface.
  command_interfaces_[0].set_value(u);
  return controller_interface::return_type::OK;
}
```

Same five-step shape as last week's PID `update`: read state, compute, write command, with the real `period` as `dt`. The difference is purely the control law — `u = −Kx` instead of the three PID terms. And because both are controllers under the same manager, **comparing them is one CLI command**:

```bash
# Deactivate the PID, activate the LQR, on the same running robot, no recompile.
ros2 control set_controller_state crunchbot_pid inactive
ros2 control set_controller_state crunchbot_lqr active
```

That runtime swap is exactly how Exercise 3 and the mini-project put LQR and PID head-to-head on the *same* curved trajectory under the *same* conditions — the only fair way to compare two controllers. This is why we spent the ceremony on `ros2_control` last week: controller comparison becomes an experiment, not a code rewrite.

---

## Part 5 — The LQR/LQE duality: why the Kalman filter is LQR backwards

This is the conceptual capstone of the week, and one of the most beautiful facts in control theory. You've been running a Kalman filter since Week 10 (`robot_localization`'s EKF). Here's the secret: **the optimal estimator (the Kalman filter, a.k.a. LQE — Linear Quadratic Estimator) is the mathematical dual of the optimal controller (LQR).** Same Riccati machinery, run on the transposed system.

### 5.1 The duality, made precise

| | LQR (control) | LQE / Kalman (estimation) |
|---|---|---|
| Solves | `AᵀP + PA − PBR⁻¹BᵀP + Q = 0` | `AΣ + ΣAᵀ − ΣCᵀV⁻¹CΣ + W = 0` |
| For | gain `K = R⁻¹BᵀP` | gain `L = ΣCᵀV⁻¹` |
| "Cost" weights | `Q` (state), `R` (effort) | `W` (process noise), `V` (measurement noise) |
| System pair | `(A, B)` | `(Aᵀ, Cᵀ)` |

Look at the two Riccati equations. They are the *same equation* with the substitution `A → Aᵀ`, `B → Cᵀ`, `Q → W`, `R → V`. That means you can solve a Kalman filter design by calling your *LQR solver* on the transposed system:

```python
def kalman_gain(A, C, W, V):
    """The Kalman gain via the LQR/LQE duality: LQR on the transposed system."""
    # Solve the LQR-shaped Riccati on (A^T, C^T) with W, V as the weights.
    Sigma = solve_continuous_are(A.T, C.T, W, V)   # same solver, transposed system
    L = Sigma @ C.T @ np.linalg.inv(V)
    return L
```

The controllability you check for LQR becomes **observability** for the estimator (which is why observability is "controllability of the transpose"). The "can I steer every state" question becomes "can I see every state." Same theorem, two faces.

### 5.2 The separation principle, and why it matters

The duality leads to the **separation principle**: you can design the optimal *estimator* and the optimal *controller* completely independently, then bolt them together (feed the estimated state into the LQR), and the combination is *still* optimal. This is not obvious — you might expect the estimator and controller to need joint design — but for linear-quadratic-Gaussian problems it's a theorem. It's why your robotics stack can have a *perception/estimation* team and a *controls* team that work separately, why `robot_localization` (estimation) and your controller (control) are different packages, and why you could spend Weeks 9–16 on estimation and Weeks 20–22 on control without ever co-designing them. The whole modular architecture of a robotics autonomy stack rests on this one result. When you wire an LQR controller onto a Kalman-estimated state (the stretch goal this week), you are *using* the separation principle — and now you know why it's allowed.

---

## Part 5.5 — Worked solve: stabilizing the cart-pole

Lecture 1 §7 built the unstable cart-pole model. Here's the payoff — solving its LQR and watching optimal feedback hold an inverted pole upright. This is the example to run *first*, before your robot, because stabilizing an open-loop-unstable system is the strongest possible confirmation your LQR pipeline works.

```python
import numpy as np
from scipy.linalg import solve_continuous_are

def cartpole_AB(M=1.0, m=0.2, l=0.5, g=9.81):
    A = np.array([[0, 1, 0, 0],
                  [0, 0, -m * g / M, 0],
                  [0, 0, 0, 1],
                  [0, 0, (M + m) * g / (M * l), 0]])
    B = np.array([[0], [1 / M], [0], [-1 / (M * l)]])
    return A, B

A, B = cartpole_AB()
# Bryson-ish cost: care most about the pole angle (don't let it fall), some about
# cart position, little about velocities; modest effort penalty.
Q = np.diag([1.0, 1.0, 10.0, 1.0])     # phi (index 2) weighted heaviest
R = np.array([[0.1]])

P = solve_continuous_are(A, B, Q, R)
K = np.linalg.inv(R) @ B.T @ P
cl = np.linalg.eigvals(A - B @ K)
print("gain K =", np.round(K, 2))
print("open-loop eigs (one unstable):", np.round(np.linalg.eigvals(A), 2))
print("closed-loop eigs (all stable): ", np.round(cl, 2))
assert np.all(np.real(cl) < 0), "LQR failed to stabilize the cart-pole"
print("STABILIZED: optimal feedback holds the inverted pole upright.")
```

Run it. The open-loop eigenvalues include a positive-real-part one (the pole falls); the closed-loop eigenvalues are *all* in the left half plane (the pole is held up). You just stabilized an unstable system with four numbers from a solver and no manual tuning. Simulate `ẋ = (A − BK)x` from a small initial pole tilt and watch it return to upright. If your code does this, you trust it on the diff-drive robot — whose job (correcting drift) is strictly easier than balancing a falling pole. The cart-pole is the controls field's standard sanity test for exactly this reason; make it yours.

A second lesson hides in the `Q` here: weighting the pole angle (`Q[2,2] = 10`) far above the cart position says "I care much more about not falling over than about exactly where the cart ends up." Change that weight and re-solve, and you'll see the controller trade pole-uprightness against cart-positioning differently — design intent expressed in the cost, mechanics handled by the solver, exactly as promised. That is LQR's whole value proposition in one editable line.

## Part 6 — The LQR design decision flow

When you face a multivariable control problem, walk this:

```
Is the problem multivariable / strongly coupled, or could PID handle it?
│
├─ Single loop, weak coupling → use last week's PID. Don't over-engineer.
│
├─ Multivariable / coupled → LQR:
│   1. MODEL: linearize to get (A, B) at the operating point.
│   2. CHECK: controllability rank == n. If not, stop and understand the mode.
│   3. COST: Q, R from Bryson's rule; iterate on the Q/R ratio, not the gains.
│   4. SOLVE: solve_continuous_are -> K = R^-1 B^T P.
│   5. VERIFY: P pos-def; closed-loop eigenvalues all stable.
│   6. Need zero steady-state error? -> augment with integral (LQI).
│   7. Operating point moves a lot? -> gain-schedule across the envelope.
│   8. SHIP: as a ros2_control plugin; compare to PID via a runtime swap.
│
└─ Hard constraints (velocity/accel limits, obstacles)? -> LQR can't. Next week: MPC.
```

Tape this next to last week's controller-design flow. Between PID, LQR, and (next week) MPC, you have a controller for nearly any robot subsystem and the judgment to pick the right one.

---

## Part 6.5 — A note on what "optimal" does and doesn't promise

One honesty checkpoint before the recap, because "optimal" is a word that invites overconfidence. LQR gives you the gain that minimizes *your* quadratic cost for *your* linear model — nothing more. It does **not** promise the robot will behave the way you intuitively want; it promises it minimizes the cost you wrote, which is only as good as your `Q`/`R` choices. If the closed loop is too aggressive, the gain is still "optimal" — for a cost that apparently valued error-killing over effort more than you meant. The fix is never "the solver is wrong"; it's "my cost didn't express what I wanted," and you re-weight `Q`/`R` and re-solve. This is liberating once it clicks: you debug LQR by debugging the *cost*, which is a small, interpretable object, rather than by fiddling gains you don't understand. And it's why the three sanity checks (Part 1.3) are about *validity* (is this a real, stabilizing solution?) not *desirability* (do I like the behavior?) — validity the solver guarantees, desirability you tune through the cost. Keep that line clear and LQR stops being mysterious: the math is exact, the judgment is yours, and they meet in `Q` and `R`.

## Part 7 — Recap

You should now be able to:

- Solve the continuous (and discrete) algebraic Riccati equation with `scipy` and recover `K = R⁻¹BᵀP`.
- Run the three sanity checks (`P` positive-definite, closed-loop stable, controllable) before trusting any gain.
- Add integral action via state augmentation (LQI) to get zero steady-state error, the LQR analog of PID's I term.
- Gain-schedule by solving LQR at several operating points and interpolating — the principled version of manual scheduling.
- Ship LQR as a `ros2_control` plugin with the same plumbing as the PID, and compare them with a runtime controller swap.
- Explain the LQR/LQE duality and the separation principle, and why they underpin the modular architecture of a robotics autonomy stack.

Next: the exercises put all of this on your robot — build the model, solve for `K`, and race LQR against the PID on a curve. Continue to [the exercises](../exercises/README.md).

One last framing to carry forward: you now own two controllers — PID (tuned by feel, single-loop) and LQR (solved from a model, multivariable, optimal-but-unconstrained). The honest senior position is that LQR does *not* make PID obsolete; it adds a tool for the problems PID can't reach (coupling, optimality), at the cost of needing a model. Many shipped robots use *both* — an LQR or MPC outer loop feeding PID inner loops. The skill this week added isn't "always use LQR"; it's "recognize when the problem is multivariable and constraint-free enough that solving from a model beats tuning by feel," and to reach for the right one. Next week adds the third tool, MPC, for when you also need hard constraints — and the decision flow in §6 is how you choose among all three.

To make the choice concrete, here's the quick triage you'll internalize:

- **One state, weak coupling, no hard limits** → PID. Don't build a model you don't need.
- **Several coupled states, no hard limits** → LQR. The optimal gain handles the coupling for free.
- **Hard constraints (velocity/accel/obstacle) or strong preview needed** → MPC (next week).
- **Need an estimate of unmeasured states** → add a Kalman filter (the dual), feed the estimate to whichever controller; the separation principle says it's allowed.

Most real robots end up with a *mix*: a fast PID inner loop, an LQR or MPC outer loop, and a Kalman filter feeding both. You don't pick one religion; you pick the right tool per loop. The judgment to do that — not the ability to solve a Riccati equation, which is a library call — is what this week actually taught.

The throughline across the three controls weeks, stated once: **PID puts your decisions in the gains, LQR puts them in the cost, MPC puts them in the cost and the constraints.** Each step moves the engineering judgment to a higher, more declarative place and lets a more capable solver do more of the work — at a rising cost in model dependence and compute. That progression — from tuning numbers, to designing a cost, to specifying a constrained optimization — is the arc of modern control, and you've now walked two-thirds of it. The third step, next week, is the one the warehouse robots run.

---

## References

- *Feedback Systems* (Åström & Murray), Optimization-Based Control notes — LQR, Riccati, LQG: <https://fbswiki.org/wiki/index.php/Main_Page>
- *Underactuated Robotics* (Tedrake) — LQR, finite-horizon LQR (the MPC bridge): <https://underactuated.mit.edu/lqr.html>
- `scipy.linalg.solve_continuous_are` / `solve_discrete_are`: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_continuous_are.html>
- `python-control` `lqr` (the cross-check): <https://python-control.readthedocs.io/en/latest/generated/control.lqr.html>
- Steve Brunton — LQR and LQG/Kalman duality episodes: <https://www.youtube.com/@Eigensteve>
- `ros2_control` — writing a new controller: <https://control.ros.org/jazzy/doc/ros2_controllers/doc/writing_new_controller.html>
