# Exercise 1 — Bound the Action Space

**Type:** Guided (Markdown deliverable + a small code artifact). **Estimated time:** 60 minutes.

**Goal:** Define the *constraint set* for your robot — the explicit bounds that the safety filter checks every learned action against — and implement the **correct** trajectory clamp (uniform time-rescaling) so a coordinated motion's shape is preserved when its speed is reduced. You will prove, on a curved path, that uniform rescaling preserves the path while per-channel saturation warps it. This constraint set is the input to every other artifact this week.

The deliverable is a committed `action_bounds.py` (the constraint set + the clamps) and a one-page `notes/constraint-set.md` documenting the bounds and *why* each one is what it is.

---

## Step 0 — Why this is the first thing you build

The safety filter (Exercise 2) is only as good as the constraint set it checks against. A filter with no bounds passes everything (the too-loose-filter defect). A filter with bounds set wrong either clamps constantly (too tight) or never (too loose). So before you write a line of filter logic, you write down — explicitly, with units, with a reason for each number — what your robot is and is not allowed to do. This is the same discipline as MPC constraint formulation (Week 22), applied to a learned action.

You are bounding four things:

1. **Velocity** — the base twist and the arm joint/Cartesian velocities.
2. **Acceleration / jerk** — the *change* between consecutive actions.
3. **Joint limits** — the commanded joint positions, with a margin.
4. **Workspace** — the end-effector operating volume and any keep-out zones.

---

## Step 1 — Write down the velocity bounds, with reasons

Create `notes/constraint-set.md`. For your robot, fill in a table like this with *real* numbers from your robot's spec (URDF limits, the room you operate in, the datasheet). Every number needs a one-line reason.

| Quantity | Bound | Reason |
|---|---|---|
| Base linear velocity | 1.0 m/s | Shared indoor space; a person can react to ≤ 1 m/s; the capstone room is small. |
| Base angular velocity | 1.5 rad/s | Avoids tipping the diff-drive base; matches the Nav2 controller limit. |
| Arm Cartesian velocity | 0.10 m/step (≈ 0.25 m/s at 40 Hz) | Smooth grasp approach; matches the demo collection speed. |
| Arm joint velocity (each) | from URDF `velocity` limit, × 0.8 margin | 80% of the hardware limit leaves headroom for the controller. |

> The *reason* column is what you defend at the midterm. A bound with no reason is a bound the panel will question. "1 m/s because a person can react to it" is defensible; "1 m/s because that seemed fine" is not.

---

## Step 2 — Implement the constraint set in code

Create `action_bounds.py`. The constraint set is data; the checks are functions over it.

```python
"""action_bounds.py — the explicit constraint set for the crunchbot, and the
correct (shape-preserving) clamps. Imported by the safety filter."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Bounds:
    """The robot's action and state constraints. Numbers from the URDF, the
    datasheet, and the operating room — every one has a reason in
    notes/constraint-set.md."""
    v_max: float = 1.0            # base linear velocity, m/s
    w_max: float = 1.5            # base angular velocity, rad/s
    a_max: float = 1.0            # base linear acceleration, m/s^2
    cart_step_max: float = 0.10   # arm Cartesian step, m per control step
    # Per-joint position limits (rad) and velocity limits (rad/s); 6-DOF arm.
    q_min: tuple = (-3.14, -2.30, -2.60, -3.14, -2.00, -3.14)
    q_max: tuple = (3.14, 2.30, 2.60, 3.14, 2.00, 3.14)
    qdot_max: tuple = (2.0, 2.0, 3.0, 3.0, 3.0, 3.0)
    # End-effector workspace volume (m), in base_link.
    ws_x: tuple = (0.15, 0.85)
    ws_y: tuple = (-0.60, 0.60)
    ws_z: tuple = (0.02, 1.10)    # z_min = 0.02 is just above the table surface


def clamp_twist_preserving_shape(vx: float, wz: float, b: Bounds) -> tuple[float, float, bool]:
    """Uniformly rescale a base twist so neither component exceeds its limit,
    preserving the path SHAPE (same curvature). Returns (vx, wz, was_clamped)."""
    f = max(abs(vx) / b.v_max, abs(wz) / b.w_max, 1.0)
    return vx / f, wz / f, (f > 1.0)


def clamp_joint_velocities(qdot: list[float], b: Bounds) -> tuple[list[float], bool]:
    """Uniformly rescale a joint-velocity vector so no joint exceeds its limit
    and ALL joints stay synchronized (same time-scaling). The correct clamp
    for coordinated arm motion."""
    f = max(max(abs(q) / qmax for q, qmax in zip(qdot, b.qdot_max)), 1.0)
    return [q / f for q in qdot], (f > 1.0)


def joint_positions_in_limits(q: list[float], b: Bounds, margin: float = 0.05) -> bool:
    """True iff every commanded joint angle is inside [q_min+margin, q_max-margin]."""
    return all(qmn + margin <= qi <= qmx - margin
               for qi, qmn, qmx in zip(q, b.q_min, b.q_max))


def ee_in_workspace(x: float, y: float, z: float, b: Bounds) -> bool:
    """True iff the end-effector position is inside the operating volume."""
    return (b.ws_x[0] <= x <= b.ws_x[1]
            and b.ws_y[0] <= y <= b.ws_y[1]
            and b.ws_z[0] <= z <= b.ws_z[1])


# The WRONG clamp — included so you can prove it warps the path. Do not use it
# for coordinated motion; it is here as the cautionary counterexample.
def clamp_twist_per_channel_WRONG(vx: float, wz: float, b: Bounds) -> tuple[float, float]:
    """Per-channel saturation. Changes the curvature when only one channel
    is over-limit. The bug Lecture 1 §4 warns against."""
    return max(min(vx, b.v_max), -b.v_max), max(min(wz, b.w_max), -b.w_max)
```

