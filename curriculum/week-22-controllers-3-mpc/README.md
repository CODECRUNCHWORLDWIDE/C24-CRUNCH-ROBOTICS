# Week 22 — Controllers Part 3: MPC

Two weeks ago you tuned a PID by feel. Last week you solved an LQR from a model and a cost. Both have a fatal blind spot: **neither can respect a hard constraint.** PID will happily command 5 m/s when your base maxes at 1.5. LQR's quadratic cost has no notion of "the wall is here, do not steer into it" — it will compute an optimal-on-paper trajectory that drives straight through an obstacle, because nothing in the cost says it can't. Real robots live and die by constraints: velocity limits, acceleration limits, steering-rate limits, the workspace boundary, the obstacle in the corridor. This week you build the controller that respects them *exactly*, by re-solving a constrained optimization problem every single control step. That's **Model Predictive Control** — MPC, the controller that ships in every warehouse AMR and most self-driving stacks because it's the one that obeys the laws of physics you actually have to obey.

By Friday you will be able to set up an MPC as a quadratic program: a model that predicts the next `N` steps, a cost over that horizon, and hard constraints on states and inputs. You will solve it with `cvxpy` (clean and pedagogical) and understand the path to `acados`/OSQP (fast and deployable), implement a kinematic-bicycle MPC that tracks a figure-8 with hard velocity and steering-rate limits, compare it to the LQR you built last week, and — the part that separates a demo from a deployment — *profile the solve time* and design around the latency budget, because an MPC that takes 80 ms to solve a 20 ms control loop is not a controller, it's a liability.

We assume you finished Week 21 and have the `crunchbot_control` package hosting both a PID and an LQR controller, and that your **week-3 differential-drive robot** still spawns in Gz Sim and tracks `/cmd_vel`. The MPC drops into that same package. If anything is broken, fix it first.

