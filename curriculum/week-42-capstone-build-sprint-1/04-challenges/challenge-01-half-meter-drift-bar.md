# Challenge 1 — The Half-Meter Drift Bar

**The capstone acceptance bar, three sprints early.** Demonstrate that your fused state estimate drifts **under 0.5 m over a 20-meter trajectory**, with a recorded run and a number you can defend in front of a panel.

**Estimated time:** ~2.5 hours (after the exercises are done).

**Path:** A or B — the bar is the same; the venue differs.

---

## The bar

> Over a 20-meter trajectory, the terminal error of the fused state estimate — the distance between where the estimate says the robot ended and where it actually ended — must be **less than 0.5 meters**.

This is the exact bar the Week 48 capstone is graded against. You are meeting it now, with six weeks of margin, on purpose. If you hit it this week, Weeks 43–47 are about telemetry, policy tuning, chaos survival, and polish — not about a stack that cannot localize. If you miss it this week, you have a measured gap and a plan instead of a panic in Week 47.

---

## What "demonstrate" means

A demonstration is a number plus an artifact. Three things, all committed to your capstone repo:

1. **A recorded run.** A `rosbag2` of the full 20-meter trajectory, including `/odometry/filtered` (the fused estimate) and the raw sensor topics. On Path A this is a real drive; on Path B it is a run in your hardened deployment over a 20-meter path through your sim world.
2. **A drift plot.** The fused path overlaid on the ground-truth path, with the terminal error annotated. On Path A, ground truth is the tape-and-chalk endpoint (and, ideally, a couple of intermediate taped waypoints). On Path B, ground truth is the simulator's true pose, which you have for free — log `/ground_truth/pose` from Gz and compare.
3. **A defensible number.** The terminal drift, in meters, with a PASS/FAIL against 0.5 m, in the `[capstone]` format. "About 40 cm" is not defensible; "0.41 m, here is the bag and the plot" is.

---

## Path A — on hardware

You already have the drive from Exercise 2. The challenge adds rigor:

- **Drive a richer path, not just out-and-back.** Out-and-back can hide heading drift (it cancels). Drive a closed rectangle (5 m × 5 m, twice around = 20 m) so the path stresses all four headings. Tape the four corners as ground-truth waypoints.
- **Measure intermediate error, not just terminal.** At each taped corner, log the fused pose and the tape distance. A run that ends at 0.4 m but passed through 1.2 m at corner 3 is telling you something the terminal number hides.
- **If you fail, attribute before you re-tune.** Run the Lecture 1 §6 sequence: `ros2 topic delay` for timestamps, the actuator step test for lag, the Allan deviation for sensor health. Re-tune against the *replayed bag*, not by re-driving.

## Path B — in the hardened deployment

You have the cold boot from Exercise 3. The challenge adds the drift measurement:

- **Drive the 20-meter path under the full stack inside your hardened deployment.** Same launch graph, same lifecycle ordering — the deployment under test must be the production one, not a hand-started dev graph.
- **Use the simulator's ground truth.** Gz publishes the true pose; subscribe to it and compute terminal drift directly. No tape measure needed, but the discipline is identical.
- **Harden the run, not just the boot.** The deployment must survive the whole 20 m without a node dropping. If the heartbeat goes DEGRADED mid-run, that is a failure even if the terminal number is good — log it and fix it.

---

## A drift-plot helper

This works for both paths: feed it the fused path and the ground-truth path (lists of (x, y)) and it produces the annotated plot and the terminal number.

```python
#!/usr/bin/env python3
"""drift_plot.py - overlay fused vs. ground-truth path; annotate terminal drift.

Path A: ground truth = your taped waypoints (interpolate a straight reference).
Path B: ground truth = /ground_truth/pose logged from the simulator.
"""
import sys
import math
import numpy as np
import matplotlib.pyplot as plt


def terminal_drift(fused_xy: np.ndarray, truth_xy: np.ndarray) -> float:
    """Distance between the final fused point and the final truth point."""
    return float(np.hypot(*(fused_xy[-1] - truth_xy[-1])))


def path_length(xy: np.ndarray) -> float:
    d = np.diff(xy, axis=0)
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def plot(fused_xy: np.ndarray, truth_xy: np.ndarray, out: str):
    drift = terminal_drift(fused_xy, truth_xy)
    dist = path_length(truth_xy)
    plt.figure(figsize=(7, 7))
    plt.plot(truth_xy[:, 0], truth_xy[:, 1], "k-", lw=2, label="ground truth")
    plt.plot(fused_xy[:, 0], fused_xy[:, 1], "C0--", lw=2, label="fused estimate")
    plt.plot(*fused_xy[-1], "C0o", ms=10)
    plt.plot(*truth_xy[-1], "ks", ms=10)
    # draw the terminal-error vector
    plt.annotate("", xy=tuple(fused_xy[-1]), xytext=tuple(truth_xy[-1]),
                 arrowprops=dict(arrowstyle="->", color="C3", lw=2))
    plt.title(f"Terminal drift = {drift:.3f} m over {dist:.1f} m  "
              f"({'PASS' if drift < 0.5 else 'FAIL'} < 0.5 m)")
    plt.xlabel("x (m)"); plt.ylabel("y (m)")
    plt.axis("equal"); plt.grid(True, ls=":"); plt.legend()
    plt.savefig(out, dpi=130)
    print(f"[capstone] path_length={dist:.2f} m terminal_drift={drift:.3f} m "
          f"{'PASS' if drift < 0.5 else 'FAIL'} (< 0.5 m)")
    print(f"wrote {out}")


if __name__ == "__main__":
    # Each file: two whitespace-separated columns, x and y, one point per line.
    fused = np.loadtxt(sys.argv[1])
    truth = np.loadtxt(sys.argv[2])
    plot(fused, truth, sys.argv[3] if len(sys.argv) > 3 else "drift.png")
```

---

## Acceptance criteria

- [ ] A `rosbag2` of the full 20-meter run is committed (or linked via Git LFS / a release asset if large).
- [ ] A drift plot (`drift.png`) overlays the fused path on ground truth with the terminal error annotated.
- [ ] The terminal drift is **under 0.5 m**, printed in the `[capstone]` format with PASS.
- [ ] The path is at least 20 m long (the plot's path-length annotation confirms it).
- [ ] Path A: at least two intermediate taped waypoints are measured and reported. Path B: the heartbeat stayed NOMINAL for the whole run.
- [ ] A two-paragraph note: what your drift was, and *why* — which of timestamp lag, actuator lag, sensor noise, or EKF tuning dominated. If you passed easily, say which margin you have; if you barely passed, say what you would fix first.

---

## If you cannot hit 0.5 m this week

That is *useful information*, not a failure of the week. Commit the run you have, with its real number, and write the note. The single most common cause of a 1–2 m drift on a stack that worked in sim is, in order:

1. **Timestamp lag** (Lecture 1 §4) — fix the stamps before anything else.
2. **`use_sim_time` left true** on one node — a five-minute fix.
3. **Untuned process noise** for measured bias instability — re-tune against the replayed bag.
4. **Actuator lag** not accounted for in the controller — measure it, then decide if it is worth modelling.

You have Weeks 43–47 to close the gap. The engineers who pass Week 48 are the ones who measured the gap honestly in Week 42 and worked it down deliberately — not the ones who declared victory on a number they never recorded.
