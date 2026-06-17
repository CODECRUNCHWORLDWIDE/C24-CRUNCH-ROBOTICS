# Week 6 Homework

Five practice problems that revisit the week's kinematics, integration, drift, and odometry-publishing topics. The full set should take about **6 hours**. Work in your Week 6 Git repository so each problem produces at least one commit you can point to at the Week 8 architecture review.

Each problem includes:

- A short **problem statement**.
- **Deliverables** — the artifacts you commit.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

The grading rubric is at the bottom. Like the mini-project, **every drift claim must carry a number** — "my odometry is good" is not a deliverable; "closure error 0.43 m over 40 m, 1.07% of path" is.

---

## Problem 1 — Derive and verify the bicycle-model odometry

**Problem statement.** Lecture 2 gave you the diff-drive forward kinematics and a NumPy verification of its Jacobian. Do the same for the **kinematic bicycle model**. Write `homework/p1_bicycle/bicycle_odom.py` that:

1. Implements `bicycle_twist(vx, delta, wheelbase) -> (vx, omega)` using `ω = (vₓ/ℓ)·tan δ` (Lecture 2, §2.5).
2. Integrates a fixed `(vₓ, δ)` over a chosen duration with the **exact-arc integrator** and reports the final pose.
3. Confirms two physical facts numerically and prints them: (a) at `δ = 0` the path is a straight line (`y` and `θ` stay zero); (b) a bicycle **cannot spin in place** — set `vₓ = 0` with any nonzero `δ` and show `ω = 0`.
4. Sweeps `δ ∈ {5°, 15°, 30°}` at fixed `vₓ` and prints the turning radius `R = ℓ/tan δ` for each, confirming tighter steering gives a smaller radius.

**Deliverables.** `homework/p1_bicycle/bicycle_odom.py` and its printed output captured in `homework/p1_bicycle/output.txt`.

**Acceptance criteria.**

- The script runs under `python3 bicycle_odom.py` with only NumPy.
- The `δ = 0` case integrates a straight line along `+x` (final `y < 1e-9`, final `θ < 1e-9`).
- The `vₓ = 0` case prints `ω = 0` regardless of `δ`.
- The printed radii match `ℓ/tan δ` to three decimal places.
- Committed.

**Hint.** Reuse the `integrate` function structure from Lecture 1's `drift_budget.py`. The only change from diff-drive is *how you compute `ω`*: instead of `r(φ̇_R−φ̇_L)/L`, it is `(vₓ/ℓ)·tan δ`. The integration is identical because both reduce to the unicycle (Lecture 2, §2.2).

**Estimated time.** 45 minutes.

---

## Problem 2 — Euler vs exact-arc: measure the integration error

**Problem statement.** Lecture 2, §2.9 claimed the Euler integrator's error scales like `vₓ·ω·Δt²` and "only shows up at low rates and high turn rates." Prove it. Write `homework/p2_integrators/compare_integrators.py` that drives a **full circle** (constant `vₓ`, constant `ω`, for exactly `2π/ω` seconds) with both the Euler and the exact-arc integrator, at three loop rates — **50 Hz, 10 Hz, and 2 Hz** — and reports, for each rate, the closure error (distance from the start pose) of each integrator.

A perfect integrator closes the circle exactly (closure error → 0). The exact-arc integrator should close to near machine-zero at every rate; the Euler integrator's closure error should *grow as the rate drops*.

**Deliverables.** `homework/p2_integrators/compare_integrators.py`, a results table `homework/p2_integrators/results.md` with the six closure numbers, and a one-paragraph interpretation.

**Acceptance criteria.**

- The script runs with only NumPy.
- The exact-arc closure error is `< 1e-6 m` at all three rates.
- The Euler closure error is visibly larger and **increases monotonically** as the rate drops (50 → 10 → 2 Hz).
- `results.md` states which integrator you would ship and why, in one paragraph that references §2.9.
- Committed.

**Hint.** Both integrators are in the lectures: Euler is the three-line rectangular scheme in §2.9 Scheme 1; exact-arc is Scheme 2 with the `|ω| > ε` guard. Drive `vₓ = 0.5`, `ω = 1.0`; the circle radius is `0.5 m` and it should close in `2π` seconds. Make `dt = 1/rate` and `steps = round((2π/ω)/dt)`.

**Estimated time.** 1 hour.

---

## Problem 3 — Fix a broken odometry node

