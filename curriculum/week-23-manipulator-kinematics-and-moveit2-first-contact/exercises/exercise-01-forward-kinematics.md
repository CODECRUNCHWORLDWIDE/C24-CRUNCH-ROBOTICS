# Exercise 1 — Forward Kinematics by Hand

**Goal:** Build the forward kinematics of a UR5e from its URDF using the product-of-exponentials formulation, then *prove* it is correct by matching it, to numerical precision, against two independent ground truths: `tf2_echo` and MoveIt2's own `/compute_fk` service. You will train the single most important habit of the week — never trusting a kinematics computation you haven't checked against the robot's own answer.

**Estimated time:** 60 minutes. Guided.

---

## Setup

You need the UR5e description and MoveIt2 config (both free, see `resources.md`):

```bash
sudo apt install ros-jazzy-ur-description ros-jazzy-ur-moveit-config
```

Bring up the arm's state publisher and MoveIt2 (this also starts `/compute_fk`):

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur5e
```

In RViz you should see the UR5e and be able to drag the interactive marker and click **Plan**. If you can, MoveIt2 is up and `/compute_fk` exists. Confirm:

```bash
ros2 service list | grep compute_fk
# /compute_fk
```

**Fallback (no robot):** the UR5e screw axes and home configuration are published numbers (they're in the `ur_description` and in *Modern Robotics*' UR5 example). The math half of this exercise runs with NumPy alone; you only need the robot for the `tf2_echo` / `/compute_fk` cross-checks.

---

## Step 1 — Read the screw axes off the URDF

The product-of-exponentials FK needs two things (Lecture 1 §3.3): the **home configuration `M`** (the `base_link → tool0` transform with all joints at zero) and one **base-frame screw axis `S_i` per joint**. Both come from the URDF. For each revolute joint, the screw axis is `S = (ω, v)` where `ω` is the joint's rotation axis in the base frame at home, and `v = -ω × q` for a point `q` on the axis.

Read `M` straight from `tf2` at the zero configuration:

```bash
# With all joints at zero (the launch starts there), read the home pose:
ros2 run tf2_ros tf2_echo base_link tool0
# Record the translation and rotation. That is your M.
```

Write the screws and `M` into a small Python module. The UR5e values (in the base frame, home configuration) are well-documented; transcribe them carefully — a sign error in one `ω` is the classic bug:

```python
import numpy as np

# UR5e screw axes S_i = (wx, wy, wz, vx, vy, vz) in the BASE frame at home.
# Transcribe from the URDF joint axes/origins (or the Modern Robotics UR example),
# then VERIFY in Step 3 — do not trust this table until tf2 agrees with it.
UR5E_SCREWS = [
    # TODO 1: fill in the 6 screw axes from the UR5e URDF. Each is (w, v).
    # Hint: joint 1 rotates about base z, so w1 = (0, 0, 1), and v1 = -w1 x q1.
]

# Home configuration M = base_link -> tool0 with all joints at zero.
UR5E_M = np.array([
    # TODO 2: fill in the 4x4 home transform read from tf2_echo at zero config.
])
```

---

## Step 2 — Implement the PoE forward kinematics

Drop in the closed-form matrix exponential and the FK product from Lecture 1 §3 (this is real, complete code — type it, don't hand-wave it):

```python
def skew(w):
    return np.array([[0, -w[2], w[1]],
                     [w[2], 0, -w[0]],
                     [-w[1], w[0], 0]])

def exp_screw(S, theta):
    w, v = np.asarray(S[:3], float), np.asarray(S[3:], float)
    W = skew(w)
    R = np.eye(3) + np.sin(theta) * W + (1 - np.cos(theta)) * (W @ W)
    G = (np.eye(3) * theta
         + (1 - np.cos(theta)) * W
         + (theta - np.sin(theta)) * (W @ W))
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = G @ v
    return T

def fk_space(screws, M, thetas):
    T = np.eye(4)
    for S, th in zip(screws, thetas):
        T = T @ exp_screw(S, th)
    return T @ M
