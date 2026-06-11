# Lecture 1 — State-Space, Controllability, and the LQR Cost

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can write a robot's dynamics in state-space form, linearize a nonlinear model around an operating point, test controllability, and design the `Q`/`R` cost matrices that encode your engineering priorities — everything you need *before* you call the Riccati solver.

If you remember one sentence from this entire week, remember this one:

> **LQR moves your engineering decisions from the gains to the cost. You stop tuning `Kp`, `Ki`, `Kd` by feel; you write down how much you care about each state error and each unit of control effort, and the solver hands you the optimal gains. The skill is no longer "tune the gains" — it's "model the system and design the cost."**

Last week's PID was a *scalar* controller: one error in, one command out, three gains tuned by watching a plot. That works beautifully until you have several coupled states to control at once — and a path-tracking diff-drive robot has at least two (how far off the path am I, and which way am I pointed) that interact strongly. Hand-tuning a multi-input multi-output gain matrix by feel is hopeless. LQR solves the whole matrix at once, optimally, from a model and a cost. This lecture builds the model and the cost. Lecture 2 does the solve.

---

## 1. State-space: the language of multivariable control

### 1.1 What is a state?

The **state** `x` of a system is the minimal set of numbers that, together with the future inputs, completely determines the future behavior. For a diff-drive robot driving in the plane, a natural state is its pose:

```
x = [ px ]   robot x position
    [ py ]   robot y position
    [ θ  ]   robot heading (yaw)
```

The **input** (or control) `u` is what you can command. For diff-drive:

```
u = [ v ]   forward (linear) velocity
    [ ω ]   angular velocity (yaw rate)
```

(These are exactly the two numbers you put in a `Twist` on `/cmd_vel`.)

### 1.2 The state-space equations

A **linear** system is written:

```
ẋ = A x + B u        (state / dynamics equation)
y = C x + D u        (output / measurement equation)
```

- `A` is the **system matrix** (`n×n`): how the state evolves *on its own*, with no input. Its eigenvalues are the system's natural modes — stable if they have negative real part, unstable otherwise.
- `B` is the **input matrix** (`n×m`): how your `m` control inputs enter the `n` state derivatives.
- `C` is the **output matrix** (`p×n`): which combinations of states you actually *measure*.
- `D` is the **feedthrough matrix** (usually zero for robots): direct input-to-output coupling.

For control design we mostly care about `A` and `B` (the dynamics); `C` matters for the estimation/observability side (and for the Kalman dual in Lecture 2). The whole point of writing the robot this way is that *all* the machinery — controllability, LQR, Kalman — is expressed in terms of these matrices, regardless of how many states you have. The math doesn't care whether `x` is 3-dimensional or 30-dimensional.

---

## 2. Linearization: getting `A` and `B` from a nonlinear robot

Here's the catch: the diff-drive robot is **not** linear. Its true kinematics are:

```
ẋ = v·cos θ
ẏ = v·sin θ
θ̇ = ω
```

Those `cos θ` and `sin θ` terms make it nonlinear — `A` and `B` would have to depend on the state, which LQR doesn't allow. LQR needs constant `A` and `B`. The standard move: **linearize around an operating point.**

### 2.1 The Jacobian linearization

Write the dynamics as `ẋ = f(x, u)`. Near an operating point `(x₀, u₀)`, a first-order Taylor expansion gives:

```
A = ∂f/∂x  evaluated at (x₀, u₀)
B = ∂f/∂u  evaluated at (x₀, u₀)
```

These Jacobians are constant matrices (numbers, once you plug in the operating point). The linear model `ẋ ≈ A(x − x₀) + B(u − u₀)` is a good approximation *near* the operating point and gets worse as you move away from it — which is exactly why gain scheduling (Lecture 2) exists.

### 2.2 The error-dynamics trick for path tracking