**Problem statement.** The file `homework/p3_broken/broken_odom.py` (you create it from the listing below) contains an `rclpy` odometry node with **three deliberate bugs** that together make the robot drive backward and in the wrong rotational sense, and desync the EKF. Find all three, fix them, and write a one-line comment at each fix naming the bug. The bugs are drawn from the three most common Week 6 review-fails.

Start from this listing (type it in; do not skip the comments — they are part of the bug):

```python
#!/usr/bin/env python3
"""Week 6 homework P3 — a diff-drive odometry node with three bugs. Fix them."""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster


def yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class BrokenOdom(Node):
    def __init__(self):
        super().__init__("broken_odom")
        self.r, self.L = 0.05, 0.30
        self.x = self.y = self.th = 0.0
        self.last = None
        self.pub = self.create_publisher(Odometry, "/odom", 10)
        self.tf = TransformBroadcaster(self)
        self.create_subscription(JointState, "/joint_states", self.cb, 10)

    def cb(self, msg: JointState):
        li, ri = msg.name.index("left_wheel_joint"), msg.name.index("right_wheel_joint")
        t = rclpy.time.Time.from_msg(msg.header.stamp)
        if self.last is None:
            self.last = t
            return
        dt = (t - self.last).nanoseconds * 1e-9
        self.last = t
        wl, wr = msg.velocity[li], msg.velocity[ri]
        # BUG-prone kinematics + integration below
        vx = self.r * (wl + wr) / 2.0
        w = self.r * (wl - wr) / self.L            # (1)
        self.x += vx * math.cos(self.th) * dt      # (2)
        self.y += vx * math.sin(self.th) * dt
        self.th += w * dt
        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()   # (3)
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = yaw_to_quaternion(self.th)
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = w
        self.pub.publish(odom)
        tf = TransformStamped()
        tf.header.stamp = odom.header.stamp
        tf.header.frame_id = "odom"
        tf.child_frame_id = "base_link"
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.rotation = yaw_to_quaternion(self.th)
        self.tf.sendTransform(tf)


def main():
    rclpy.init()
    rclpy.spin(BrokenOdom())


if __name__ == "__main__":
    main()
```

The three bugs, for grading reference (do not read until you have tried — but they are the deliverable, so they appear in the rubric):

1. **Sign error in the yaw rate** at marker `(1)`: it is `(wr − wl)`, not `(wl − wr)`. With the wrong sign the robot rotates the wrong way and the heading drifts in the wrong direction — exactly the failure mode the comment at the end of Exercise 2 warns about.
2. **Euler integrator** at marker `(2)`: it uses the cheap rectangular scheme instead of the exact-arc integrator (Lecture 2, §2.9). On a square at modest loop rate this injects visible cross-track error.
3. **`now()` timestamp** at marker `(3)`: the message is stamped with the *wall clock*, not the `/joint_states` header stamp. The Week 10 EKF synchronizes inputs by stamp; this desyncs the filter (mini-project "Why this compounds", point 3).

**Deliverables.** `homework/p3_broken/fixed_odom.py` with all three fixes and a one-line `# FIX:` comment at each.

**Acceptance criteria.**

- All three bugs are fixed.
- Each fix carries a `# FIX:` comment naming the bug class.
- The node still runs under `rclpy` (sourced Jazzy) without exceptions.
- A `homework/p3_broken/notes.md` explains, in three sentences, the *symptom* each bug produces (wrong rotation, cross-track drift, EKF desync).
- Committed.

**Hint.** Cross-check each marked line against Exercise 2's `exercise-02-odom-and-tf-publisher.py`, which is correct. The diff is three lines.

**Estimated time.** 1 hour.

---

## Problem 4 — A drift-vs-speed measurement table

**Problem statement.** Using your Exercise 3 / mini-project square-driver and the Week 3 robot in Gz Sim, drive the 10×10 m square at **three speeds** (0.25, 0.5, 1.0 m/s) and produce a table of closure error vs speed. This is the controlled experiment behind Lecture 1's claim that *systematic* error is speed-independent while *slip* (non-systematic) grows with speed.

For each speed, record: commanded speed, total path length (perimeter = 40 m), closure error (m), drift as a fraction of path length (%), and the final heading error (degrees). Plot closure error against speed with matplotlib and save the figure.

**Deliverables.**

