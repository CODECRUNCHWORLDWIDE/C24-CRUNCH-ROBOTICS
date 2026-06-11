# Mini-Project — `crunch_rotations`: Your Rotation Library and the Tumbling Pose

> Build a small, well-tested Python rotation library — `crunch_rotations` — that converts fluently among rotation matrix, quaternion, axis-angle, and Euler ZYX, every conversion verified against `scipy`. Then wrap it in a `crunch_pose` ROS2 package whose `tumbling_pose` node publishes a smoothly rotating `PoseStamped` at 50 Hz that you visualize in rviz2.

This is the artifact you will *reuse for the rest of the year*. Week 2 lifts it to SE(3) for tf2; Week 9 leans on it to integrate gyro data; every controller and estimator that touches orientation calls back to it. Build it carefully now, with tests, and you never write a swapped-sign quaternion bug again — because the test suite catches it the moment you do.

**Estimated time:** ~7.5 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** `crunch_rotations` becomes the rotation core of your **Week 2 SE(3)/tf2 work** and resurfaces in Week 9's IMU integration. The Week 8 architecture review checks that your math lives in one tested library, not copy-pasted across nodes. Build it well now; you'll defend it in seven weeks.

---

## What you will build

Two deliverables in one repo:

1. **`crunch_rotations`** — a pure-Python package (NumPy only, no ROS) that is the single source of truth for rotation math: conversions among matrix / quaternion / axis-angle / Euler ZYX, composition, inversion, and a normalized-by-construction guarantee. Every public function has a unit test that checks it against `scipy.spatial.transform.Rotation`.
2. **`crunch_pose`** — an `ament_python` ROS2 package whose `tumbling_pose` node uses `crunch_rotations` to publish a rotating `geometry_msgs/PoseStamped` at 50 Hz on `/tumbling_pose`, visualized in rviz2 with a saved layout.

By the end you have a public repo of ~300–400 lines (library + tests + node) that any future crunch package can `from crunch_rotations import quat_to_matrix` and trust.

---

## Why a library and not inline math

You could compute quaternions inline in every node. Don't. A tested library gives you:

