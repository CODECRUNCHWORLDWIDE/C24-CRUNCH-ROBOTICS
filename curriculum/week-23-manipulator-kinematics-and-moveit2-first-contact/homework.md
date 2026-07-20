# Week 23 Homework

Six problems that drive the kinematics into your fingers and the MoveIt2 stack into your hands. The full set should take about **5 hours**. Work in your Week 23 Git repository (the same workspace as the exercises and the `crunch_arm` mini-project) so every problem produces at least one commit you can point to at the Phase 3 milestone in Week 24.

The headline deliverable is **Problem 4 — the analytic-vs-numerical IK comparison**, the artifact a reviewer reads to see whether you understand *why* a shop reaches for one IK family over another.

Each problem includes a short **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`) and your overlay if you've built one. Have your **MoveIt2 arm** (UR5e or MyCobot) bringable up — Problems 1, 4, 5, and 6 use it. The pure-math problems (2, 3) run with NumPy alone.

---

## Problem 1 — FK three ways, all agreeing

**Problem statement.** For your arm and a fixed non-trivial joint vector, compute the `base_link → tool0` transform **three** ways and show they agree to 1e-4 m: (1) your product-of-exponentials `fk_space` from Exercise 1, (2) `ros2 run tf2_ros tf2_echo base_link tool0`, and (3) `ros2 service call /compute_fk`. Record all three.

**Acceptance criteria.**

- `notes/week-23/fk-three-ways.md` shows the joint vector and the resulting tool0 position/orientation from all three sources, side by side.
- They agree to ~1e-4 m in position and ~1e-3 rad in orientation.
- If you had to fix a screw axis or `M` to make them agree, you say which and why.
- Committed.

**Hint.** Use the same joint vector everywhere. The classic discrepancy is an `M` read at a non-zero config, or a screw `v = -ω × q` computed with `q` in the wrong frame. Three independent sources agreeing is real proof; two against one tells you which to fix.

**Estimated time.** 45 minutes.

---

## Problem 2 — Find a singularity and measure it

**Problem statement.** Using your FK and `space_jacobian` from Exercise 1, search for a configuration where the smallest singular value of the Jacobian drops below 0.05. Report the joint vector, the singular values, the Yoshikawa manipulability, and the condition number. Identify *which* singularity family (shoulder, elbow, or wrist) it is and why.

**Acceptance criteria.**

- `notes/week-23/singularity.md` records the singular configuration, its singular values, manipulability, and condition number.
- You name the singularity family (shoulder / elbow / wrist) and justify it geometrically (which axes lined up).
- A second, well-conditioned configuration is shown for contrast (smallest singular value comfortably above 0.3).
- Committed.

**Hint.** The elbow singularity is the easiest to find: stretch the arm nearly straight (`elbow_joint` near 0). Sweep one joint and watch the manipulability dip. The wrist singularity is `wrist_2_joint` near 0 (two wrist axes collinear).

**Estimated time.** 40 minutes.

---

## Problem 3 — Damped least squares vs. naive pseudoinverse

**Problem statement.** Extend Exercise 2 (or port it to your 6-DOF arm's FK/Jacobian). Pick a target near a singularity. Run both the naive-pseudoinverse and the damped-least-squares IK from the same seed. Plot or tabulate the joint-step magnitude per iteration for both, and the final residual error. Show the naive step exploding and the damped step staying bounded.

**Acceptance criteria.**

- `notes/week-23/dls-vs-naive.md` shows a table or plot of step magnitude per iteration for both solvers on a near-singular target.
- The naive solver's step magnitude is at least an order of magnitude larger than the damped solver's near the singularity.
- You state, in one sentence, what `λ` does to the `1/σ_min` blow-up.
- Committed.

**Hint.** The clearest demo is an *unreachable* target just past the workspace edge: the naive solver thrashes with huge steps while the damped solver settles to a bounded residual equal to "how far past reach the target is." That bounded residual is the honest answer.

**Estimated time.** 45 minutes.

---

## Problem 4 — Analytic vs. numerical IK comparison (headline deliverable)

**Problem statement.** This is the syllabus comparison. Take 1,000 random *reachable* poses for your arm (generate them by running FK on random joint vectors). For each, solve IK two ways: (a) MoveIt2's numerical plugin via `/compute_ik` (or your own DLS solver), and (b) the closed-form analytic IK for your arm — for the UR5e this is published; for the MyCobot use IKFast or the documented analytic solution. Compare on three axes: **solve time**, **success rate**, and **number of solutions returned**. Write it up as a one-page comparison.

**Acceptance criteria.**

- `notes/week-23/ik-comparison.md` (~one page) with a table: solve time (median + p99), success rate, and solutions-per-pose, for numerical vs. analytic.
- The analytic solver is shown to be orders of magnitude faster (µs vs ms) and to return *all* solution branches (up to 8) where the numerical solver returns one.
- A paragraph on *when* you'd choose each: numerical for a generic arm or one-off planning; analytic/IKFast for high-rate IK or when you need all branches (e.g. picking the collision-free one).
- The 1,000-pose set and the script that generates and solves them are committed.
- Committed.

**Hint.** Generating reachable poses by FK guarantees they're reachable, so a "failure" from the numerical solver is a *solver* limitation (seed, singularity), not an unreachable pose — which is exactly the comparison you want to surface. If deriving the UR analytic IK by hand is too much, use a published implementation (cite it) or IKFast; the point is comparing the *families*, not re-deriving the algebra.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Make MoveIt2 fail on purpose, name the code

**Problem statement.** Drive your arm with the Exercise 3 pose-goal node (or your mini-project service). Engineer one example of each of these failures and record the `error_code.val` and name MoveIt2 returns: (a) an unreachable pose (expect `NO_IK_SOLUTION`/`PLANNING_FAILED`), (b) a pose blocked by a collision object you add to the planning scene (expect `PLANNING_FAILED`), and (c) a wrong planning-group name (expect `INVALID_GROUP_NAME`). For each, state where you'd look to fix it.

**Acceptance criteria.**

- `notes/week-23/error-codes.md` records the three failures, each with the exact `error_code.val`, the name, and a one-line "where I'd look."
- The collision-object failure is reproduced by adding an object to the planning scene that blocks the only path — and removing it makes the plan succeed.
- You correctly distinguish a *planning* failure from a *control* failure (and explain you can't easily trigger `CONTROL_FAILED` in a clean sim — note that).
- Committed.

**Hint.** Add a collision object with the planning-scene interface (a box right in front of the goal). `INVALID_GROUP_NAME` is the easiest: pass `"not_a_group"` as the planning group. The exact integer for the no-IK case varies across MoveIt2 versions (-17 or -31); record what *yours* returns.

**Estimated time.** 50 minutes.

---

## Problem 6 — Reachable or not, before you plan

**Problem statement.** Write a fast pre-plan reachability check using your FK and the arm's max reach: given a target position, return `reachable` / `not reachable` *without* calling MoveIt2, by comparing the target's distance from the base to the arm's published reach (and, optionally, a manipulability floor). Validate it against MoveIt2's `/compute_ik` on 50 points inside and 50 outside the envelope.

**Acceptance criteria.**

- A `reachability_check.py` (or the mini-project's `reachability.py`) that returns a verdict in well under a millisecond, no MoveIt2 call.
- `notes/week-23/reachability-check.md` reports the agreement rate against `/compute_ik` for the 100 validation points and accounts for any disagreements (they should cluster at the boundary).
- You explain why a cheap local check before the expensive global plan is the right engineering — it saves OMPL from spending its whole time budget failing on an obviously-unreachable pose.
- Committed.

**Hint.** The crude check is `‖target - base‖ ≤ max_reach` (and `≥ min_reach` for arms with a dead zone near the base). It will disagree with `/compute_ik` near the boundary and for orientation-constrained poses — that's expected and worth noting. The mini-project uses exactly this to fail unreachable poses fast.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — FK three ways | 45 min |
| 2 — Find and measure a singularity | 40 min |
| 3 — DLS vs naive pseudoinverse | 45 min |
| 4 — Analytic vs numerical IK (headline) | 1 h 15 min |
| 5 — Make MoveIt2 fail, name the code | 50 min |
| 6 — Pre-plan reachability check | 35 min |
| **Total** | **~5 h 10 min** |

## Grading rubric

Each problem is scored out of 10:

- **Correctness (5)** — the numbers/behavior are right and verified against ground truth (`tf2`, `/compute_fk`, `/compute_ik`), not asserted.
- **Evidence (3)** — real command output, tables, or plots are committed, not just prose.
- **Insight (2)** — you explain *why*, not just *what* — the singularity family, the IK family trade, the where-to-look for a failure code.

A passing homework is **42/60**. The headline Problem 4 is double-weighted at the Phase 3 milestone: a clear, evidenced analytic-vs-numerical comparison is exactly the kind of judgement a manipulation engineer is hired for.

When you've finished all six, push your repo and make sure the `crunch_arm` [mini-project](./mini-project/README.md) is in the same workspace — Week 24 imports it. Then take the [quiz](./quiz.md) with your notes closed.
