# Week 21 — Resources

Every resource here is **free** or has a free, legal full-text version. The optimal-control references we lean on (Åström & Murray's *Feedback Systems*, Hespanha's lecture notes, Bertsekas's DP notes) are author-hosted PDFs. The `scipy` and `python-control` docs are open. No paywalled books are linked; where a famous text is canonical, we point at the free author PDF.

When a link is versioned, the Jazzy URL is given. The LQR math is software- and distro-independent; only the `ros2_control` API URLs move.

## Required reading (work it into your week)

- **Åström & Murray, *Feedback Systems* (2nd ed.) — Chapters 6–8 (state-space, linear systems) and the optimal-control supplement (`obc` notes).** The cleanest free treatment of state-space, controllability, and LQR. Read Ch. 6–7 Monday, the LQR material Tuesday:
  <https://fbswiki.org/wiki/index.php/Main_Page> (full PDF on the front page; the Optimization-Based Control notes cover LQR)
- **Steve Brunton — Control Bootcamp, the LQR lectures.** The single best free video build-up: state-space → controllability → LQR → Kalman duality, in order, with intuition. Watch the LQR and "LQR control" episodes this week:
  <https://www.youtube.com/playlist?list=PLMrJAkhIeNNR20Mz-VpzgfQs5zrYi085m>
- **`scipy.linalg.solve_continuous_are` / `solve_discrete_are`** — the Riccati solvers you call. Read the docstrings and the return-value notes:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_continuous_are.html>
- **`python-control` — `lqr`, `ctrb`, `obsv`, `ss`.** The library you cross-check against. Read the LQR and state-space pages:
  <https://python-control.readthedocs.io/en/latest/control.html>

## The optimal-control references (skim the relevant sections)

- **João Hespanha — *Linear Systems Theory* lecture notes (UCSB).** Free, rigorous, and exactly the controllability/observability and LQR derivations you want when the intuition isn't enough:
  <https://web.ece.ucsb.edu/~hespanha/linearsystems/>
- **Dimitri Bertsekas — *Dynamic Programming and Optimal Control* lecture slides (MIT, free).** LQR is the canonical DP example; the slides show where the Riccati recursion comes from:
  <https://web.mit.edu/dimitrib/www/dpchapter.html>
- **Underactuated Robotics (Russ Tedrake, MIT, free online book) — the LQR chapter.** LQR for robots specifically, including the linearize-and-LQR pattern and finite-horizon LQR (the bridge to MPC):
  <https://underactuated.mit.edu/lqr.html>

## State-space and Riccati API (open all week)

- **`numpy.linalg`** — `eig` (closed-loop eigenvalues), `matrix_rank` (controllability test), `inv`, `solve`:
  <https://numpy.org/doc/stable/reference/routines.linalg.html>
- **`scipy.linalg`** — `solve_continuous_are`, `solve_discrete_are`, `expm` (matrix exponential for discretization):
  <https://docs.scipy.org/doc/scipy/reference/linalg.html>
- **`control.matlab`** — if you prefer the MATLAB-style API (`lqr`, `care`, `lsim`) as a cross-check:
  <https://python-control.readthedocs.io/en/latest/matlab.html>

## `ros2_control` (carried over from Week 20)

- **`ros2_control` — writing a new controller.** The plugin lifecycle your `LqrPathController` implements (same as last week's PID):
  <https://control.ros.org/jazzy/doc/ros2_controllers/doc/writing_new_controller.html>
- **`ros2 control` CLI** — `load_controller`, `set_controller_state`, `list_controllers`. How you *swap* between the PID and the LQR at runtime:
  <https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html>
- **Your Week 20 `crunchbot_control` package** — the LQR controller drops in beside the PID. Reuse the param surface and the launch files.

## LQR in real robotics (read controllers that ship it)

- **Cart-pole / inverted-pendulum LQR** — the canonical worked example, everywhere. Underactuated Robotics has the cleanest derivation; replicate it before you trust your diff-drive LQR:
  <https://underactuated.mit.edu/acrobot.html>
- **Quadrotor LQR / cascaded control** — LQR is the inner attitude/position controller on many research drones. PX4's controllers are PID-cascaded, but the LQR formulations in the literature use the exact `A`/`B`/`Q`/`R` workflow you learn here:
  <https://github.com/PX4/PX4-Autopilot>
- **`robot_localization`'s EKF** — the Kalman side of the LQR/LQE duality, running in your own stack since Week 10. Re-read its covariance handling with the duality in mind:
  <https://github.com/cra-ros-pkg/robot_localization>

## Tuning and design references

- **Bryson's rule for `Q`/`R`** — the units-aware starting point (`Q_ii = 1/x_i,max²`, `R_jj = 1/u_j,max²`). Summarized in Bryson & Ho, *Applied Optimal Control*; the rule itself is one line and appears in every LQR tutorial:
  <https://underactuated.mit.edu/lqr.html> (the cost-design discussion)
- **`scipy.signal.cont2discrete`** — converting your continuous `A`/`B` to discrete for the discrete-time LQR and for simulation:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.cont2discrete.html>

## Talks worth your time (free, no signup)

- **Steve Brunton — "LQR control" and "Linear Quadratic Gaussian (LQG)".** The duality and the separation principle, made visual:
  <https://www.youtube.com/@Eigensteve>
- **Brian Douglas — state-space and LQR videos.** The gentler on-ramp if the matrices feel abstract:
  <https://www.youtube.com/@ControlSystemLectures>

## Tools you'll use this week

- **`scipy`** — `sudo apt install python3-scipy`. The Riccati solvers and discretization.
- **`python-control`** — `pip install control`. The cross-check library and a faster path to `lqr`/`ctrb`/`obsv`.
- **`numpy` + `matplotlib`** — the model, the simulation, the eigenvalue plots.
- **PlotJuggler** — `sudo apt install ros-jazzy-plotjuggler-ros`. Live-plot cross-track error and heading error during the LQR-vs-PID comparison on the robot.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **State** `x` | The minimal set of variables that fully describes the system now (for diff-drive tracking: cross-track error, heading error, etc.). |
| **State-space** `ẋ = Ax + Bu` | The model: how the state evolves (`A`) and how your command pushes it (`B`). |
| **`A` (system matrix)** | How the state evolves on its own, with no input. |
| **`B` (input matrix)** | How the control input enters the state dynamics. |
| **Linearization** | Approximating a nonlinear model by its Jacobian at an operating point, giving a local `A`/`B`. |
| **Controllability** | Whether you can steer the state anywhere you want with the available inputs. Tested by the rank of `[B AB A²B …]`. |
| **Observability** | Whether you can reconstruct the full state from the measured outputs. The dual of controllability. |
| **LQR cost** `J = ∫(xᵀQx + uᵀRu)` | The thing you minimize: state error weighted by `Q`, control effort weighted by `R`. |
| **`Q`** | State-error penalty. Bigger `Q` → care more about accuracy → more aggressive. |
| **`R`** | Control-effort penalty. Bigger `R` → care more about gentle actuation → less aggressive. |
| **Riccati equation** | The matrix equation whose solution `P` yields the optimal gain. Solved numerically, never by hand. |
| **`P`** | The symmetric positive-definite solution of the Riccati equation. |
| **`K = R⁻¹BᵀP`** | The optimal feedback gain. The control law is `u = −K(x − x_ref)`. |
| **Bryson's rule** | `Q_ii = 1/x_i,max²`, `R_jj = 1/u_j,max²` — a principled, units-aware first guess for the cost matrices. |
| **LQI** | LQR with the state augmented by the integral of error, for zero steady-state error (the LQR analog of PID's I term). |
| **Gain scheduling** | Solving LQR at several operating points and interpolating the gains at runtime. |
| **LQE / Kalman** | The optimal *estimator* — LQR's mathematical dual, same Riccati machinery on `(Aᵀ, Cᵀ)`. |
| **Separation principle** | You can design the optimal estimator and the optimal controller independently and combine them. |

---

*If a link 404s, please open an issue so we can replace it.*
