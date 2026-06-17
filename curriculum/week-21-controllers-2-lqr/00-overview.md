# Week 21 — Controllers Part 2: LQR

Last week you tuned a PID by feel. You poked `Kp` until it oscillated, backed off, added `Kd` for damping, added a little `Ki`. It worked, and it will keep working for single-loop problems forever. But the moment you have **more than one state to control at once** — a diff-drive base where cross-track error *and* heading error *and* velocity all couple together — tuning by feel falls apart. You'd be hand-tuning a 2×4 matrix of gains by watching plots, and there are too many knobs and too much coupling. This week you stop guessing. You write down a *model* of the robot, a *cost* that says how much you care about each error and how much you care about effort, and you let a solver hand you the **optimal** feedback gain matrix. That's LQR — the Linear Quadratic Regulator.

By Friday you will be able to write a robot's dynamics in state-space form, check whether it's even *controllable*, build the `Q` and `R` cost matrices that encode your engineering priorities, solve the algebraic Riccati equation with `scipy.linalg.solve_continuous_are` to get the optimal gain `K`, and ship the resulting controller against the same `ros2_control` plumbing you built last week — then put it head-to-head with the PID on a curved trajectory and measure who tracks better. You will also understand the duality that makes LQR and the Kalman filter the *same math* run forwards and backwards, which is the conceptual key to the whole estimation-and-control half of robotics.

We assume you finished Week 20 and have the `crunchbot_control` package with a working PID `ros2_control` plugin, and that your **week-3 differential-drive robot** still spawns in Gz Sim and tracks `/cmd_vel`. The LQR controller this week drops into that same package. If either is broken, fix it first.

The one thing to internalize before you read another line: **LQR is PID with adult supervision. When your system is linear and your cost is quadratic, LQR gives you the provably optimal feedback law — not a good one, the optimal one — in one solve, with no manual tuning of the gains themselves.** You still make engineering choices, but you make them where they belong: in the *cost* (how much do I care about cross-track error versus control effort?), not in the *gains*. The solver translates your cost into gains. That separation — design intent in the cost, mechanics in the solver — is the entire reason LQR scales to problems PID can't touch, and it's the same separation MPC will extend next week by adding constraints.

## Learning objectives

By the end of this week, you will be able to:

- **Write** a robot's dynamics in continuous-time state-space form `ẋ = Ax + Bu`, and explain what the `A` and `B` matrices physically mean.
- **Linearize** a nonlinear robot model (the diff-drive kinematics) around an operating point to get a local `A`/`B`, and state honestly where that linearization is valid and where it breaks.
- **Check controllability** with the controllability matrix (and the discrete-time and Gramian variants), and explain what an uncontrollable mode means for whether LQR can even help you.
- **Formulate** the LQR cost `J = ∫(xᵀQx + uᵀRu) dt` and design `Q` and `R` to encode engineering priorities — including Bryson's rule as a principled starting point instead of random matrices.
- **Solve** the continuous and discrete algebraic Riccati equations numerically (`scipy.linalg.solve_continuous_are` / `solve_discrete_are`) and recover the optimal gain `K = R⁻¹BᵀP`.
- **Implement** the LQR control law `u = −K·(x − x_ref)` as a `ros2_control` controller, with the integral-augmentation trick that gives LQR the zero-steady-state-error property PID gets from its I term.
- **Compare** LQR against PID on a path-tracking task and quantify the difference in cross-track error, heading error, and control effort.
- **Apply gain scheduling**: solve LQR at several operating points and interpolate, so a single controller works across the robot's speed range — the principled version of last week's manual gain scheduling.
- **Explain the LQR/LQE (Kalman) duality**: why the optimal estimator is the optimal controller's transpose, and what that means for the separation principle that lets you design them independently.

## Prerequisites

This week assumes you have completed **C24 weeks 1–20**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**. Your Week 20 `crunchbot_control` package builds and its PID controller loads under the `controller_manager`.
- You are comfortable with the **PID, feedforward, and `ros2_control`** material from Week 20 — this week extends that exact framework.
- You can do **basic linear algebra**: matrix multiplication, transpose, inverse, eigenvalues. We use `numpy` and `scipy.linalg` for all of it and introduce the controls-specific operations (Riccati, controllability) inline, but you must not be afraid of a matrix.
- You remember the **diff-drive kinematics** from Week 6 (forward kinematics, the unicycle model) — that's the model we linearize and control.
- `numpy`, `scipy`, and `matplotlib` installed. We also use the **`python-control`** library (`pip install control`) as a cross-check against the hand-rolled `scipy.linalg` solves.