```

---

## Step 3 — Verify against `tf2`

Pick a non-trivial joint vector — not all zeros, so the test is meaningful:

```python
theta_test = np.array([0.3, -1.1, 1.4, -0.5, 0.9, 0.2])
T_mine = fk_space(UR5E_SCREWS, UR5E_M, theta_test)
print("my tool0 position:", T_mine[:3, 3])
```

Now command the same joint vector on the robot and read `tf2`:

```bash
# Publish the joint state (or use the MoveIt2 joint-jog panel to set it), then:
ros2 run tf2_ros tf2_echo base_link tool0
```

The translation `tf2` prints must match `T_mine[:3, 3]` to ~1e-4 m. If it doesn't, **a screw axis or `M` is wrong** — the most common culprits are a sign-flipped `ω`, a `v` computed with the wrong point `q`, or an `M` read at a non-zero config. Fix it until they agree. This is the lesson: you found the bug by checking against the robot's own FK, not by staring at the math.

---

## Step 4 — Verify against MoveIt2's `/compute_fk`

`tf2` and your code could *both* be wrong in the same way if your `M` came from `tf2`. So cross-check against MoveIt2's independent FK service:

```bash
ros2 service call /compute_fk moveit_msgs/srv/GetPositionFK \
  "{header: {frame_id: 'base_link'},
    fk_link_names: ['tool0'],
    robot_state: {joint_state: {
      name: ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint',
             'wrist_1_joint','wrist_2_joint','wrist_3_joint'],
      position: [0.3, -1.1, 1.4, -0.5, 0.9, 0.2]}}}"
```

The `pose_stamped` it returns must match `T_mine` in both position and orientation. Three independent computations — yours, `tf2`'s, and MoveIt2's — agreeing is proof. Two agreeing and one not tells you which one to fix.

---

## Step 5 — Compute and read the Jacobian

Add the space Jacobian from Lecture 1 §4.1 and report the singular values at `theta_test`:

```python
def adjoint(T):
    R, p = T[:3, :3], T[:3, 3]
    Ad = np.zeros((6, 6))
    Ad[:3, :3] = R
    Ad[3:, 3:] = R
    Ad[3:, :3] = skew(p) @ R
    return Ad

def space_jacobian(screws, thetas):
    n = len(screws)
    J = np.zeros((6, n))
    T = np.eye(4)
    for i in range(n):
        if i > 0:
            T = T @ exp_screw(screws[i - 1], thetas[i - 1])
        J[:, i] = adjoint(T) @ np.asarray(screws[i])
    return J

J = space_jacobian(UR5E_SCREWS, theta_test)
sv = np.linalg.svd(J, compute_uv=False)
print("singular values:", sv)
print("manipulability  :", np.sqrt(max(np.linalg.det(J @ J.T), 0.0)))
print("condition number:", sv[0] / sv[-1])
```

At a well-conditioned `theta_test` the smallest singular value should be comfortably above zero (order 0.1–1) and the condition number modest (single or low double digits). Now set `theta_test` to a stretched-out pose (e.g. elbow near zero) and re-run: watch the smallest singular value and the manipulability drop toward zero and the condition number climb. You have just *measured* a singularity.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] Your `fk_space(UR5E_SCREWS, UR5E_M, theta_test)` position matches `tf2_echo base_link tool0` to ~1e-4 m for a non-trivial `theta_test`.
- [ ] The same position and orientation match MoveIt2's `/compute_fk` result.
- [ ] You can state which input (a screw `ω`, a screw `v`, or `M`) you had to fix to make them agree — or explain how you got it right the first time.
- [ ] `space_jacobian` produces a 6×6 matrix whose singular values you can print, and you can identify a configuration where the smallest singular value drops toward zero.

---

## Stretch

- Implement the **body Jacobian** as well and confirm `J_body = Adjoint(inv(T_base_tool)) @ J_space`. Two frames, one Jacobian.
- Build a **DH table** for the UR5e (modified DH; the parameters are published) and write a second FK from it. Confirm it agrees with your PoE FK — and notice how much more bookkeeping DH took.
- Sweep `elbow_joint` from `-π` to `π` holding the others fixed, plot the manipulability `w(θ)` along the sweep, and mark the configuration where it dips to its minimum. That dip is the elbow singularity, plotted.

---

When this feels comfortable, move to [Exercise 2 — Damped-least-squares IK](exercise-02-damped-least-squares-ik.py).
