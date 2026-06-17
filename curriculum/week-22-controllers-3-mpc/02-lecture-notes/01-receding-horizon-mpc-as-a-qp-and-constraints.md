# Lecture 1 — Receding Horizon, MPC as a Quadratic Program, and Constraints

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain the receding-horizon principle, formulate an MPC as a quadratic program (model as equality constraints, bounds as inequality constraints, tracking-plus-effort as the objective), solve it with `cvxpy`, and add the hard constraints that are the entire reason MPC exists.

If you remember one sentence from this entire week, remember this one:

> **MPC is LQR with two upgrades — a finite horizon re-solved every step, and explicit hard constraints — and the price for those upgrades is that you solve an optimization problem online, every control tick, instead of computing one gain offline.**

Last week's LQR gave you the optimal feedback gain for an *unconstrained* linear-quadratic problem, computed once. That gain will cheerfully command 5 m/s when your base maxes at 1.5, or steer through an obstacle, because the quadratic cost has no language for "this is a hard limit you cannot cross." Real robots are *defined* by their limits — max velocity, max acceleration, the workspace wall, the obstacle in the doorway. MPC is the controller that respects them exactly. This lecture builds it from the receding-horizon idea up to a constraint-respecting `cvxpy` solver.

---

## 1. The receding-horizon principle

### 1.1 The core loop

Here is the entire idea of MPC, and it's worth reading slowly:

1. **Predict.** Using a model of the robot, predict how the state will evolve over the next `N` steps (the **prediction horizon**) for any candidate sequence of inputs `u₀, u₁, …, u_{N−1}`.
2. **Optimize.** Find the input sequence that minimizes a cost over that horizon (tracking error plus control effort) *subject to* the model and the constraints.
3. **Apply one.** Take *only* the first input `u₀` and send it to the robot. Throw away `u₁…u_{N−1}`.
4. **Re-solve.** One control step later, measure the new actual state, shift the horizon forward one step, and go back to step 1.

That "optimize a whole plan, but only execute the first move, then re-plan from where you actually are" is the **receding horizon**, and it is what makes MPC a *feedback* controller rather than open-loop trajectory optimization. You re-plan from the *measured* state every step, so disturbances, model error, and a changing reference all get corrected at the re-solve. The plan is always `N` steps long and always starts *now* — the horizon "recedes" in front of the robot like the view from a moving car.

### 1.2 Why apply only the first input?

This trips people up: if you computed an optimal `N`-step plan, why throw away `N−1` steps of it? Because the plan was optimal *given the model and the state at solve time*, and both are slightly wrong. The model is an approximation; the state will be perturbed by the time you'd execute step 5. By re-solving every step from fresh state, you fold the latest reality back into the plan continuously. Executing the whole plan open-loop would let errors accumulate with no correction — exactly the failure mode of "plan once, run blindly." MPC plans far ahead (for foresight) but commits only one step (for feedback). That combination — long preview, short commitment — is the whole trick, and it's why MPC handles a curve or an obstacle the robot is *approaching* gracefully: it sees the upcoming reference and starts reacting before the error exists, the way feedforward did in Week 20 but derived automatically from the horizon.

---

## 2. MPC as a quadratic program

Now we make "optimize the input sequence subject to the model and constraints" precise. When the model is linear and the constraints are linear, the MPC problem is a **convex quadratic program (QP)** — minimize a quadratic objective subject to linear equality and inequality constraints — which is a class of problem that solvers handle fast and reliably. This is the formulation you build in `cvxpy`.

### 2.1 The decision variables

Over a horizon of `N` steps, the things the optimizer gets to choose are the predicted states and inputs:

```
states:  x₀, x₁, x₂, …, x_N        (N+1 state vectors)
inputs:  u₀, u₁, …, u_{N−1}        (N input vectors)
```