You do **not** need a prior controls course or any optimal-control theory. We build state-space, controllability, and the Riccati equation from "what is a state" up to "here is the optimal gain," connecting every matrix to a line of code. If you've heard "LQR" as a buzzword but never solved one, this is the week it becomes a tool in your hands.

## Topics covered

- **State-space form.** `ẋ = Ax + Bu`, `y = Cx + Du`. What the state vector *is* for a robot, what `A` (the system matrix, how the state evolves on its own) and `B` (the input matrix, how your command pushes it) encode. Continuous vs. discrete-time state-space and how to convert.
- **Linearization.** Taking the nonlinear diff-drive model (`ẋ = v·cosθ`, `ẏ = v·sinθ`, `θ̇ = ω`), computing the Jacobians `A = ∂f/∂x`, `B = ∂f/∂u` at an operating point (e.g. `v = 0.5 m/s`, `θ = 0`), and the error-dynamics formulation that turns path tracking into a regulation problem LQR can solve.
- **Controllability and observability.** The controllability matrix `𝒞 = [B, AB, A²B, …]` and its rank test; what an uncontrollable mode is and why LQR can't fix one; observability as the dual (can you *see* every state from the outputs?); the Gramians as the quantitative versions.
- **The LQR cost function.** `J = ∫₀^∞ (xᵀQx + uᵀRu) dt`. `Q` penalizes state error (how much you care about each state being off), `R` penalizes control effort (how much you care about working the actuator). The fundamental error-vs-effort trade-off, and why scaling `Q` up or `R` down both make the controller more aggressive.
- **The algebraic Riccati equation.** Where the optimal gain comes from: solve `AᵀP + PA − PBR⁻¹BᵀP + Q = 0` for the symmetric positive-definite `P`, then `K = R⁻¹BᵀP`. Why you never solve this by hand and always call `solve_continuous_are`. The discrete-time analog and when you need it.
- **Designing `Q` and `R`.** Bryson's rule (`Q_ii = 1/max_acceptable_xᵢ²`, `R_jj = 1/max_acceptable_uⱼ²`) as a principled, units-aware starting point. Diagonal vs. full matrices. The iterate-on-the-cost workflow that replaces iterate-on-the-gains.
- **Integral action and reference tracking.** Pure LQR is a *regulator* (drives state to zero) and leaves steady-state error against a disturbance, exactly like P-only PID. Augmenting the state with the integral of the tracking error (the LQI controller) to recover zero steady-state error — the LQR analog of PID's I term.
- **Gain scheduling.** The linearization is only valid near its operating point. Solve LQR at several operating points (several speeds), store the gains, and interpolate at runtime — a single scheduled controller that's optimal-ish across the whole envelope.
- **The LQR/LQE duality.** The Kalman filter (LQE — Linear Quadratic Estimator) is LQR's mathematical dual: the same Riccati machinery, run on `(Aᵀ, Cᵀ)` instead of `(A, B)`. The separation principle: you can design the optimal estimator and the optimal controller independently and bolt them together. Why this is the load-bearing idea under most of modern robotics.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | State-space; linearization; controllability            |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The LQR cost; Riccati; solving for K; Q/R design        |   1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Integral action; reference tracking; gain scheduling   |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | LQR as a `ros2_control` plugin; LQR vs PID on a curve   |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | The LQR/LQE duality; tuning the cost; packaging         |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                 |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, comparison-writeup polish                |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The state-space and optimal-control references, the `scipy`/`control` docs, and the talks worth your time |
| [lecture-notes/01-state-space-controllability-and-the-lqr-cost.md](./02-lecture-notes/01-state-space-controllability-and-the-lqr-cost.md) | State-space, linearization, controllability, and the LQR cost function |
| [lecture-notes/02-riccati-integral-action-scheduling-and-duality.md](./02-lecture-notes/02-riccati-integral-action-scheduling-and-duality.md) | Solving the Riccati equation, integral action, gain scheduling, `ros2_control` integration, and the LQR/LQE duality |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-controllability-and-qr-design.md](./03-exercises/exercise-01-controllability-and-qr-design.md) | Build the diff-drive `A`/`B`, check controllability, and design `Q`/`R` with Bryson's rule |
| [exercises/exercise-02-solve-and-simulate-lqr.py](./03-exercises/exercise-02-solve-and-simulate-lqr.py) | Solve the Riccati equation, recover `K`, and simulate the closed loop; cross-check against `python-control` |
| [exercises/exercise-03-lqr-vs-pid-tracking.py](./03-exercises/exercise-03-lqr-vs-pid-tracking.py) | An LQR path-tracking controller vs. the Week-20 PID on a curved trajectory, with quantified error |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-beat-pid-on-a-curve.md](./04-challenges/challenge-01-beat-pid-on-a-curve.md) | Design an LQR (with integral action and gain scheduling) that beats your tuned PID on a figure-8, and defend the cost |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the headline LQR-vs-PID comparison writeup |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `LqrPathController` `ros2_control` plugin with integral action, gain scheduling, and a head-to-head harness |

