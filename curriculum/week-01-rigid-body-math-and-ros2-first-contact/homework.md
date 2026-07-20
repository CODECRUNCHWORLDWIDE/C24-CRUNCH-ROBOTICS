# Week 1 Homework

Six problems that revisit the week's topics and force the rotation math into your fingers. The full set should take about **5 hours**. Work in your Week 1 Git repository (the same workspace as the exercises and the `crunch_rotations` mini-project) so every problem produces at least one commit you can point to at the Phase 1 architecture review in Week 8.

The headline deliverable is **Problem 4 — the rotation-conversion library write-up**, which documents and demonstrates that your `crunch_rotations` conversions are correct against an independent reference.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

For the ROS problems, source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`) and your overlay if you've built one. The pure-math problems need only NumPy + SciPy.

---

## Problem 1 — Verify your install and capture the proof

**Problem statement.** Install ROS2 Jazzy (if you haven't) and prove it works end to end. Run `ros2 doctor`, then the `demo_nodes_cpp talker` / `demo_nodes_py listener` pair in two terminals. Capture the output showing the listener receiving the talker's messages, and capture `ros2 doctor` reporting all checks passed.

**Acceptance criteria.**

- `notes/week-01/install-proof.md` contains the `ros2 doctor` summary line and a few lines of `listener` output showing `I heard: Hello World: N`.
- You note your platform (native 24.04 / WSL2 / container / VM) and `ros2 --version`.
- Committed.

**Hint.** If the talker/listener don't talk, it's almost always (a) one terminal unsourced, or (b) a `ROS_DOMAIN_ID` mismatch. Source `/opt/ros/jazzy/setup.bash` in *both* and leave `ROS_DOMAIN_ID` unset (defaults to 0) in both.

**Estimated time.** 30 minutes (longer if installing from scratch).

---

## Problem 2 — The rotation cheat-sheet, derived not copied

**Problem statement.** By hand (paper or LaTeX), derive and write out the three elementary rotation matrices `Rx(α)`, `Ry(β)`, `Rz(γ)`, paying explicit attention to the `Ry` sign pattern. Then derive `Rz(γ)` a *second* way from Rodrigues' formula with `k = [0,0,1]ᵀ` and confirm the two match. Record it in `notes/week-01/rotation-cheatsheet.md`.

**Acceptance criteria.**

- All three elementary matrices written correctly, with the `Ry` `−sin` in the top-right.
- A short derivation showing Rodrigues with `k=[0,0,1]` reproduces `Rz(γ)` exactly.
- One sentence explaining why `Ry`'s sign pattern differs from `Rx`/`Rz` (right-hand-rule consistency).
- Committed.

**Hint.** The `Ry` sign isn't a convention you can flip — it falls out of the right-hand rule applied to the y-axis. Check it: `Ry(90°)` must send `+z → +x` (`[0,0,1]ᵀ → [1,0,0]ᵀ`). If yours sends `+z → −x`, your signs are flipped.

**Estimated time.** 40 minutes.

---

## Problem 3 — Composition order, demonstrated

**Problem statement.** Pick two non-parallel rotations (e.g. `Ra = Rz(90°)`, `Rb = Rx(90°)`). In NumPy, compute `Ra @ Rb` and `Rb @ Ra` and show they differ. Then take a test vector and show `(Ra @ Rb) @ v ≠ (Rb @ Ra) @ v`. Finally, do the same with quaternions (`quat_mul(qa, qb)` vs `quat_mul(qb, qa)`) and confirm the quaternion result agrees with the corresponding matrix result.

**Acceptance criteria.**

- `notes/week-01/composition-order.md` shows the two different products, the two different rotated vectors, and the matching quaternion result.
- A one-paragraph physical explanation (the "rotate a book two ways" intuition) of *why* order matters.
- Committed.

**Hint.** Convert your quaternion composition back to a matrix with `quat_to_matrix` and `np.allclose` it against the matrix product — up to the double-cover sign on the quaternion itself, but the *matrix* should match exactly. If they don't, you have a Hamilton-product sign bug.

**Estimated time.** 40 minutes.

---

## Problem 4 — The rotation-conversion library write-up (headline deliverable)

**Problem statement.** Document and demonstrate that your `crunch_rotations` library's conversions are correct. Write `notes/week-01/conversions-validated.md` that, for each conversion (quat↔matrix, axis-angle↔quat, euler↔quat), shows: the function signature, a worked example with numbers, and the `pytest` line (or output) proving it matches `scipy` to `1e-8` with the double cover handled. Include a round-trip demonstration (`matrix_to_quat(quat_to_matrix(q)) == ±q`).

**Acceptance criteria.**

- `notes/week-01/conversions-validated.md` covers every conversion with a numeric example and a reference to its passing test.
- The double-cover handling is explicitly shown (a comparison that allows `±q`).
- At least one round-trip is demonstrated with numbers.
- `pytest crunch_rotations/tests` is green and the write-up quotes the summary line.
- Committed.

**Hint.** The strongest evidence is a `pytest -v` run pasted in, showing each conversion test passing. If a test fails for *some* random rotations but not others, you almost certainly forgot the double cover in a *quaternion* comparison (the matrix comparison doesn't need it). See Lecture 1 §5.2.

**Estimated time.** 1 hour.

---

## Problem 5 — Stamp and frame discipline on your publisher

**Problem statement.** Extend your `tumbling_pose` node (or Exercise 3) to *also* publish a second `PoseStamped` on `/tumbling_pose_lagged` whose stamp is set *after* a deliberate `time.sleep(0.04)` (simulating 40 ms of "processing"). Echo both topics with `ros2 topic echo --field header.stamp` and show the lagged one's stamps trail the correct one's by ~40 ms. Write up why this matters for a moving robot.

**Acceptance criteria.**

- `notes/week-01/stamp-discipline.md` shows the two stamp streams and the ~40 ms offset.
- A short paragraph computing the position error this would inject on a robot moving at 1 m/s (≈4 cm) and why it compounds downstream.
- Committed.

**Hint.** Don't actually `sleep` inside a 50 Hz timer callback in production — it blocks the executor. For this demonstration it's fine because the point is to *show the bad pattern*. Note in your write-up that the real fix is "stamp at acquisition, carry the stamp through processing."

**Estimated time.** 45 minutes.

---

## Problem 6 — Read a rotation off a live topic

**Problem statement.** Write a tiny `rclpy` subscriber that consumes `/tumbling_pose`, converts the incoming `geometry_msgs/Quaternion` to a rotation matrix and to ZYX Euler degrees using your `crunch_rotations` library (via `from_ros_quat`), and logs the axis-angle and the Euler readout once per second. This exercises the *correct* use of Euler — human-readable display at the edge — and the ROS↔library convention adapter.

**Acceptance criteria.**

- A subscriber node that prints, once per second, the current rotation as axis-angle and as ZYX Euler degrees.
- The conversion uses `crunch_rotations` (not inline math, not scipy at runtime), through `from_ros_quat`.
- `notes/week-01/live-readout.md` captures a few seconds of output and a one-line note that this is the *only* sanctioned use of Euler (display, at the edge).
- Committed.

**Hint.** `from_ros_quat` must map the message's `(x,y,z,w)` to your library's `(w,x,y,z)` — this is exactly the convention adapter you wrote in the mini-project. If your Euler readout looks rotated about the wrong axis, suspect a swapped scalar in the adapter.

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Verify install | 30 min |
| 2 — Rotation cheat-sheet | 40 min |
| 3 — Composition order | 40 min |
| 4 — Conversion write-up (headline) | 1 h 0 min |
| 5 — Stamp & frame discipline | 45 min |
| 6 — Live rotation readout | 45 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_rotations` [mini-project](./mini-project/README.md) is in the same workspace — Week 2 imports it. Then take the [quiz](./quiz.md) with your notes closed.