For path tracking we don't want to regulate the *absolute* pose to zero — we want to drive the *error relative to the path* to zero. The clean formulation uses the **error state**: cross-track error `e_y` (lateral distance from the path), heading error `e_θ` (angle between the robot heading and the path tangent), and sometimes a velocity error. Linearizing the error dynamics around "on the path, at reference speed `v_ref`, zero heading error" gives a tidy constant `A`/`B`. A common diff-drive path-tracking model is:

```
state x = [ e_y, e_θ ]        (cross-track error, heading error)
input u = [ δω ]              (yaw-rate correction about the reference)

       d/dt [ e_y ]   [ 0   v_ref ] [ e_y ]   [ 0 ]
            [ e_θ ] = [ 0    0    ] [ e_θ ] + [ 1 ] · δω
                       └─── A ────┘            └ B ┘
```

Read it physically: cross-track error changes at a rate `v_ref·e_θ` (if you're pointed off-axis and moving forward, you drift sideways), and heading error changes directly with your yaw-rate correction. This is the model you build in Exercise 1 and control all week. Notice `v_ref` appears *in* `A` — the dynamics literally depend on how fast you're going, which is why a controller tuned at one speed isn't optimal at another. Hold that thought for gain scheduling.

```python
import numpy as np

def diff_drive_error_AB(v_ref):
    """Linearized diff-drive PATH-TRACKING error dynamics.
    State = [cross_track_error, heading_error]; input = yaw-rate correction."""
    A = np.array([[0.0, v_ref],
                  [0.0, 0.0]])
    B = np.array([[0.0],
                  [1.0]])
    return A, B

A, B = diff_drive_error_AB(v_ref=0.5)
```

> **Honesty about linearization:** this is valid for *small* errors near the path at *roughly* `v_ref`. Drive the robot far off the path, or change speed dramatically, and the real dynamics diverge from this `A`/`B`, and the LQR gain that was optimal here becomes merely "okay." That's not a flaw in LQR; it's the price of turning a nonlinear problem into a linear one. MPC (next week) and gain scheduling (Lecture 2) are the two principled ways to manage it.

---

## 3. Controllability: can LQR even help you?

Before you spend any effort on cost design, you must answer a yes/no question: **can the inputs actually steer every state?** If some combination of states is *uncontrollable* — no input can affect it — then no controller, LQR or otherwise, can do anything about it, and the LQR solve will either fail or hand you a gain that silently ignores that mode.

### 3.1 The controllability matrix

For a system `(A, B)` with `n` states, form the **controllability matrix**:

```
𝒞 = [ B  AB  A²B  …  Aⁿ⁻¹B ]
```

The system is **controllable** if and only if `𝒞` has full row rank (`rank(𝒞) = n`). The intuition: `B` is the directions you can push *right now*; `AB` is where those pushes propagate after one instant of dynamics; `A²B` after two; and so on. If, after stacking all `n` of these, you span the entire `n`-dimensional state space, you can reach anywhere — you're controllable.

```python
import numpy as np

def controllability_matrix(A, B):
    n = A.shape[0]
    blocks = [B]
    for i in range(1, n):
        blocks.append(A @ blocks[-1])      # A^i B
    return np.hstack(blocks)

C = controllability_matrix(A, B)
rank = np.linalg.matrix_rank(C)
print(f"controllability rank: {rank}  (need {A.shape[0]})")
assert rank == A.shape[0], "UNCONTROLLABLE — LQR cannot fix a mode no input can reach"
```

For the diff-drive error model above, `𝒞 = [B, AB] = [[0, v_ref], [1, 0]]`, which has rank 2 = `n` as long as `v_ref ≠ 0`. That's a real physical fact: **a diff-drive robot can't correct cross-track error while standing still** (`v_ref = 0` makes it uncontrollable), because the only way to reduce lateral error is to drive forward while turning. LQR *encodes* that physics — at `v_ref = 0` the controllability check fails, telling you the problem is ill-posed, not that your code is buggy. Run the check; believe it.

### 3.2 Observability — the dual, for the estimator side

There's a mirror-image question for estimation: can you *reconstruct* the full state from the outputs you measure? That's **observability**, tested by the rank of the **observability matrix** `𝒪 = [C; CA; CA²; …; CAⁿ⁻¹]` (stacked vertically). A system is observable iff `rank(𝒪) = n`. You'll use this on the Kalman side in Lecture 2 — and the deep fact, which we'll make precise, is that *observability of `(A, C)` is exactly controllability of `(Aᵀ, Cᵀ)`*. Controllability and observability are the same theorem looked at from two ends. That duality is what makes LQR and the Kalman filter the same math.

### 3.3 Stabilizability (the weaker condition you actually need)

A technical note worth knowing: LQR doesn't strictly require *full* controllability — it requires **stabilizability**, which means every *unstable* mode is controllable (you're allowed to have uncontrollable modes as long as they're already stable and will decay on their own). In practice, for robot models, check full controllability; if it fails, find out *which* mode is uncontrollable and whether it's stable before deciding whether you have a real problem or a benign one. For everything this week, full controllability is the target.

---

## 4. The LQR cost: where your engineering judgment goes

Now the heart of it. You have a controllable linear model `(A, B)`. You want a feedback law `u = −Kx` that drives the state to zero. There are infinitely many `K`'s that stabilize the system — which one is *best*? LQR answers "best with respect to a cost you define."

### 4.1 The quadratic cost functional

LQR minimizes:

```
       ┌ ∞
J  =   │  ( xᵀ Q x  +  uᵀ R u )  dt
       ┘ 0
          └─ state ─┘  └ effort ┘
          error cost     cost
```

- `xᵀQx` penalizes the state being away from zero. `Q` is a symmetric positive-semidefinite `n×n` matrix; its `(i,i)` entry says "how much do I care about state `i` being off."
- `uᵀRu` penalizes control effort. `R` is symmetric positive-definite `m×m`; its `(j,j)` entry says "how much do I care about working actuator `j`."

The optimal `K` is the one feedback law that makes this integral as small as possible over all time. That's it — that's the entire specification. Everything else (the Riccati equation, the gain) is *machinery* for solving this minimization. **Your job is the cost; the solver's job is the gain.**

### 4.2 The fundamental trade-off

`Q` and `R` are in tension, and the tension *is* the design:

- **Big `Q` (or small `R`)** → you care a lot about killing state error and little about effort → the controller is **aggressive**: fast, high-gain, big commands, but more likely to saturate the actuator and amplify noise.
- **Small `Q` (or big `R`)** → you care about gentle actuation → the controller is **relaxed**: smooth, conservative, slower to correct error.

Only the *ratio* `Q/R` matters for the gain — scaling both by the same factor leaves `K` unchanged. So in practice you fix `R` (say to identity) and scale `Q` up to get more aggressive, down to get gentler. Tuning LQR *is* sweeping that ratio and watching the closed-loop response, the same loop as PID tuning but with one knob (the cost ratio) instead of three coupled gains, and with the optimality guarantee that for whatever cost you land on, `K` is the best possible.

### 4.3 Designing `Q` and `R` — Bryson's rule

Staring at a blank `Q` matrix is intimidating. **Bryson's rule** gives a principled, units-aware first guess: set each diagonal entry to the reciprocal of the square of the largest value you're willing to tolerate for that quantity.

```
Q_ii = 1 / (max acceptable value of state x_i)²
R_jj = 1 / (max acceptable value of input u_j)²
```

The genius of this is **units**. Your cross-track error is in meters, your heading error in radians, your control effort in rad/s — you can't just put `1`s on the diagonals and compare them, because a 1 m error and a 1 rad error are wildly different in significance. Bryson's rule normalizes each term by what "bad" means for that quantity, so the cost adds up apples to apples. Example:

```python
import numpy as np

# I can tolerate up to 0.1 m cross-track error and 0.2 rad heading error.
e_y_max, e_theta_max = 0.1, 0.2
# I can tolerate up to 1.0 rad/s of yaw-rate correction.
u_max = 1.0

Q = np.diag([1.0 / e_y_max**2, 1.0 / e_theta_max**2])   # [[100, 0], [0, 25]]
R = np.array([[1.0 / u_max**2]])                          # [[1.0]]
```

This is your *starting* `Q`/`R`, not your final one. From here you iterate: too sluggish on cross-track? scale up `Q[0,0]`. Saturating the actuator? scale up `R`. But you iterate from a sane, units-correct baseline instead of from random matrices — which is the difference between converging in twenty minutes and flailing for an afternoon.

### 4.4 Diagonal vs. full matrices

Almost always you use **diagonal** `Q` and `R` — each state and input penalized independently. Off-diagonal terms in `Q` penalize *correlations* between state errors (and let you express things like "I care about cross-track error and heading error being wrong *in the same direction*"), but they're rarely needed and hard to reason about. Start diagonal. Add off-diagonal terms only when you have a specific, articulable reason. A reviewer who sees a full `Q` will ask you to justify every off-diagonal entry, and "I was experimenting" is not a justification.

---

## 5. Putting the pieces together (before the solve)

At this point, for any robot subsystem, you can produce the four ingredients LQR needs:

1. **`A`, `B`** — from linearizing the dynamics at an operating point.
2. **Controllability check** — `rank([B AB … Aⁿ⁻¹B]) == n`. If it fails, stop and understand why.
3. **`Q`** — diagonal, from Bryson's rule, penalizing each state error by `1/x_max²`.
4. **`R`** — diagonal, from Bryson's rule, penalizing each input by `1/u_max²`.

```python
import numpy as np

v_ref = 0.5
A = np.array([[0.0, v_ref], [0.0, 0.0]])
B = np.array([[0.0], [1.0]])

# Controllability.
Cm = np.hstack([B, A @ B])
assert np.linalg.matrix_rank(Cm) == 2, "uncontrollable"

# Cost (Bryson).
Q = np.diag([1.0 / 0.1**2, 1.0 / 0.2**2])
R = np.array([[1.0 / 1.0**2]])

print("A=\n", A, "\nB=\n", B, "\nQ=\n", Q, "\nR=\n", R)
# Next lecture: solve the Riccati equation for K from exactly these four matrices.
```

That's the whole front half of LQR design. Notice what you *didn't* do: you never tuned a gain. You modeled the robot and stated your priorities. The next lecture turns these four matrices into the optimal `K` with a single function call and the three sanity checks that confirm it's trustworthy.

---

## 6. Why this scales where PID doesn't

It's worth pausing on the payoff, because it justifies the matrix-heavy week. With PID, adding a second controlled state means a second PID loop, and if the two states *couple* (cross-track and heading absolutely do), the two loops fight each other and you tune them against each other by hand, forever. With LQR, a second state is one more row in `x`, one more diagonal entry in `Q`, and the solver accounts for *all* the coupling automatically — the optimal `K` already knows that turning to fix heading error will change cross-track error, and trades them off optimally. That's the "adult supervision" in "PID with adult supervision": LQR handles multivariable coupling that PID makes you handle by hand. A 6-DOF arm, a quadrotor with twelve states, a robot with strongly coupled dynamics — these are where PID's per-loop tuning collapses and LQR's model-and-cost approach keeps working with no extra conceptual machinery, just bigger matrices.

---

## 7. A second worked model: the cart-pole, the controls "hello world"

Before you trust LQR on your robot, build it on the canonical example — the **cart-pole** (an inverted pendulum on a moving cart). It's worth fifteen minutes because it's the example every controls reference uses, it's *unstable* open-loop (the pole falls over), and watching LQR stabilize an unstable system is the moment the method clicks.

The state is `x = [p, ṗ, φ, φ̇]` — cart position, cart velocity, pole angle (from vertical), pole angular velocity — and the input is the force `F` on the cart. Linearizing the nonlinear pendulum dynamics around the *upright* equilibrium (`φ = 0`) gives a constant `4×4` `A` and `4×1` `B`:

```python
import numpy as np

def cartpole_AB(M=1.0, m=0.2, l=0.5, g=9.81):
    """Cart-pole linearized about upright. State [p, p_dot, phi, phi_dot], input F."""
    A = np.array([
        [0, 1, 0, 0],
        [0, 0, -m * g / M, 0],
        [0, 0, 0, 1],
        [0, 0, (M + m) * g / (M * l), 0],
    ])
    B = np.array([[0], [1 / M], [0], [-1 / (M * l)]])
    return A, B

A, B = cartpole_AB()
print("open-loop eigenvalues:", np.linalg.eigvals(A))   # one has POSITIVE real part!
```

Run it and you'll see one eigenvalue with a **positive real part** — the open-loop system is unstable, exactly as physics demands (let go of an upright pole and it falls). Now check controllability (`rank([B AB A²B A³B]) == 4` — it is) and you've confirmed LQR *can* stabilize it. Next lecture you'll solve for `K` and watch the unstable pole get held upright by optimal feedback. The cart-pole matters because if your LQR code stabilizes an unstable system, you trust it on your robot's stable-but-drifting one. Replicate it before you ship.

## 8. The fundamental limit: LQR assumes a perfect model and full state

One honesty note before the recap, because it's the seam where LQR meets reality. LQR is *optimal* — but optimal *with respect to the model and cost you gave it*. Two assumptions are baked in:

- **You know the full state.** The control law `u = −Kx` needs every component of `x`. If you can't measure all of it (you usually can't — you measure position, not velocity directly), you need an *estimator* to reconstruct it. That's the Kalman filter, and the separation principle (Lecture 2 §5) is what lets you bolt an estimator onto an LQR cleanly.
- **The model is right.** `K` is optimal for *your* `A`/`B`. If the real robot's dynamics differ — unmodeled friction, a payload you didn't account for, a linearization that's stale because you drove far from the operating point — the gain is no longer optimal and, in the worst case, not even stabilizing. LQR has famously good *robustness margins* (guaranteed gain and phase margins for the full-state-feedback case), which is part of why it's trusted, but those margins evaporate if you close the loop through a poorly-tuned estimator. The practical takeaway: LQR is robust to *moderate* model error and gives you margin to spare, but it is not magic, and "my model was wrong" is the most common reason an LQR underperforms in the field.

