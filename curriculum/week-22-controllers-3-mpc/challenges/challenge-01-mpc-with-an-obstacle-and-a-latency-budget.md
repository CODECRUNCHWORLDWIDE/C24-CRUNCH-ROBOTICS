# Challenge 1 — MPC with an Obstacle and a Latency Budget

**Time estimate:** ~90 minutes.

## Problem statement

The syllabus lab for this week is explicit: *"Implement a kinematic-bicycle MPC for path tracking with `do-mpc`. Track a figure-8 reference at 1 m/s with hard velocity and steering-rate limits. Compare to LQR. Profile the solve time on the Orin Nano; document the latency budget."* This challenge is that lab, plus the one thing that makes MPC genuinely worth its cost: an **obstacle**.

You will extend the bicycle MPC from Exercise 3 with **obstacle-avoidance constraints**, place an obstacle on the figure-8 so the robot must route around it, and then make the whole thing **fit a hard per-step latency budget** — documenting the horizon-versus-latency trade-off and your plan for when the QP goes infeasible. This is MPC at deployment shape: it tracks, it avoids, it's safe, and it's fast enough.

## Setup

Use **Exercise 3** (`exercise-03-bicycle-mpc-tracking.py`) as your base. You'll add the obstacle constraint, place an obstacle, and run with `--profile`. Use OSQP via `cvxpy` (or drop to OSQP-direct / `acados` for the latency stretch). Pick a control rate and therefore a budget (e.g. 20 Hz → 50 ms, or 50 Hz → 20 ms — state which and why).

## Your task

### Part A — Add obstacle avoidance

1. **Place an obstacle** (a disk of radius `r` at some point on the figure-8) that blocks the nominal path.
2. **Add the avoidance constraint** as a *linearized half-plane* (Lecture 1 §4.2): each step, given the robot's predicted position relative to the obstacle center, require the position to stay on the safe side of the tangent line to the obstacle's safety circle — a linear constraint `aₖᵀ[x,y] ≥ bₖ` that keeps the QP convex. Re-linearize the half-plane each control step as the robot moves.
3. **Demonstrate the robot routes around** the obstacle while still tracking the rest of the figure-8, and that without the constraint it would have driven through.

### Part B — Make it fit the budget

4. **Profile** the solve time (mean / p95 / max) at your chosen control rate. Report p95 against the budget.
5. **If p95 exceeds the budget** (it likely will with `cvxpy` at a tight rate), bring it into budget by some combination of: shortening the horizon `N`, warm-starting harder, reducing the constraint count, or porting the solve to **OSQP-direct or `acados`**. Document *what you changed and what it cost* (e.g., "cut `N` from 20 to 10, p95 dropped from 31 ms to 9 ms, but the robot now starts avoiding the obstacle 0.5 s later").
6. **Compare to LQR** on the same path *without* the obstacle (LQR can't do the obstacle at all — that's the point), to quantify what tracking quality the MPC's machinery costs you when no constraint is active.

### Part C — Plan for infeasibility

7. **Write the infeasibility-recovery plan** (Lecture 2 §4.1): what does the controller do the step the QP returns `infeasible`? Soft constraints? A braking fallback? The LQR? Implement *at least* the detection (check `prob.status`) and one recovery (a safe fallback command), and demonstrate it by tightening the obstacle until the QP is momentarily infeasible.

## The report (`mpc-obstacle-latency-report.md`)

The deliverable a reviewer reads. It must contain:

1. **The formulation** — the model, the cost, the hard constraints (velocity, steering-rate, obstacle half-plane), and how you linearize the obstacle each step.
2. **The avoidance demonstration** — a path plot showing the robot routing around the obstacle, and a with/without-constraint overlay proving the constraint did the work.
3. **The latency table** — mean/p95/max solve time at your control rate, against the budget, *before and after* your optimizations, with what each optimization cost.
4. **The horizon-vs-latency trade-off** — a short discussion (with at least two `(N, p95, tracking-quality)` data points) of how shortening the horizon traded foresight for speed.
5. **The infeasibility plan** — the detection and recovery, demonstrated.
6. **The verdict** — at what control rate and horizon is this MPC deployable on Orin-class hardware, and what would you change to ship it (almost certainly: leave `cvxpy` for `acados`)?

## Acceptance criteria

- [ ] `mpc-obstacle-latency-report.md` exists with all six sections.
- [ ] The MPC routes around the obstacle (shown); without the constraint it drives through (shown).
- [ ] The obstacle constraint is a *linearized half-plane* re-computed each step, keeping the QP convex (not a non-convex disk constraint that breaks the QP).
- [ ] The solve time is profiled (mean/p95/max) and compared to a stated budget, before and after at least one optimization.
- [ ] At least two `(N, p95)` data points document the horizon-vs-latency trade-off.
- [ ] `prob.status` is checked every step and at least one infeasibility-recovery path is implemented and demonstrated.
- [ ] Committed to your Week 22 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

Two traps. First, the **non-convex obstacle**: if you write the avoidance as "distance to obstacle ≥ r" directly, that's a non-convex constraint and your QP is no longer a QP — OSQP will choke or you'll have silently left the convex world. The fix is the *linearized half-plane*: each step, replace the disk with a tangent line at the robot's current bearing to the obstacle. It's conservative (you give up a sliver of space) but it stays a QP and you re-linearize as you move, recovering most of the lost space. Second, the **profiling self-deception**: reporting the *mean* solve time and declaring victory. A control loop has a hard deadline *every* period; if the mean is 8 ms but the p95 is 60 ms on a 20 ms budget, you miss the deadline one step in twenty, which is a jerk or a dropped command, which on a robot near an obstacle is exactly the moment you couldn't afford it. **Budget for the tail.** A reviewer who sees only a mean solve time will ask for the p95, and "I didn't measure it" is the wrong answer when the robot is near people.

## Stretch

- **Port to `acados`.** Reimplement the obstacle MPC with `acados` and its real-time-iteration scheme. Profile against your `cvxpy` version. The speedup is usually dramatic and is the literal difference between "ran in a notebook" and "ran on the robot."
- **Multiple obstacles.** Add a second and third obstacle (more half-planes, more constraint rows) and watch the solve time grow with constraint count (Lecture 2 §3.3). Quantify the per-obstacle latency cost.
- **Soft obstacle margin.** Make the obstacle's *comfort* margin soft (slack + penalty) while keeping the obstacle's *hard* radius hard. Show the robot shaves the comfort margin under pressure but never the hard radius — the soft/hard split from Lecture 1 §4.3 applied to a safety constraint.

## Why this matters

At the Phase 3 milestone in Week 24, a reviewer will ask "your MPC tracks well — but does it fit the control budget, and what happens when it can't find a feasible plan?" This challenge *is* that conversation. Every warehouse-AMR and self-driving company that ships MPC has an engineer whose entire job is the answer to those two questions, because an MPC that's elegant offline and 80 ms per solve on the target hardware is not a controller — it's a research demo. The engineer who can route around an obstacle, fit the deadline, and have a plan for the infeasible step is the one whose MPC actually goes on the robot. That's the whole point of the latency obsession: an optimal command that arrives after the deadline is just a late command.