- `homework/p4_drift/drift_table.md` — the five-column table for the three speeds.
- `homework/p4_drift/drift_vs_speed.png` — closure error vs speed plot.
- `homework/p4_drift/runs/` — the three CSV logs (odom vs ground truth) that back the table.

**Acceptance criteria.**

- Three runs at the three speeds, each logged to CSV.
- The table reports closure error and drift-% for all three.
- The plot renders closure error vs speed with axis labels and units.
- A one-paragraph interpretation states whether your drift grew with speed and what that implies about the slip vs systematic split (Lecture 1, §1.8).
- Committed.

**Hint.** Reuse the square-driver from Exercise 3; it already logs odom and ground truth. If your Gz Sim has near-zero slip you may see almost flat drift-vs-speed — that is itself a finding: it means the simulator's systematic error dominates, and you should say so. To *see* slip grow, increase the commanded turn rate or lower the wheel-ground friction in the world file.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — The covariance defense memo

**Problem statement.** The single most common review-fail on a student odometry node is a dishonest covariance block (Lecture 1, §1.7 and §1.10; mini-project submission note). Write a **one-page memo**, `homework/p5_covariance/covariance.md`, that defends the exact `pose.covariance` and `twist.covariance` diagonals your mini-project node publishes, as if presenting to the Week 8 reviewer who will hand your `/odom` to the Week 10 EKF.

The memo must address, in its own short section each:

1. **Why yaw variance is larger than x/y variance.** Tie it to §1.3 (heading error dominates).
2. **Why the unmeasured DOFs (`z`, `roll`, `pitch`, `vy`, `vz`) are set to `1e6`.** Explain the "ignore this" convention and what happens if you instead set them small.
3. **Why no fused diagonal is zero.** Explain the singular-matrix / NaN failure (§1.10, failure mode 2).
4. **What breaks downstream if you "lie small"** — set everything to `0.001` (§1.10, failure mode 1) — and why the EKF then follows the drift.
5. **The one number you are least sure of**, and how you would measure it properly (the velocity-proportional model from §1.7, fit from the challenge's slip data).

**Deliverables.** `homework/p5_covariance/covariance.md`, with the actual 6-float diagonals from your `config/odometry.yaml` quoted at the top.

**Acceptance criteria.**

- All five sections present, each in its own paragraph or subsection.
- The quoted diagonals match your mini-project's `config/odometry.yaml`.
- The memo names the two EKF failure modes (lying small, zero on a fused diagonal) explicitly.
- 350–600 words.
- Committed.

**Hint.** This is the memo you will half-recite at the Week 8 review when the reviewer points at your covariance block and says "defend these numbers." Write it now while the lecture is fresh; future-you at Week 10 will thank present-you.

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 | 45 min |
| 2 | 1 h 0 min |
| 3 | 1 h 0 min |
| 4 | 1 h 15 min |
| 5 | 45 min |
| **Total** | **~4 h 45 min** |

(The remaining time in the 6-hour budget is reading the UMBmark paper and the REPs you cite.)

---

## Rubric

Graded out of 100. The bar is *honest numbers*, not perfect odometry.

| Criterion | Weight | What full marks looks like |
|---|---:|---|
| **P1 — Bicycle kinematics** | 15% | `ω = (vₓ/ℓ)tan δ` correct; straight-line and no-spin-in-place facts demonstrated numerically; radii match `ℓ/tan δ`. |
| **P2 — Integrator comparison** | 20% | Exact-arc closes to `<1e-6` at all rates; Euler error grows monotonically as rate drops; ship-recommendation cites §2.9. |
| **P3 — Bug fix** | 20% | All three bugs fixed with named `# FIX:` comments; `notes.md` correctly states each symptom. |
| **P4 — Drift table** | 25% | Three real runs with CSVs; table reports closure and drift-%; plot rendered; interpretation distinguishes systematic from slip. |
| **P5 — Covariance memo** | 20% | All five sections; quoted diagonals match the node; both EKF failure modes named; 350–600 words. |

**Pass:** 75/100, with **no problem scoring zero** (every problem must have a committed, runnable, or written deliverable). A drift table with no CSVs, or a covariance memo that does not name the EKF failure modes, fails that problem.

When you've finished all five, push your repo and make sure the mini-project's `CALIBRATION.md` and this homework's `p5_covariance/covariance.md` tell the *same* story about your covariance — a reviewer who finds them contradicting will ask which one you actually believe.