---

## Step 3 — Prove uniform rescaling preserves the path, saturation warps it

Add this driver to the bottom of `action_bounds.py` (or a separate `prove_clamp.py`) and run it:

```python
def _prove() -> None:
    """A curved motion (forward + turning) that's over the linear limit but
    within the angular limit. Show that uniform rescale keeps the curvature
    (ratio vx/wz) and per-channel saturation breaks it."""
    b = Bounds()
    vx, wz = 2.0, 1.0      # vx is 2x over v_max=1.0; wz is within w_max=1.5
    ratio_in = vx / wz     # the curvature signature: 2.0

    vx_u, wz_u, clamped = clamp_twist_preserving_shape(vx, wz, b)
    ratio_uniform = vx_u / wz_u

    vx_s, wz_s = clamp_twist_per_channel_WRONG(vx, wz, b)
    ratio_sat = vx_s / wz_s

    print(f"input          : vx={vx:.2f} wz={wz:.2f}  curvature ratio={ratio_in:.3f}")
    print(f"uniform rescale: vx={vx_u:.2f} wz={wz_u:.2f}  ratio={ratio_uniform:.3f}  "
          f"(clamped={clamped}) -> PATH PRESERVED")
    print(f"per-channel sat: vx={vx_s:.2f} wz={wz_s:.2f}  ratio={ratio_sat:.3f}  "
          f"-> PATH WARPED")
    assert math.isclose(ratio_uniform, ratio_in, rel_tol=1e-6), "uniform must preserve ratio"
    assert not math.isclose(ratio_sat, ratio_in, rel_tol=1e-6), "saturation must change ratio"
    print("PASS: uniform rescaling preserves curvature; saturation does not.")


if __name__ == "__main__":
    _prove()
```

Run it:

```bash
python3 action_bounds.py
```

Expected output:

```
input          : vx=2.00 wz=1.00  curvature ratio=2.000
uniform rescale: vx=1.00 wz=0.50  ratio=2.000  (clamped=True) -> PATH PRESERVED
per-channel sat: vx=1.00 wz=1.00  ratio=1.000  -> PATH WARPED
PASS: uniform rescaling preserves curvature; saturation does not.
```

Read it: the input wants twice the linear speed it's allowed while turning. Uniform rescaling halves *both* channels, so the curvature ratio (`vx/wz = 2.0`) is unchanged — the robot drives the same arc, slower. Per-channel saturation caps only `vx`, leaving `wz`, so the ratio collapses to `1.0` — the robot now turns twice as sharply as the policy intended, and may clip an obstacle the policy was steering around. That is the bug Lecture 1 §4 warns about, demonstrated in eight lines.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `notes/constraint-set.md` has the velocity, acceleration, joint-limit, and workspace bounds for *your* robot, each with a one-line reason, using real numbers from your URDF / datasheet / operating room.
- [ ] `action_bounds.py` defines the `Bounds` dataclass and the four check/clamp functions, plus the cautionary per-channel `_WRONG` function.
- [ ] Running `python3 action_bounds.py` prints the proof and asserts that uniform rescaling preserves the curvature ratio and saturation breaks it.
- [ ] You can state, in one sentence, *why* per-channel saturation is wrong for a coordinated motion (it changes the relative scaling of the channels, warping the path/trajectory shape).
- [ ] Committed.

---

## Stretch

- Add an **acceleration clamp**: given the previous action and the current one, bound the delta to `a_max · dt` and rescale uniformly if exceeded. Prove it limits jerk on a step input.
- Add a **keep-out volume** (a sphere around a point in `base_link`) to the workspace check, and a function `ee_clear_of_keepout(x, y, z, center, radius)`. This is the seed of the dynamic keep-out around a detected person.
- Plot (in PlotJuggler or matplotlib) the *actual paths* the uniform-rescale and saturation clamps produce by integrating the twist over 3 seconds. The two arcs diverge visibly — that picture is the strongest argument for uniform rescaling.

---

When this feels comfortable, move to [Exercise 2 — The runtime safety filter](./exercise-02-runtime-safety-filter.py).