`x₀` is pinned to the *measured current state* (it's where you actually are). The rest are free for the solver to pick — subject to the dynamics tying them together.

### 2.2 The equality constraints — the model

Consecutive states aren't independent; they're linked by the dynamics. With a discrete-time linear model `x_{k+1} = A x_k + B u_k`, each step imposes an equality constraint:

```
x₁ = A x₀ + B u₀
x₂ = A x₁ + B u₁
…
x_N = A x_{N−1} + B u_{N−1}
```

plus `x₀ = x_measured`. These `N+1` equality constraints *are* the prediction model — they force the predicted state trajectory to be physically consistent with the chosen inputs. (Use the *discrete-time* `A`/`B` here, from discretizing your continuous model at the control period `dt` — `scipy.signal.cont2discrete` does this.)

### 2.3 The inequality constraints — the limits

This is the part LQR can't express. State and input bounds become linear inequality constraints:

```
u_min ≤ u_k ≤ u_max          for all k        (e.g. |v| ≤ 1.5 m/s)
x_min ≤ x_k ≤ x_max          for all k        (e.g. stay in the workspace)
|u_{k+1} − u_k| ≤ Δu_max     for all k        (rate limits: acceleration, steering rate)
```

Every one of these is a *hard* constraint — the solver will not return a solution that violates it. That's the categorical difference from a cost penalty (§4): a penalty *discourages*, a constraint *forbids*.

### 2.4 The objective — tracking plus effort

The cost to minimize, summed over the horizon, is the same quadratic shape as LQR's cost, made discrete and finite:

```
        N−1
J  =    Σ   [ (x_k − x_ref,k)ᵀ Q (x_k − x_ref,k)  +  u_kᵀ R u_k ]   +   (x_N − x_ref,N)ᵀ P (x_N − x_ref,N)
        k=0
            └──────── stage cost (track + effort) ────────┘            └──── terminal cost ────┘
```

`Q` penalizes tracking error at each step, `R` penalizes effort, exactly as in LQR. The new piece is the **terminal cost** `P` on the final state — it stands in for "the infinite cost tail beyond the horizon that we cut off at step `N`." Choosing `P` to be the LQR Riccati solution (last week's `P`!) makes the finite-horizon MPC behave like the infinite-horizon LQR in the unconstrained interior — a beautiful connection we exploit in §5.

### 2.5 The whole QP, assembled

Putting it together, the MPC solves, every control step:

```
minimize   Σ (x_k−x_ref)ᵀQ(x_k−x_ref) + u_kᵀRu_k  +  terminal
over       x₀…x_N, u₀…u_{N−1}
subject to x₀ = x_measured                          (current state)
           x_{k+1} = A x_k + B u_k                  (dynamics)
           u_min ≤ u_k ≤ u_max                      (input bounds)
           x_min ≤ x_k ≤ x_max                      (state bounds)
           |u_{k+1} − u_k| ≤ Δu_max                 (rate bounds)
```

Solve it, take `u₀`, apply it, advance, re-solve. That's MPC.

---

## 3. Solving it with `cvxpy`

`cvxpy` lets you write that QP almost verbatim. It's the perfect *learning* tool — readable, declarative, and it forces you to state the problem cleanly — and it's deliberately what we use for graded work this week (the speed concerns of §Lecture 2 come later). Here is a complete, minimal MPC for a double integrator (`position`/`velocity` state, `acceleration` input):

```python
import numpy as np
import cvxpy as cp

# Discrete-time double integrator: state [position, velocity], input acceleration.
dt = 0.1
A = np.array([[1.0, dt], [0.0, 1.0]])
B = np.array([[0.5 * dt**2], [dt]])
n, m = 2, 1

N = 20                      # prediction horizon
Q = np.diag([10.0, 1.0])    # care about position more than velocity
R = np.array([[0.1]])       # cheap-ish control
x_ref = np.array([1.0, 0.0])   # drive to position 1, velocity 0

def solve_mpc(x0):
    x = cp.Variable((n, N + 1))     # predicted states
    u = cp.Variable((m, N))         # predicted inputs
    cost = 0
    constraints = [x[:, 0] == x0]   # pin the current state
    for k in range(N):
        cost += cp.quad_form(x[:, k] - x_ref, Q) + cp.quad_form(u[:, k], R)
        constraints += [x[:, k + 1] == A @ x[:, k] + B @ u[:, k]]   # dynamics
        constraints += [cp.abs(u[:, k]) <= 2.0]                     # |accel| <= 2
        constraints += [cp.abs(x[1, k]) <= 1.0]                     # |velocity| <= 1
    cost += cp.quad_form(x[:, N] - x_ref, Q)                        # terminal cost
    prob = cp.Problem(cp.Minimize(cost), constraints)
    prob.solve(solver=cp.OSQP, warm_start=True)
    return u[:, 0].value, prob.status      # apply only the FIRST input

# Receding horizon: solve, apply u0, step the real plant, repeat.
x = np.array([0.0, 0.0])
for t in range(60):
    u0, status = solve_mpc(x)
    assert status == "optimal", f"MPC infeasible at step {t}!"
    x = A @ x + B @ u0                      # the plant takes one real step
```

Read it against the QP in §2.5 — every line maps to a constraint or a cost term. `cp.quad_form(z, Q)` is `zᵀQz`. The dynamics are an equality constraint per step. The bounds are inequality constraints. `prob.solve()` runs OSQP. And `u[:, 0].value` is the *only* input you use — the receding horizon in one line.

### 3.1 Read the solver status, every time

The single most important habit: **check `prob.status` before you trust the solution.** The values you care about:

- `"optimal"` — solved; the QP was feasible and you have the optimal input. Use it.
- `"infeasible"` — *no* input sequence satisfies all the constraints. `u[:, 0].value` is `None`. You must recover (§4.3, and Lecture 2's failure modes). **Never send a command from an infeasible solve.**
- `"optimal_inaccurate"` / solver-specific warnings — solved but to loose tolerance, often from a too-short solve budget. Usable with care; investigate.

A controller that sends `u₀` without checking status will, the first time the QP is infeasible, send `None` (or stale garbage) to the motors. Checking the status *is* part of the control law.

---

## 4. Constraints — the whole reason MPC exists

### 4.1 Hard constraint vs. soft penalty: a categorical difference

Beginners often ask "why not just put a big penalty in the cost for going too fast, instead of a hard constraint?" The answer is the heart of MPC. A **penalty** in the cost *discourages* a behavior but will accept it if the trade-off pays off — the optimizer will gladly exceed your "soft" speed limit if doing so reduces tracking error enough. A **hard constraint** *forbids* it absolutely; the solver searches only over solutions that satisfy it. For anything safety-relevant — a velocity the actuator physically can't exceed, a workspace boundary, an obstacle — you need the hard version. "Mostly stays under the limit" is not a safety property. MPC's ability to express *hard* constraints is precisely what PID and LQR lack, and it's why warehouse AMRs (which operate near people, near racking, at speed) ship MPC.

### 4.2 The constraints you'll actually use

- **Input magnitude:** `|v| ≤ v_max`, `|δ| ≤ δ_max`. The actuator's physical limits. Always present.
- **Input rate:** `|u_{k+1} − u_k| ≤ Δu_max`. Acceleration limits (rate of velocity) and steering-rate limits (rate of steering angle). These keep the commanded trajectory *smooth* and within what the mechanism can physically slew — a car can't snap its wheels instantly, and a base can't step from 0 to 1.5 m/s in one tick without ripping the floor or the gearbox.
- **State bounds:** stay within the workspace, keep the velocity below a comfort/safety limit.
- **Obstacle avoidance:** the interesting one. An obstacle defines a region the robot must *avoid*, which is a *non-convex* constraint in general (the feasible region is "everywhere except a disk"). The standard MPC trick is to **linearize** it into a half-plane constraint each step: at the robot's current position relative to the obstacle, replace "stay outside the disk" with "stay on the safe side of the tangent line" — a linear constraint `aᵀx ≥ b` that keeps the QP convex. It's conservative (you give up a sliver of feasible space) but it keeps the problem solvable fast, and re-linearizing every step (because the robot moves) recovers most of what the conservatism cost you. You'll do exactly this in the challenge.

### 4.2.1 The obstacle half-plane, in code

The obstacle linearization is worth seeing concretely, because it's the constraint you'll meet in the challenge and it's the one beginners get wrong (by writing the non-convex version). Given an obstacle at center `c = [cx, cy]` with safety radius `r`, and the robot's current (or predicted) position `p`, the safe-side half-plane is the tangent to the safety circle perpendicular to the line from the obstacle to the robot:

```python
import numpy as np

def obstacle_halfplane(p, c, r):
    """Return (a, b) such that the constraint a^T x >= b keeps x on the safe side
    of the tangent to the circle of radius r around c, nearest to p."""
    d = p - c
    dist = np.linalg.norm(d)
    n = d / dist                 # unit vector from obstacle toward the robot
    # The tangent point is at c + r*n; stay on the robot side of the tangent line.
    a = n                        # constraint normal (points away from obstacle)
    b = n @ (c + r * n)          # the tangent line offset
    return a, b                  # enforce: a @ [x, y] >= b
```

In the QP you add `cons += [a @ x[:2, k] >= b]` for each step `k`, recomputing `(a, b)` from the *predicted* position at that step. Two things make this work: it's **linear** (so the QP stays convex), and you **re-linearize every control step** as the robot moves, so the conservative tangent approximation tracks the robot's changing bearing to the obstacle and you give up only a thin sliver of feasible space. The wrong version — `||x - c|| >= r`, the literal "stay outside the disk" — is non-convex, breaks the QP, and is the single most common obstacle-MPC mistake. Linearize; don't disk.

### 4.3 When a hard constraint is impossible: soft constraints and slack

Sometimes the hard constraints *can't all be satisfied* — a disturbance shoves the robot into a state from which no input keeps it within every bound, and the QP returns `infeasible`. An infeasible MPC gives you *no command*, which on a moving robot is dangerous. The pragmatic fix is **soft constraints**: relax the constraint with a non-negative **slack variable** `s` and add a large penalty on `s` to the cost:

```python
s = cp.Variable(nonneg=True)
constraints += [x[1, k] <= v_comfort + s]        # soft: allowed to exceed, but...
cost += 1e4 * s                                    # ...heavily penalized for doing so
```

Now the constraint is "violate this only if you absolutely must, and pay dearly." The QP stays feasible (there's always *some* `s` that works), the optimizer keeps `s` at zero whenever it can, and you get a usable command even in a momentarily-impossible situation — degrading gracefully instead of failing hard. **The rule: hard-constrain what is truly inviolable (the actuator's physical max, a wall), soft-constrain what is merely preferred (a comfort speed, a soft workspace margin).** Mixing the two correctly is a real MPC design skill, and getting it wrong is how an MPC either becomes infeasible at the worst moment or quietly violates a safety limit.

---

## 4.4 Worked example: watch a constraint bind

Concreteness helps. Take the double-integrator MPC from §3 and add a hard velocity limit `|v| ≤ 0.5`, then command a large position step that *wants* a high velocity. Without the constraint, the optimizer would build up speed well past 0.5 to reach the target fast. With the constraint, watch what happens:

```python
import numpy as np
import cvxpy as cp

dt = 0.1
A = np.array([[1.0, dt], [0.0, 1.0]])
B = np.array([[0.5 * dt**2], [dt]])
N, V_MAX = 20, 0.5

def solve(x0):
    x = cp.Variable((2, N + 1)); u = cp.Variable((1, N))
    cost, cons = 0, [x[:, 0] == x0]
    for k in range(N):
        cost += cp.quad_form(x[:, k] - np.array([2.0, 0.0]), np.diag([10.0, 1.0])) \
                + cp.quad_form(u[:, k], np.array([[0.1]]))
        cons += [x[:, k + 1] == A @ x[:, k] + B @ u[:, k]]
        cons += [cp.abs(x[1, k]) <= V_MAX]        # the binding constraint
        cons += [cp.abs(u[:, k]) <= 1.0]
    p = cp.Problem(cp.Minimize(cost), cons); p.solve(solver=cp.OSQP)
    return x.value, p.status

X, status = solve(np.array([0.0, 0.0]))
print("status:", status, " peak velocity:", X[1].max())   # pinned AT 0.5, not above
```

Run it and the peak velocity is *exactly* 0.5 — the constraint is **binding** (active). The optimizer drives at the speed limit for as long as it helps, then eases off to stop on target. That's the behavior LQR cannot produce: an LQR would compute a velocity profile peaking well above 0.5 and you'd have to crudely clip its output after the fact, which is suboptimal and breaks the optimality the LQR promised. MPC bakes the limit *into the optimization*, so the whole trajectory is optimal *subject to* the limit. This is the single clearest demonstration of why MPC exists, and Exercise 2 has you reproduce and quantify it against an unconstrained LQR on the same problem.

The vocabulary: a constraint is **active** (or **binding**) at the solution if it holds with equality (the velocity *is* 0.5), and **inactive** if there's slack (the velocity is comfortably below the limit). In the region where no constraint is active, the MPC behaves exactly like the LQR (§5). The constraints only change the answer where they bind — which is precisely the high-stakes region (near a limit, near an obstacle) where you needed them.

## 5. The LQR connection (and a sanity check)

Here's a fact that ties the three weeks together and gives you a free sanity check: **an MPC with no constraints, a long enough horizon, and a terminal cost equal to the LQR `P`, produces exactly the LQR control law.**

The intuition: LQR is the infinite-horizon optimal controller. MPC is the finite-horizon version. If you make the horizon long enough that the finite cut-off doesn't matter, *and* you cap the horizon with a terminal cost that correctly accounts for the infinite tail (which is precisely what the LQR `P` is), the two coincide. So if you build an unconstrained MPC and its first input `u₀` doesn't match `−K·x` from last week's LQR, **you have a bug** — wrong sign, wrong discretization, mismatched cost. Exercise 1 has you verify exactly this: build an unconstrained MPC, compare `u₀` to the LQR command, and confirm they agree. It's the strongest possible confirmation your MPC machinery is correct before you add constraints and lose the closed-form check.

This connection also explains *what the constraints actually do*: in the region where no constraint is active, MPC *is* LQR. The constraints only change the behavior when the robot is up against a limit — near max speed, near an obstacle, slewing hard. That's exactly when you want MPC and exactly when LQR would have failed. The rest of the time they're identical, which is why "MPC is LQR with constraints" is not a slogan but a precise statement.

---

## 5.5 Two ways to assemble the QP: sparse vs. condensed

A practical note that matters the moment you care about speed. There are two standard ways to hand the MPC to a solver, and knowing the difference is what lets you read other people's MPC code and understand `acados`'s choices next lecture.

- **Sparse (multiple-shooting) formulation.** Keep *both* the states `x₀…x_N` and inputs `u₀…u_{N−1}` as decision variables, with the dynamics as explicit equality constraints — exactly what we wrote in `cvxpy` above. The resulting QP is large (it has all the states) but *sparse* (the constraint matrices are mostly zeros, with a banded structure from the step-to-step dynamics). Modern QP solvers (OSQP, `acados`'s HPIPM) exploit that sparsity and are very fast on it. This is the default and what you'll use.

- **Condensed (single-shooting) formulation.** Eliminate the states by substituting the dynamics — express every `x_k` as a function of `x₀` and the input sequence `u₀…u_{N−1}`, so the *only* decision variables are the inputs. The QP becomes small (only inputs) but *dense* (every input affects every future state, so the matrices fill in). For short horizons the condensed form can be faster; for long horizons the sparse form usually wins because solvers exploit the banded structure better than they handle a dense matrix.

You don't choose this by hand this week — `cvxpy` builds the sparse form and OSQP exploits it. But when you read the `acados` docs (next lecture) and see "condensing" as a tuning option, this is what it means: trading a big-sparse problem for a small-dense one, with the right choice depending on your horizon length and solver. The takeaway for now: the QP you wrote *is* the sparse form, the sparsity is why it solves fast despite being large, and "how the problem is assembled for the solver" is itself a performance lever — one of several you'll pull when you fight for the latency budget.

## 6. The MPC tuning surface

MPC has more knobs than LQR, and they interact. The ones you'll turn:

- **Horizon length `N`.** Longer horizon → more foresight (sees obstacles and curves sooner, plans smoother), but a bigger QP and a slower solve (Lecture 2's latency story). Too short and the MPC is myopic — it doesn't see the obstacle until it's too late to avoid smoothly. There's a sweet spot where the horizon covers the relevant preview distance (roughly, how far the robot travels in the time it takes to react) without ballooning the solve.
- **Discretization `dt`.** The prediction step size. Finer `dt` → more accurate prediction but more steps to cover the same horizon time (more compute). Often you use the control period as `dt`, but for a long horizon you might predict at a coarser `dt` than you control at.
- **`Q`, `R`, terminal `P`.** Same error-vs-effort trade-off as LQR (Bryson's rule still applies for a starting point). The terminal `P` matters for stability with short horizons.
- **Solver tolerance / iteration cap.** The knob that trades solution accuracy for solve time — central to the latency budget. A looser tolerance solves faster but may return `optimal_inaccurate`.

The workflow is: pick `dt` from your control rate, pick `N` to cover the preview you need, set `Q`/`R` from Bryson, set terminal `P` to the LQR solution, then tune `N` and the tolerance against the *latency budget* (Lecture 2). You iterate on the cost and the horizon, not on a gain — the same "design intent in the cost" philosophy as LQR, with the horizon as the new dimension.

---

## 6.5 Two cheap tricks worth knowing: move-blocking and a separate control horizon

Two techniques that reduce the QP size without much loss, because you'll meet them in real MPC code and they're each one idea.

**Move-blocking / a shorter control horizon.** The prediction horizon `N` and the *control* horizon `Nc` don't have to be equal. You predict `N` steps ahead (for foresight), but you only let the input *change* for the first `Nc < N` steps, holding it constant for the rest. So instead of `N` free input vectors, you optimize `Nc` of them — a smaller QP, a faster solve — while still predicting the full horizon. The intuition: the far-future inputs barely affect the immediate decision (you'll re-solve before you ever execute them), so spending decision variables on them is low-value. A common choice is `Nc` around a third to a half of `N`. **Move-blocking** is the same idea generalized: group horizon steps into blocks and hold the input constant within each block, putting fine resolution near the start (where it matters) and coarse resolution far out (where it doesn't). Both cut solve time for little tracking cost and are standard in production MPC.

**Why these matter for the budget.** Everything in MPC deployment comes back to "make the QP smaller without losing what you need," and these are two of the cleanest levers: a shorter control horizon and move-blocking both shrink the decision-variable count directly. They join the levers from §6 (horizon length, discretization, tolerance) and the sparse/condensed choice from §5.5 as the toolkit you'll reach into when Lecture 2's profiler tells you you're over budget. None of them change the *formulation* — the QP is still tracking-plus-effort subject to dynamics and constraints — they change how finely you discretize the *decision*, which is a knob you turn against the latency budget. Knowing they exist now means that when you read an `acados` config with `Nc` and a control-horizon parameter, you understand what it's buying.

## 6.6 The full receding-horizon loop, annotated

To cement the whole picture, here is the complete MPC control loop with every step labeled — read it as the executable summary of this lecture:

```python
# One-time setup: model, cost, horizon.
A, B = discretize(continuous_model, dt)     # the prediction model (equality cons)
Q, R = bryson_QR(...)                         # the stage cost (track + effort)
P_term = solve_discrete_are(A, B, Q, R)       # terminal cost = LQR P (the tail)

x = measure_state()                           # where we actually are
prev_u = np.zeros(m)
while running:
    # 1. SOLVE the QP for the next N steps from the CURRENT measured state.
    u_seq, status = solve_qp(x, A, B, Q, R, P_term, bounds, prev_u)

    # 2. CHECK the status. Never command from a non-optimal solve.
    if status != "optimal":
        u0 = safe_fallback(x)                 # soften / fall back (Lecture 2 §4)
    else:
        u0 = u_seq[:, 0]                      # 3. APPLY ONLY THE FIRST input.

    send_to_actuators(u0)
    prev_u = u0

    # 4. ADVANCE one step: re-measure and re-solve next tick (receding horizon).
    x = measure_state()
```

Four numbered steps: solve, check, apply-one, advance. The `solve` carries the model and constraints; the `check` is the discipline that makes it safe; the `apply-one` is what makes it feedback; the `advance` is the receding horizon. Memorize this loop — it's MPC, and every elaboration this week and next (constraints, bicycle model, latency, fallback) hangs off one of these four steps. The genius and the cost of MPC both live here: the genius is that re-solving from measured state every tick gives you constrained, optimal, predictive feedback; the cost is that `solve_qp` runs *every single iteration of this loop*, which is the latency problem Lecture 2 spends its length on.

## 7. Recap

You should now be able to:

- Explain the receding-horizon loop (predict `N`, optimize the sequence, apply only `u₀`, re-solve) and why applying one step gives feedback.
- Formulate MPC as a QP: decision variables (predicted states/inputs), equality constraints (the dynamics), inequality constraints (the bounds), and the quadratic tracking-plus-effort objective with a terminal cost.
- Write and solve that QP in `cvxpy`, and *always* check `prob.status` before using the result.
- Add hard input, rate, state, and (linearized) obstacle constraints, and explain why a hard constraint is categorically different from a soft penalty.
- Soften a constraint with a slack variable to keep the QP feasible when the hard version is momentarily impossible.
- Use the unconstrained-MPC-equals-LQR fact as a correctness check.

Next: the kinematic-bicycle MPC for path tracking, the head-to-head with LQR, the latency profiling that decides whether your MPC is deployable, the move to `acados`/OSQP, and the failure modes that bite real MPCs. Continue to [Lecture 2 — The Bicycle MPC, Latency, `acados`, and Failure Modes](./02-bicycle-mpc-latency-acados-and-failure-modes.md).

---

## References

- Rawlings, Mayne & Diehl, *Model Predictive Control* — Ch. 1–2 (receding horizon, the QP, constraints): <https://sites.engineering.ucsb.edu/~jbraw/mpc/>
- Borrelli, Bemporad & Morari, *Predictive Control for Linear and Hybrid Systems* — the QP formulation: <https://www.mpc.berkeley.edu/mpc-course-material>
- `cvxpy` control example and tutorial: <https://www.cvxpy.org/examples/basic/index.html>
- OSQP documentation (the QP solver, warm-starting, status codes): <https://osqp.org/docs/>
- Steve Brunton — Model Predictive Control episodes: <https://www.youtube.com/@Eigensteve>