## The "K came out of the solver" promise

C24 uses a recurring marker for every LQR exercise that ends in a gain matrix you actually trust:

```
$ python3 solve_lqr.py
A (3x3), B (3x2) at operating point v=0.5, theta=0.0
controllability matrix rank: 3  (== n, fully controllable)  OK
solved continuous ARE; P is symmetric positive-definite        OK
optimal gain K =
 [[ 0.000  0.000  3.162]
  [ 1.414  2.236  0.000]]
closed-loop eigenvalues (must all have negative real part):
 [-2.41+1.9j  -2.41-1.9j  -3.16+0.j]   all stable                OK
```

If the controllability rank is less than `n`, *stop* — you cannot LQR your way out of an uncontrollable mode, and the solver will either fail or hand you nonsense. If any closed-loop eigenvalue has a non-negative real part, your `Q`/`R` or your model is wrong. The point of Week 21 is to make those three checks — controllable, `P` positive-definite, closed loop stable — a reflex you run before you ever put `K` on a robot.

## A word on the math

This is the most matrix-heavy week of the track, and it is genuinely where a self-taught engineer's controls gap is widest. We close it the same way we closed the calculus gap last week: every equation is wired to runnable `numpy`/`scipy`. When we write the Riccati equation `AᵀP + PA − PBR⁻¹BᵀP + Q = 0`, the next code block is `P = scipy.linalg.solve_continuous_are(A, B, Q, R)` and a check that `P` actually satisfies it. You do not need to derive the Riccati equation from the calculus of variations (we sketch where it comes from, for the curious). You *do* need to be able to build `A`, `B`, `Q`, `R` for your robot, call the solver, and run the three sanity checks. That skill — model, cost, solve, check — is LQR, and it is entirely learnable by running the code and watching the closed-loop eigenvalues move as you change `Q`.

## Stretch goals

If you finish the regular work early and want to push further:

- Solve the **discrete-time** LQR (`solve_discrete_are`) for your controller's actual sample rate and compare the gains to the continuous solution discretized. For fast loops they nearly match; for slow loops the discrete solve is the correct one.
- Implement the **finite-horizon** LQR (the time-varying gain from the differential Riccati equation, solved backwards in time) and watch the gain converge to the infinite-horizon steady-state `K`. This is the conceptual bridge to MPC, which is finite-horizon optimal control re-solved every step.
- Build a **Kalman filter** for your diff-drive state estimate using `solve_continuous_are` on `(Aᵀ, Cᵀ, Q_process, R_measurement)` and confirm by hand that the math is LQR's transpose. Then close the loop: LQR controller on a Kalman-estimated state, demonstrating the separation principle.
- Read the **`python-control` `lqr` source** and confirm it calls the same `solve_continuous_are` you do: <https://python-control.readthedocs.io/>.

## Up next

Week 22 takes everything you built here — the state-space model, the quadratic cost, the optimal-control mindset — and adds the one thing LQR fundamentally *cannot* do: **respect hard constraints**. LQR will happily command 5 m/s when your base maxes at 1.5, or steer through an obstacle, because the quadratic cost has no notion of a hard limit. MPC re-solves a constrained optimization every control step to honor velocity limits, acceleration limits, and obstacle avoidance exactly. The model and cost carry straight over; the solver changes from "Riccati, once" to "quadratic program, every tick." Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