This is precisely the gap MPC narrows next week: by re-optimizing every step against the *current* state and an explicit model, and by handling constraints the quadratic cost can't, MPC tolerates a wider range of conditions — at a much higher compute cost. LQR is the cheap, elegant, model-trusting baseline; know its assumptions so you know when to reach past it.

## 8.5 Discrete vs. continuous, and which `A`/`B` you actually need

A practical clarification, because it trips people up when they move from the math to the code. The dynamics we've written (`ẋ = Ax + Bu`) are **continuous-time** — they describe the instantaneous rate of change. But your controller runs at a sample rate (50 Hz, `dt = 0.02 s`), and any *simulation* of the system steps in discrete time. So there are two pairs of matrices floating around:

- **Continuous `(A, B)`** — from the Jacobian linearization. These go into the *continuous* Riccati solver (`solve_continuous_are`, next lecture) and are the natural output of linearizing physics.
- **Discrete `(A_d, B_d)`** — the continuous model converted to "given the state now, what's the state one sample later." You get them with `scipy.signal.cont2discrete` (which computes the matrix exponential `A_d = e^{A·dt}` and the corresponding `B_d`), and they go into the *discrete* Riccati solver (`solve_discrete_are`) and into your simulation loop.

For *control design* this week, the continuous solve is the default and what we use — it's cleaner and, for fast loops, the resulting gain is essentially the same as the discrete one. For *simulating* the closed loop to check your gain, you step the discrete model (or integrate the continuous one with small steps). The one mistake to avoid: mixing them — solving the continuous Riccati but then simulating as if the matrices were discrete, or vice versa. Keep straight which pair you're holding. The exercises are explicit about it, and the rule of thumb is: linearize → continuous `(A,B)` → `solve_continuous_are` for the gain; convert to discrete only when your loop is slow enough that the discretization matters (next lecture §1.4) or when you simulate.