- **Verification once.** Each conversion is proven against `scipy` in a test. When a node misbehaves, you *know* the rotation math is right and look elsewhere.
- **One convention.** `(w, x, y, z)` scalar-first everywhere inside, with explicit `to_ros()` / `from_ros()` adapters at the ROS boundary (where it's `(x, y, z, w)`). The convention trap is solved in one place.
- **Greppable reuse.** `from crunch_rotations import ...` is searchable across the workspace; forty inline `math.cos(theta/2)` calls are not, and one of them will have the wrong sign.

---

## Package layout

```
crunch_rotations_ws/
├── crunch_rotations/                 # pure-Python, no ROS
│   ├── pyproject.toml
│   ├── crunch_rotations/
│   │   ├── __init__.py
│   │   ├── quaternion.py             # quat_mul, conjugate, rotate, normalize
│   │   ├── conversions.py            # quat<->matrix<->axisangle<->euler
│   │   └── ros_adapters.py           # to_ros_quat / from_ros_quat (x,y,z,w order)
│   └── tests/
│       ├── test_quaternion.py        # ops vs scipy
│       └── test_conversions.py       # every conversion vs scipy, round-trips
└── crunch_pose/                      # ament_python ROS2 package
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/crunch_pose
    ├── crunch_pose/
    │   ├── __init__.py
    │   └── tumbling_pose.py          # the 50 Hz PoseStamped node
    └── rviz/
        └── tumbling.rviz             # saved rviz2 layout
```

---

## Deliverable 1 — `crunch_rotations` (the tested library)

The library must provide, at minimum:

**`quaternion.py`**
- `quat_mul(q1, q2)` — Hamilton product, `(w,x,y,z)`.
- `quat_conjugate(q)` — negate vector part.
- `quat_normalize(q)` — divide by norm; raise on zero.
- `quat_rotate(q, v)` — rotate a 3-vector by the sandwich `q (0,v) q⁻¹`.

**`conversions.py`**
- `axis_angle_to_quat(axis, theta)` and `quat_to_axis_angle(q)`.
- `quat_to_matrix(q)` and `matrix_to_quat(R)`.
- `euler_zyx_to_quat(roll, pitch, yaw)` and `quat_to_euler_zyx(q)` — with a documented note that the Euler path is for human display only (Lecture 1 §6).

**`ros_adapters.py`**
- `to_ros_quat(q)` — `(w,x,y,z)` → a `geometry_msgs/Quaternion`-shaped `(x,y,z,w)` tuple or message.
- `from_ros_quat(msg)` — the reverse.

Here is the spine of `quaternion.py` to start from; fill in the rest yourself:

```python
"""crunch_rotations.quaternion — quaternion ops in (w, x, y, z) scalar-first order.

Internal convention is ALWAYS (w, x, y, z). Convert at the ROS boundary only,
in ros_adapters.py.
"""
from __future__ import annotations

import numpy as np


def quat_normalize(q) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    n = np.linalg.norm(q)
    if n == 0.0:
        raise ValueError("cannot normalize a zero quaternion")
    return q / n


def quat_conjugate(q) -> np.ndarray:
    w, x, y, z = q
    return np.array([w, -x, -y, -z])


def quat_mul(q1, q2) -> np.ndarray:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def quat_rotate(q, v):
    """Rotate 3-vector v by unit quaternion q via q (0,v) q^-1."""
    q = quat_normalize(q)
    p = np.array([0.0, v[0], v[1], v[2]])
    out = quat_mul(quat_mul(q, p), quat_conjugate(q))
    return out[1:]
```

> **The convention discipline is graded.** Inside the library, everything is `(w, x, y, z)`. The *only* place `(x, y, z, w)` appears is `ros_adapters.py`. If `grep -rn "x, y, z, w\|xyzw" crunch_rotations/` finds the ROS order anywhere outside `ros_adapters.py`, you've leaked the convention and you'll create a bug.

### Tests (this is half the project)

`test_conversions.py` must, for each conversion, generate random rotations (`scipy.spatial.transform.Rotation.random`) and assert your function matches scipy to `atol=1e-8`, **handling the double cover** (compare a quaternion up to sign). It must also test **round-trips**: `matrix_to_quat(quat_to_matrix(q)) == ±q`, `quat_to_euler_zyx` then back equals the original rotation, etc. The round-trip tests catch sign and ordering bugs that a single-direction test can miss.

```python
import numpy as np
from scipy.spatial.transform import Rotation
from crunch_rotations.conversions import quat_to_matrix

def _eq_rot(q_a, q_b, atol=1e-8):
    """Equal up to the double-cover sign."""
    return np.allclose(q_a, q_b, atol=atol) or np.allclose(q_a, -q_b, atol=atol)

def test_quat_to_matrix_matches_scipy():
    rng = np.random.default_rng(0)
    for _ in range(50):
        r = Rotation.random(random_state=rng)
        x, y, z, w = r.as_quat()           # scipy is (x,y,z,w)
        q = [w, x, y, z]                    # our (w,x,y,z)
        assert np.allclose(quat_to_matrix(q), r.as_matrix(), atol=1e-8)
```

---

## Deliverable 2 — `crunch_pose` (the ROS2 node)

`tumbling_pose.py` is the Exercise 3 node, refactored to import from `crunch_rotations` instead of inlining `math.cos`. It must:

- Use `crunch_rotations.axis_angle_to_quat` to build the orientation and `crunch_rotations.ros_adapters.to_ros_quat` to set the message fields. **No `math.cos` / `math.sin` in the node** — the rotation math lives in the library.
- Publish `PoseStamped` at 50 Hz on `/tumbling_pose`, `frame_id="world"`, stamped at acquisition time.
- Be runnable as `ros2 run crunch_pose tumbling_pose` (declare the entry point in `setup.py`).
- Ship a saved rviz2 config (`rviz/tumbling.rviz`) with Fixed Frame `world` and a Pose display on `/tumbling_pose`, so a reviewer runs *one* command and sees the tumble.

Run it:

```bash
colcon build --symlink-install --packages-select crunch_pose
source install/setup.bash
ros2 run crunch_pose tumbling_pose &
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix crunch_pose)/share/crunch_pose/rviz/tumbling.rviz
```

The reviewer should see a smoothly tumbling triad. A *jerky* one means the quaternion isn't normalized or the convention leaked — exactly the bug the library's tests exist to prevent.

---

## Rules

- **You may** read the ROS2 docs, scipy docs, the lecture notes, and `tf_transformations` source.
- **You must not** call `scipy` or `tf_transformations` from the *library's runtime* code — scipy is allowed only in the **tests**, as the reference oracle. The library implements the math itself; that's the learning. (Using scipy in production is fine in real life; here we're building the muscle.)
- **You must not** let the `(x,y,z,w)` ROS order appear outside `ros_adapters.py`.
- Python 3.12 (Ubuntu 24.04 default), NumPy. `rclpy` on Jazzy for `crunch_pose`.
- All conversions tested against scipy with the double cover handled.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-01-crunch-rotations-<yourhandle>`.
- [ ] `crunch_rotations` implements all the functions listed in Deliverable 1, in `(w,x,y,z)` internally.
- [ ] `pytest crunch_rotations/tests` passes, with at least: one test per conversion vs. scipy, the double cover handled, and round-trip tests for matrix↔quat and euler↔quat.
- [ ] `grep -rn "x, y, z, w" crunch_rotations/crunch_rotations/` finds matches **only** in `ros_adapters.py`.
- [ ] `colcon build --packages-select crunch_pose` succeeds with no warnings.
- [ ] `ros2 run crunch_pose tumbling_pose` publishes ~50 Hz on `/tumbling_pose` (verify with `ros2 topic hz`).
- [ ] Opening the saved rviz2 layout shows a **smoothly** tumbling Pose (no snaps).
- [ ] The node contains **no** `math.cos`/`math.sin` — it imports from `crunch_rotations`.
- [ ] A `README.md` with the convention note, the run commands, and a one-line-each description of every public function.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Conversion correctness** | 25 | Every conversion matches scipy to `1e-8`; the double cover is handled; `Ry` signs correct; no off-by-convention. |
| **Convention discipline** | 15 | `(w,x,y,z)` internal everywhere; ROS order isolated to `ros_adapters.py`; the `grep` check is clean. |
| **Test quality** | 25 | One test per conversion vs. scipy; round-trip tests present; double cover handled in the asserts; `pytest` green. |
| **The node** | 20 | 50 Hz, stamped, framed, normalized; imports the library (no inline trig); runs as `ros2 run`. |
| **rviz2 visualization** | 10 | Saved layout; the tumble is smooth; one command brings it up. |
| **Docs & hygiene** | 5 | Clear README, convention documented, sensible commits, no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to import in Week 2. **70–89** works but has a convention leak or a thin test suite. **Below 70** means the library isn't actually trustworthy — fix the tests first, because everything downstream depends on this math being right.

---

## Stretch goals

- **SLERP.** Add `slerp(q0, q1, t)` to the library, test it against `scipy`'s `Slerp`, and make `tumbling_pose` *ease* between two keyframe orientations instead of spinning at constant rate. Confirm the path is a great-circle arc (constant angular speed) by plotting the per-step geodesic angle.
- **Euler-display node.** Add a tiny subscriber that consumes `/tumbling_pose` and logs the orientation as ZYX Euler degrees — the *correct* use of Euler (human display at the edge), demonstrating the discipline from Lecture 1 §6.
- **Property tests.** Add a hypothesis-style randomized test asserting `quat_rotate` preserves vector length (`‖q·v‖ == ‖v‖`) and that composition matches matrix multiplication for random pairs.
- **CI.** Add a GitHub Actions workflow that runs `pytest` on every push. A green check on a rotation library is a small but real portfolio signal.

---

## How this connects to the rest of C24

- **Week 2 (SE(3) + tf2)** wraps `crunch_rotations` with a translation to make full rigid-body transforms, and feeds tf2 broadcasters.
- **Week 9 (IMU integration)** integrates gyro angular velocity into orientation using your quaternion ops — `Ṙ = [ω]× R` becomes a quaternion update.
- **Week 8 (integration review)** grades whether your rotation math is centralized and tested. This mini-project is that centralization, built seven weeks early. Push it, keep the repo, import it in Week 2.

When you've finished, push the repo and take the [quiz](../quiz.md).