The one thing to internalize before you read another line: **MPC is LQR's optimal-control mindset plus two upgrades — a *finite* horizon re-solved every step (so it can react to a changing reference and re-plan), and *explicit hard constraints* (so it never commands the impossible). The price is compute: instead of solving one Riccati equation offline, you solve a quadratic program online, every tick, in real time.** That price is the entire engineering challenge of MPC. The theory is "LQR but constrained and re-solved"; the craft is making the solve fit in your control period on the hardware you actually have. Get the theory in the lectures; respect the latency in the lab.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** the receding-horizon principle: predict `N` steps ahead, optimize the whole input sequence, apply only the first input, then re-solve next step with fresh state.
- **Formulate** an MPC problem as a quadratic program (QP): the prediction model as equality constraints, the input/state bounds as inequality constraints, and the tracking-plus-effort objective as a quadratic cost.
- **Solve** an MPC with `cvxpy` — building the decision variables, constraints, and objective declaratively — and read the solver's status to know whether your QP was feasible.
- **Handle real constraints**: velocity and acceleration limits, steering-rate limits, and (linearized) obstacle-avoidance constraints, and explain why a hard constraint is fundamentally different from a large penalty in the cost.
- **Implement** a kinematic-bicycle MPC for path tracking, the standard model for Ackermann-like and car-like vehicles, and tune its horizon length and cost weights.
- **Compare** MPC to LQR on the same trajectory, and articulate exactly what MPC buys (constraint satisfaction, preview/look-ahead) and what it costs (compute, complexity, tuning surface).
- **Profile and budget latency**: measure the QP solve time, understand how horizon length and constraint count drive it, and design the control architecture (solve rate, warm-starting, the move to `acados`/OSQP) around a real latency budget on Orin-class hardware.
- **Diagnose MPC failure modes**: infeasibility (the constraints can't all be satisfied), solver timeout, terminal-cost/terminal-set issues, and the recursive-feasibility question that keeps an MPC from painting itself into a corner.
- **Ship** an MPC as a `ros2_control`-integrated controller (often as an outer loop generating a reference for an inner tracking controller), reusing the framework from the last two weeks.

## Prerequisites

This week assumes you have completed **C24 weeks 1–21**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**. Your `crunchbot_control` package builds and hosts the PID and LQR controllers.
- You are fluent in the **LQR material from Week 21** — state-space models, quadratic costs, the optimal-control mindset. MPC is the constrained, finite-horizon extension of exactly that.
- You can do **linear algebra and read an optimization problem** — "minimize this quadratic subject to these linear constraints." We build the QP up from scratch and introduce `cvxpy`'s modeling syntax inline, but you must not be afraid of `minimize ... subject to ...`.
- `numpy`, `scipy`, `matplotlib`, and **`cvxpy`** installed (`pip install cvxpy`). `cvxpy` ships with the OSQP and ECOS solvers; we use OSQP for the QPs. We *discuss* `acados` and `do-mpc` and point at their install docs, but the graded work uses `cvxpy` so nobody is blocked on a heavy toolchain.
- You remember the **kinematic models from Week 6** (unicycle, bicycle) — the bicycle model is the MPC plant this week.

You do **not** need a prior optimization or optimal-control course. We build the receding-horizon idea, the QP formulation, and constraint handling from "what is a horizon" up to "here is a profiled, constraint-respecting MPC," connecting every piece to runnable `cvxpy`. If you've heard "MPC" as the controller self-driving companies brag about but never set one up, this is the week it becomes a tool you can profile and ship.

## Topics covered

- **The receding-horizon principle.** Predict the next `N` steps with a model, optimize the whole input sequence `u₀…u_{N−1}` to minimize a cost over the horizon, apply *only* `u₀`, discard the rest, advance one step, and re-solve with the new measured state. Why "apply one, re-plan" gives feedback and robustness that open-loop trajectory optimization lacks.
- **MPC as a quadratic program.** The decision variables (the predicted states and inputs over the horizon), the *equality* constraints (the dynamics `x_{k+1} = Ax_k + Bu_k` linking consecutive states), the *inequality* constraints (state and input bounds), and the quadratic objective (`Σ xₖᵀQxₖ + uₖᵀRuₖ` plus a terminal term). Why this is a convex QP when the model is linear and the constraints are linear.
- **Solving with `cvxpy`.** Declaring variables, expressing constraints as a Python list, building the objective, calling `prob.solve()`, and reading `prob.status` (`optimal`, `infeasible`, `unbounded`). The OSQP solver under the hood. Warm-starting between solves.
- **Constraint handling — the whole point.** Hard input bounds (`v_min ≤ v ≤ v_max`), rate bounds (`|u_{k+1} − u_k| ≤ Δu_max` for acceleration/steering-rate limits), state bounds, and obstacle avoidance as a (linearized) half-plane or a sequence of them. Why a *hard* constraint is categorically different from a *soft* penalty — and when to deliberately soften a constraint (slack variables) to keep the QP feasible.
- **The kinematic-bicycle MPC.** The bicycle model (`ẋ = v·cosθ`, `ẏ = v·sinθ`, `θ̇ = v·tanδ/L`), its linearization for the QP, path-tracking with a reference trajectory and look-ahead, and tuning the horizon `N`, the discretization `dt`, and the `Q`/`R`/terminal weights.
- **MPC vs. LQR.** What MPC adds (exact constraint satisfaction, preview of the upcoming reference) and what it costs (an online solve every step vs. a precomputed gain). The unconstrained-MPC-equals-LQR fact (with a long enough horizon and the LQR terminal cost), which is the conceptual bridge and a sanity check.
- **Latency and deployment.** Profiling the solve time; how `N`, the state dimension, and the constraint count drive it; warm-starting to exploit step-to-step similarity; the move from `cvxpy` (pedagogical) to **OSQP** (the embeddable QP solver `cvxpy` calls) and **`acados`** (the codegen real-time framework warehouse AMRs ship). Designing the solve rate and the inner/outer-loop split around an Orin-class latency budget.
- **MPC failure modes.** Infeasibility and how to detect and recover (soften constraints, shrink the horizon, fall back to a safe controller); solver timeout and the hard real-time deadline; terminal cost and terminal set for stability and recursive feasibility; the "MPC drove into a corner it can't get out of" problem and how a terminal set prevents it.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                   | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|---------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Receding horizon; MPC as a QP; the `cvxpy` formulation   |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Constraint handling; the double-integrator MPC exercise  |   1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Kinematic-bicycle MPC; figure-8 tracking; MPC vs LQR     |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Latency profiling; warm-start; acados/OSQP; the budget   |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Failure modes; feasibility & recovery; packaging         |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                  |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, latency-report polish                     |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                         | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The MPC texts, the `cvxpy`/OSQP/`acados` docs, and the talks worth your time |
| [lecture-notes/01-receding-horizon-mpc-as-a-qp-and-constraints.md](./lecture-notes/01-receding-horizon-mpc-as-a-qp-and-constraints.md) | The receding-horizon idea, MPC as a QP, solving with `cvxpy`, and constraint handling |
| [lecture-notes/02-bicycle-mpc-latency-acados-and-failure-modes.md](./lecture-notes/02-bicycle-mpc-latency-acados-and-failure-modes.md) | The kinematic-bicycle MPC, MPC vs LQR, latency profiling, `acados`/OSQP, and failure modes |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-mpc-formulation.md](./exercises/exercise-01-mpc-formulation.md) | Formulate a double-integrator MPC on paper and in `cvxpy`; verify it equals LQR when unconstrained |
| [exercises/exercise-02-constrained-double-integrator-mpc.py](./exercises/exercise-02-constrained-double-integrator-mpc.py) | A constrained double-integrator MPC; add velocity and acceleration limits and watch them bind |
| [exercises/exercise-03-bicycle-mpc-tracking.py](./exercises/exercise-03-bicycle-mpc-tracking.py) | A kinematic-bicycle MPC tracking a figure-8 with hard velocity and steering-rate limits, vs LQR, profiled |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-mpc-with-an-obstacle-and-a-latency-budget.md](./challenges/challenge-01-mpc-with-an-obstacle-and-a-latency-budget.md) | Add obstacle-avoidance constraints and meet a hard per-step latency budget; document the trade-off |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the headline latency-budget writeup |
| [mini-project/README.md](./mini-project/README.md) | The `MpcPathController` with constraints, warm-starting, a latency profiler, and the three-way controller benchmark |