## 9. Recap

You should now be able to:

- Write a robot's dynamics in state-space form `ẋ = Ax + Bu` and say what `A` and `B` mean.
- Linearize a nonlinear model (diff-drive) around an operating point to get constant `A`/`B`, and use the error-dynamics formulation to turn path tracking into a regulation problem.
- Build the controllability matrix, test its rank, and interpret an uncontrollable mode physically (a diff-drive robot can't fix cross-track error at zero speed).
- Write the LQR cost `J = ∫(xᵀQx + uᵀRu) dt` and explain the `Q`-vs-`R` (error-vs-effort) trade-off.
- Design `Q` and `R` with Bryson's rule, and explain why its units-normalization is the whole point.

Next: solving the algebraic Riccati equation for the optimal gain, adding integral action for zero steady-state error, gain scheduling across operating points, shipping it as a `ros2_control` plugin, and the LQR/LQE duality that ties controls and estimation into one idea. Continue to [Lecture 2 — Riccati, Integral Action, Scheduling, and Duality](./02-riccati-integral-action-scheduling-and-duality.md).

## 10. The four-ingredient checklist

Before you move to the solve, internalize the checklist — it's what you'll run for *every* LQR design for the rest of your career:

1. **Model.** Linearize the dynamics at the operating point → constant `A`, `B`. Know where the linearization is valid.
2. **Controllability.** `rank([B AB … Aⁿ⁻¹B]) == n`? If not, *stop* and understand the uncontrollable mode physically before going further.
3. **`Q`.** Diagonal, from Bryson's rule (`1/x_i,max²`). Each entry says how much you care about that state being off.
4. **`R`.** Diagonal, from Bryson's rule (`1/u_j,max²`). Each entry says how much you care about working that actuator.

Four objects, four lines of `numpy`. Notice again what's *absent*: no gains. You modeled and you prioritized; the gain is the solver's job, next lecture. If you can produce these four objects for a robot subsystem and run the controllability check, you have done the hard, judgment-heavy part of LQR — the rest is a function call and three sanity checks.

Concretely, the workflow you'll run in the exercises is:

1. Build `A`, `B` at the operating point.
2. Confirm `rank([B AB … Aⁿ⁻¹B]) == n`.
3. Set `Q`, `R` from Bryson's rule.
4. (Next lecture) solve for `K`, check the three conditions, simulate.
5. Too aggressive or too sluggish? Adjust the `Q/R` ratio, re-solve, re-simulate.

Step 5 is the loop, and it's short because there's one knob (the ratio) and a fast solver. Contrast the PID loop, where step 5 was "adjust one of three coupled gains and hope the others still hold." That's the productivity gain LQR buys once the model exists.

A final mental model to carry into the solve: think of `Q` and `R` as the two ends of a seesaw. Push `Q` up and the controller leans toward accuracy (aggressive, fast, big commands). Push `R` up and it leans toward economy (gentle, smooth, conservative). The optimal gain is wherever you set the balance, and the solver finds it exactly. Tuning LQR is moving that one balance point and watching the closed-loop poles slide — far more tractable than juggling three coupled PID gains, and the reason a 30-state system is no harder to *design* than a 2-state one: it's the same seesaw, just with more weights on each side.

---

## References

- *Feedback Systems* (Åström & Murray), Ch. 6–7 (state-space, controllability) and the Optimization-Based Control LQR notes: <https://fbswiki.org/wiki/index.php/Main_Page>
- *Underactuated Robotics* (Tedrake), the LQR chapter (linearize-and-LQR, cost design): <https://underactuated.mit.edu/lqr.html>
- Hespanha, *Linear Systems Theory* — controllability/observability: <https://web.ece.ucsb.edu/~hespanha/linearsystems/>
- Steve Brunton, Control Bootcamp — state-space and LQR episodes: <https://www.youtube.com/playlist?list=PLMrJAkhIeNNR20Mz-VpzgfQs5zrYi085m>
- `scipy.linalg.solve_continuous_are` (next lecture's solver): <https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_continuous_are.html>
