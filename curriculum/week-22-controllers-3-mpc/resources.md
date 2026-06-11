# Week 22 — Resources

Every resource here is **free** or has a free, legal full-text version. The MPC references we lean on (Rawlings, Mayne & Diehl's *Model Predictive Control: Theory, Computation, and Design*, Borrelli/Bemporad/Morari) are author-hosted PDFs. The `cvxpy`, OSQP, and `acados` docs are open. No paywalled books are linked.

When a link is versioned, the Jazzy URL is given. The MPC math and the solver APIs are distro-independent; only the `ros2_control` URLs move.

## Required reading (work it into your week)

- **Rawlings, Mayne & Diehl, *Model Predictive Control: Theory, Computation, and Design* (2nd ed.) — the free PDF.** The canonical MPC text. Read Ch. 1 (the receding-horizon idea) and Ch. 2 (the QP formulation, constraints) this week; Ch. 2's feasibility and stability material is the failure-modes lecture:
  <https://sites.engineering.ucsb.edu/~jbraw/mpc/> (full PDF, author-hosted)
- **`cvxpy` — the official tutorial and the "Control" example.** The modeling syntax you'll use for every QP this week, and a worked MPC example to start from:
  <https://www.cvxpy.org/examples/basic/index.html> and <https://www.cvxpy.org/tutorial/index.html>
- **OSQP — the documentation.** The operator-splitting QP solver `cvxpy` calls under the hood and that `acados` can use; understand its warm-starting and its status codes:
  <https://osqp.org/docs/>
- **Steve Brunton — MPC lectures.** The cleanest free video build-up of receding horizon and the LQR→MPC connection. Watch the MPC episodes this week:
  <https://www.youtube.com/@Eigensteve>

## The MPC references (skim the relevant chapters)

- **Borrelli, Bemporad & Morari, *Predictive Control for Linear and Hybrid Systems* (free PDF).** The QP formulation, explicit MPC, and feasibility/stability theory, rigorously:
  <https://www.mpc.berkeley.edu/mpc-course-material>
- **`do-mpc` documentation.** The Python MPC framework the syllabus names; a higher-level alternative to hand-rolling the QP, with nonlinear MPC support:
  <https://www.do-mpc.com/en/latest/>
- **`acados` documentation.** The real-time codegen MPC framework that warehouse AMRs and drones ship. This is the "deploy MPC" tool; read the Python interface and the SQP_RTI explanation:
  <https://docs.acados.org/>
- **MPC for autonomous driving (the kinematic-bicycle tracker).** The standard reference formulation you implement this week, written up in many free course notes; the F1TENTH MPC materials are an excellent, runnable example:
  <https://f1tenth.org/learn.html>

## Solver and modeling API (open all week)

- **`cvxpy` API reference** — `Variable`, `Parameter`, `Minimize`, `Problem`, `quad_form`, and the `.solve(solver=cp.OSQP, warm_start=True)` options:
  <https://www.cvxpy.org/api_reference/cvxpy.html>
- **OSQP Python interface** — if you drop below `cvxpy` to call OSQP directly for speed:
  <https://osqp.org/docs/interfaces/python.html>
- **`scipy.signal.cont2discrete`** — discretizing your continuous bicycle/double-integrator model for the prediction step:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.cont2discrete.html>
- **`numpy` + `matplotlib`** — the model, the simulation, the tracking and latency plots.

## `ros2_control` (carried over from Weeks 20–21)

- **`ros2_control` — writing a new controller.** The plugin lifecycle your `MpcPathController` implements:
  <https://control.ros.org/jazzy/doc/ros2_controllers/doc/writing_new_controller.html>
- **Your Weeks 20–21 `crunchbot_control` package** — the MPC drops in beside the PID and LQR; reuse the param surface, the launch files, and the benchmark harness.
- **Nav2 MPPI controller** — Nav2 ships a sampling-based MPC-family controller (MPPI). Read it to see a real, deployed predictive controller in the navigation stack and contrast it with the QP-MPC you build:
  <https://docs.nav2.org/configuration/packages/configuring-mppic.html>

## MPC in real robotics (read controllers that ship it)

- **Nav2 MPPI** — the production predictive controller in the most-used mobile-robot navigation stack:
  <https://github.com/ros-navigation/navigation2/tree/main/nav2_mppi_controller>
- **`acados` examples — the racecar / bicycle MPC** — a runnable, profiled, real-time bicycle MPC, exactly this week's plant at deployment quality:
  <https://github.com/acados/acados/tree/master/examples>
- **F1TENTH MPC** — a complete, open, runnable MPC for a real (small) car; the kinematic-bicycle MPC at racing speeds with hard limits:
  <https://github.com/f1tenth/f1tenth_labs>

## Latency and deployment references

- **The OSQP paper (Stellato et al., 2020)** — why operator-splitting and warm-starting make successive MPC solves cheap; the basis for real-time QP-MPC:
  <https://osqp.org/citing/>
- **`acados` real-time iteration (RTI) scheme** — the trick that makes nonlinear MPC real-time: do one SQP iteration per control step instead of solving to convergence:
  <https://docs.acados.org/python_interface/index.html>

## Talks worth your time (free, no signup)

- **Steve Brunton — "Model Predictive Control".** Receding horizon and constraints, made visual:
  <https://www.youtube.com/@Eigensteve>
- **ROSCon Nav2 / control talks** — the OSRF posts every talk free; the Nav2 controller and the predictive-control sessions are the ones to watch:
  <https://roscon.ros.org/> and <https://vimeo.com/osrfoundation>

## Tools you'll use this week

- **`cvxpy`** — `pip install cvxpy`. Ships OSQP and ECOS. The pedagogical QP modeler for all graded work.
- **OSQP** — installed with `cvxpy`; the QP solver it calls. You'll read its status codes and warm-start flag.
- **`acados`** (stretch) — `pip install acados_template` plus the source build; the real-time deployment framework.
- **`do-mpc`** (alternative) — `pip install do-mpc`; the higher-level Python MPC framework the syllabus names.
- **`time.perf_counter` / `cProfile`** — your latency profilers. The solve-time measurement is a deliverable, not an afterthought.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **MPC** | Model Predictive Control — optimize an input sequence over a horizon, apply the first input, re-solve next step. |
| **Receding horizon** | The "predict N steps, apply one, re-plan" loop that gives MPC its feedback. |
| **Prediction horizon** `N` | How many steps ahead the MPC predicts and optimizes. |
| **Decision variables** | The predicted states and inputs over the horizon that the solver chooses. |
| **Equality constraints** | The dynamics `x_{k+1} = Ax_k + Bu_k` linking consecutive predicted states. |
| **Inequality constraints** | The hard bounds: `v_min ≤ v ≤ v_max`, rate limits, obstacle half-planes. |
| **QP (quadratic program)** | Minimize a quadratic objective subject to linear constraints. Convex; solved fast and reliably. |
| **Terminal cost** | A cost on the final predicted state (often the LQR `P`) that stands in for the infinite tail beyond the horizon. |
| **Terminal set** | A constraint that the final state lands in a known-safe region — gives recursive feasibility. |
| **Recursive feasibility** | The guarantee that if the MPC is feasible now, it stays feasible next step (it can't paint itself into a corner). |
| **Infeasible** | The solver's report that no input sequence satisfies all the constraints. A failure mode to detect and recover from. |
| **Warm-starting** | Seeding the solver with last step's solution (shifted), so it converges in far fewer iterations. |
| **Soft constraint** | A constraint relaxed with a slack variable + penalty, so the QP stays feasible when the hard version is momentarily impossible. |
| **`cvxpy`** | The Python convex-optimization modeling language — readable, pedagogical, too slow for tight real-time. |
| **OSQP** | The operator-splitting QP solver `cvxpy` calls; fast, warm-startable, embeddable. |
| **`acados`** | The codegen real-time MPC framework that deployed robots ship; the SQP_RTI scheme makes it real-time. |
| **Latency budget** | The control period the solve must fit inside. p95 solve time over budget = not a controller. |

---

*If a link 404s, please open an issue so we can replace it.*