## The "solved, feasible, and in budget" promise

C24 uses a recurring marker for every MPC exercise that ends in a controller you could actually deploy:

```
$ python3 bicycle_mpc.py --profile
horizon N=20, dt=0.05 s, states=4, inputs=2
constraints: |v|<=1.5, |delta|<=0.5, |delta_rate|<=2.0/s
solve status: optimal     (feasible every step over 600 steps)
solve time:   mean 4.1 ms   p95 6.8 ms   max 9.2 ms
control period budget: 20 ms   ->  p95 is 34% of budget   OK
RMS cross-track error: 0.041 m   (vs LQR 0.058 m on the same path)
```

If the solver returns `infeasible` on any step, *stop* — your constraints can't all be satisfied and you must soften one or widen the horizon. If the p95 solve time exceeds your control period, you do not have a controller — you have a plan that arrives too late to use. The point of Week 22 is to make "optimal, feasible, in budget" the three things you check before an MPC goes anywhere near a robot.

## A word on the compute reality

This is the week where the math stops being the hard part and the *engineering* takes over. The MPC formulation is, conceptually, last week's LQR with constraints and a re-solve — a few hours to understand. Making it solve in 5 ms on an Orin Nano while a perception stack eats the rest of the GPU is the real job, and it's why we treat latency as a first-class artifact, not an afterthought. `cvxpy` is perfect for *learning* MPC — it's readable and it forces you to state the problem cleanly — and it is *too slow* for a tight real-time loop, which is exactly why `acados` and OSQP exist. We have you build the readable version, profile it honestly, watch it miss a tight budget, and understand precisely what `acados` does differently. That arc — readable first, then fast, with a profiler in between — is how production MPC actually gets built, and pretending the solve is free is the single most common way a robotics MPC project fails.

## Stretch goals

If you finish the regular work early and want to push further:

- Install **`acados`** (or **`do-mpc`**, which the syllabus names) and reimplement the bicycle MPC with it. Profile the solve time against your `cvxpy` version on the same problem and quantify the speedup. This is the jump from "learning MPC" to "deploying MPC."
- Add a **terminal cost equal to the LQR `P`** (the Riccati solution from Week 21) and a **terminal constraint set**, and explain how they give the MPC stability guarantees and recursive feasibility — the rigorous version of "don't paint yourself into a corner."
- Implement **soft constraints with slack variables** and an L1 penalty, so the MPC degrades gracefully (and stays feasible) when a hard constraint is momentarily impossible, instead of returning `infeasible` and leaving you with no command.
- Read the **OSQP paper** (the operator-splitting QP solver `cvxpy` calls and `acados` can use) until you understand why warm-starting makes successive MPC solves so cheap: <https://osqp.org/>.

## Up next

This is the last controls week of Phase 3. Week 23 changes subject entirely to **manipulator kinematics and MoveIt2** — forward and inverse kinematics of a 6-DOF arm, the Jacobian, singularities, and the `move_group` planning interface. But the controller stays with you: the arm runs under a `joint_trajectory_controller`, and the MPC mindset (predict, optimize under constraints, re-plan) reappears the moment you care about respecting joint limits and avoiding self-collision while moving. Push your mini-project, and make sure all three controllers — PID, LQR, MPC — live in `crunchbot_control` for the Phase 3 milestone in Week 24, where you defend the whole stack and the choice between its controllers.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
