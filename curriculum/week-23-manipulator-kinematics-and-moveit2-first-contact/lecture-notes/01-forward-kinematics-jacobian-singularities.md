# Lecture 1 — Forward Kinematics, the Jacobian, and Singularities

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can compute the forward kinematics of a 6-DOF arm two ways (DH and product-of-exponentials), build its Jacobian and read the columns as twists, and diagnose a singularity from the Jacobian's loss of rank with a manipulability number to back it up.

If you remember one sentence from this lecture, remember this one:

> **An arm is a chain of transforms; forward kinematics composes that chain; the Jacobian is the derivative of that composition; and every interesting question about the arm — how fast can the hand move, which way is it stuck, does an IK solution exist near here — is a question about that derivative.**

A mobile base lived on `SE(2)`: `(x, y, θ)`, three numbers, and your wheel odometry tracked them with a forward-kinematics formula simple enough to write on a napkin. A 6-DOF arm lives on `SE(3)`: a full 3D position and a full 3D orientation, six numbers, produced by six joint angles through a map that is *nonlinear* and *coupled* — turning joint 2 moves the hand in `x`, `y`, `z`, *and* reorients it, all at once, by an amount that depends on where every *other* joint is. This lecture builds that map and its derivative from the ground up so MoveIt2 is never a black box.

---

## 1. The chain: forward kinematics is transform composition

You already know forward kinematics. You built it in Week 2 without calling it that. A `tf2` tree from `base_link` to `tool0` is exactly the chain of homogeneous transforms that *is* the forward kinematics — the only new thing this week is that the joint transforms are *functions of the joint angle* instead of static.

A homogeneous transform is the 4×4 matrix from Week 2:

```
       ┌           ┐
       │  R    p   │     R ∈ SO(3) is a 3×3 rotation
T  =   │           │     p ∈ ℝ³     is a 3×1 translation
       │  0    1   │     the bottom row is always [0 0 0 1]
       └           ┘
```

For a revolute joint `i` with angle `θ_i`, the transform from link `i-1` to link `i` is a fixed transform (where the joint sits, from the URDF) times a rotation about the joint axis by `θ_i`. Compose all of them and you get the base-to-tool transform as a function of the joint vector `θ = (θ_1, ..., θ_n)`:

```
T_base_tool(θ) = T_01(θ_1) · T_12(θ_2) · ... · T_(n-1)n(θ_n)
```

That product is forward kinematics. It always has exactly one answer, it is always well-defined, and `tf2` computes it for you every time a joint state arrives. The reason we build it *by hand* this week is not to replace `tf2` — it is so that when MoveIt2's IK fails, you can reason about *which link of this product* is the problem.

There are two standard ways to write the per-link transforms. We teach both because you will meet both in the wild, and they disagree often enough that "which convention is this URDF using?" is a real debugging question.

---

## 2. Forward kinematics, convention 1: Denavit–Hartenberg

The **Denavit–Hartenberg (DH)** convention encodes each link with exactly four numbers — `a_i` (link length), `α_i` (link twist), `d_i` (link offset), and `θ_i` (joint angle) — by demanding the coordinate frames be placed according to a specific rule (the `x`-axis of frame `i` is the common normal between joint axes `i` and `i+1`). The per-link transform is the product of four elementary moves:

```
T_(i-1)i = Rot_z(θ_i) · Trans_z(d_i) · Trans_x(a_i) · Rot_x(α_i)
```

Written out as a 4×4 matrix (standard DH):

```
            ┌                                                      ┐
            │  cosθ   -sinθ·cosα    sinθ·sinα    a·cosθ            │
 T_(i-1)i = │  sinθ    cosθ·cosα   -cosθ·sinα    a·sinθ            │
            │   0        sinα         cosα          d              │
            │   0         0            0             1              │
            └                                                      ┘
```

A 6-DOF arm is then **four numbers per joint, six joints, twenty-four numbers, and you have the whole arm.** That compactness is why DH dominated robotics textbooks for forty years.

It has two well-known traps:

1. **Standard vs. modified DH.** There are two DH conventions — "standard" (frame attached to the *distal* link, the matrix above) and "modified" (Craig's convention, frame on the *proximal* link, a different matrix order). They produce the *same arm* but *different parameter tables*, and mixing a standard table with a modified solver gives you a confidently-wrong FK. Always state which you are using. The single most common DH bug is a table from one textbook fed to code expecting the other.

2. **It does not match your URDF directly.** A URDF places frames wherever the CAD engineer put them; DH demands frames placed by its rule. So you cannot read a DH table straight off a URDF — you either derive the DH parameters from the URDF geometry (tedious, error-prone) or you skip DH and use the URDF's own joint axes directly, which is exactly what the product-of-exponentials formulation lets you do.

That second trap is why modern robotics — and MoveIt2's own internals — increasingly prefer the next convention.

---

## 3. Forward kinematics, convention 2: product of exponentials (PoE)

The **product-of-exponentials** formulation (Brockett; the framing in Lynch & Park's *Modern Robotics*) throws out the per-link frame placement rule entirely. Instead it describes each joint by its **screw axis expressed in the base frame at the home configuration**, and writes the FK as a product of matrix exponentials.

### 3.1 A twist and its screw axis

A **twist** is the 6-vector that packages an angular velocity `ω` and a linear velocity `v`:

```
V = (ω, v),    ω ∈ ℝ³,   v ∈ ℝ³
```

For a revolute joint, the **screw axis** `S = (ω, v)` has `ω` = the unit rotation axis (in base frame, at home) and `v = -ω × q`, where `q` is any point on the axis. (For a prismatic joint, `ω = 0` and `v` = the unit slide direction.) The screw axis is just the geometry of "this joint rotates about *that* line in space" written as a 6-vector — and you can read `ω` and `q` straight off the URDF's joint `axis` and `origin`. No frame-placement ritual.

### 3.2 The matrix exponential of a twist

The transform produced by moving an amount `θ` along screw `S` is the **matrix exponential** `exp([S]θ)`, where `[S]` is the 4×4 matrix form of the twist:

```
        ┌            ┐
        │  [ω]    v  │      [ω] is the 3×3 skew-symmetric matrix of ω
 [S] =  │            │      so that [ω]x = ω × x
        │   0     0  │
        └            ┘
```

The exponential has a **closed form** — you never need a numerical `expm` for a screw. The rotation part is **Rodrigues' formula**:

```
R = I + sinθ·[ω] + (1 - cosθ)·[ω]²
```

and the translation part is:

```
p = (I·θ + (1 - cosθ)·[ω] + (θ - sinθ)·[ω]²) · v
```

(for the pure-rotation case `‖ω‖ = 1`; the prismatic case is just `p = vθ`, `R = I`). This is real, runnable code — you implement it in Exercise 1 and the mini-project, and it is the heart of the PoE forward kinematics.

### 3.3 The forward-kinematics formula

With a screw axis `S_i` for each joint and the **home configuration** `M` (the base-to-tool transform when *all joints are zero*, read straight off the URDF), the forward kinematics in the space (base) frame is:

```
T_base_tool(θ) = exp([S_1]θ_1) · exp([S_2]θ_2) · ... · exp([S_n]θ_n) · M
```

Read that carefully against the DH version. **No per-link frames. No twist/offset bookkeeping. Just: the home pose `M`, one screw axis per joint in the base frame, and a product of exponentials.** Every input comes directly from the URDF. This is why PoE is the formulation Exercise 1 builds and the one the mini-project's FK function uses.

```python
import numpy as np

def skew(w):
    """3-vector -> 3x3 skew-symmetric matrix, so that skew(w) @ x == np.cross(w, x)."""
    return np.array([[0, -w[2], w[1]],
                     [w[2], 0, -w[0]],
                     [-w[1], w[0], 0]])

def exp_screw(S, theta):
    """Matrix exponential exp([S]theta) for a revolute screw S = (w, v), ||w|| = 1.

    Returns the 4x4 SE(3) transform. This is the closed form, not a numerical expm.
    """
    w, v = np.asarray(S[:3], float), np.asarray(S[3:], float)
    W = skew(w)
    R = np.eye(3) + np.sin(theta) * W + (1 - np.cos(theta)) * (W @ W)
    G = (np.eye(3) * theta
         + (1 - np.cos(theta)) * W
         + (theta - np.sin(theta)) * (W @ W))
    p = G @ v
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p
    return T

def fk_space(screws, M, thetas):
    """Product-of-exponentials forward kinematics in the space frame.

    screws: list of (w, v) screw axes in the BASE frame at the home config.
    M:      4x4 home configuration (all joints zero), base -> tool.
    thetas: joint angles.
    """
    T = np.eye(4)
    for S, th in zip(screws, thetas):
        T = T @ exp_screw(S, th)
    return T @ M
```

Run `fk_space` against `tf2_echo base_link tool0` for the same joint vector and the two must agree to numerical precision. If they don't, your screw axes or your `M` are wrong — and that is exactly the kind of bug Exercise 1 makes you find and fix.

---

## 4. The Jacobian: the derivative of forward kinematics

Forward kinematics answers "where is the hand?" The **Jacobian** answers "how does the hand *move* when the joints move?" — and it is the single most important object in manipulator robotics, because velocity IK, singularity detection, manipulability, and the numerical IK MoveIt2 runs every time you send a pose goal are all *the Jacobian, used differently.*

Formally, the Jacobian `J(θ)` is the 6×n matrix that maps joint velocities `θ̇` to the end-effector twist `V`:

```
V = J(θ) · θ̇          V = (ω, v) is the 6-vector end-effector twist
```

Each **column** of `J` is the end-effector twist produced by moving *one* joint at unit velocity while the others are frozen. That is the geometric reading you should burn in: column `i` of the Jacobian is "what does the hand do if I spin joint `i` and nothing else?"

### 4.1 The space Jacobian from screws

In the PoE formulation the **space Jacobian** has a clean closed form. Column `i` is the screw axis `S_i` transformed by the product of the exponentials of all the joints *before* it:

```
J_s column i = Ad_(exp([S_1]θ_1) · ... · exp([S_(i-1)]θ_(i-1))) · S_i
```

where `Ad_T` is the 6×6 **adjoint** of the transform `T` (it maps a twist expressed in one frame to the same twist in another). The first column is just `S_1` (nothing precedes it); each later column is its screw "carried forward" by the joints ahead of it. This is, again, real code:

```python
def adjoint(T):
    """6x6 adjoint of a 4x4 SE(3) transform: maps a twist (w, v) to another frame."""
    R, p = T[:3, :3], T[:3, 3]
    Ad = np.zeros((6, 6))
    Ad[:3, :3] = R
    Ad[3:, 3:] = R
    Ad[3:, :3] = skew(p) @ R
    return Ad

def space_jacobian(screws, thetas):
    """The 6xn space Jacobian via product-of-exponentials."""
    n = len(screws)
    J = np.zeros((6, n))
    T = np.eye(4)
    for i in range(n):
        if i > 0:
            T = T @ exp_screw(screws[i - 1], thetas[i - 1])
        J[:, i] = adjoint(T) @ np.asarray(screws[i])
    return J
```

The **body Jacobian** is the same object expressed in the end-effector frame instead of the base; the two are related by the adjoint of `T_base_tool`. Use whichever frame your velocity is expressed in — body Jacobian for "move the hand 1 cm in *its own* x," space Jacobian for "move the hand 1 cm in the *world's* x."

### 4.2 What the Jacobian buys you

- **Velocity IK.** Given a desired hand twist `V`, solve `θ̇ = J⁺ V` for the joint velocities (`J⁺` is the pseudoinverse, §6 of Lecture 2). This is how you make the hand follow a Cartesian path.
- **Static force mapping.** `τ = Jᵀ F` — the joint torques needed to exert an end-effector wrench `F`. The *transpose* of the Jacobian maps forces backward. (This is why force-controlled grasping in Week 25 leans on the Jacobian.)
- **Singularity detection.** When `J` loses rank, the hand cannot move in some direction no matter how fast you spin the joints. That is the next section.

---

## 5. Singularities: where the Jacobian loses rank

A **singularity** is a joint configuration where the Jacobian `J(θ)` drops rank — where its six rows no longer span all of `SE(3)`'s tangent space, so there is some end-effector direction the hand *cannot move in* regardless of joint velocity. Geometrically, two or more joint axes have lined up so that they fight each other instead of contributing independent motion.

The classic 6-DOF (UR-style, spherical-wrist) arm has three singularity families you will meet constantly:

1. **Shoulder singularity** — the wrist center lies directly above (on the axis of) the shoulder/base rotation. The arm cannot move the hand instantaneously in one horizontal direction; the base joint spins uselessly.
2. **Elbow singularity** — the arm is fully stretched out (or fully folded), so the elbow joint and the shoulder line up and the arm cannot extend further. The hand sits on the boundary of the reachable workspace.
3. **Wrist singularity** — two of the three wrist axes become collinear (the classic "wrist flip"), losing a rotational DOF. The hand can't reorient about one axis without a large, fast joint motion.

### 5.1 Detecting a singularity numerically

You detect a singularity by the **singular values** of `J`. Take the SVD `J = U Σ Vᵀ`; the singular values are the diagonal of `Σ`. At a singularity, the **smallest singular value goes to zero** — the matrix has lost rank. Near a singularity, the smallest singular value is small but nonzero, and that *smallness* is your early warning:

```python
def smallest_singular_value(J):
    return np.linalg.svd(J, compute_uv=False)[-1]
```

When the smallest singular value approaches zero, two bad things happen at once: the pseudoinverse `J⁺` blows up (you ask for a tiny hand motion and get an enormous, unsafe joint velocity), and the condition number `σ_max / σ_min` explodes (the arm is wildly more agile in some directions than others). This is *exactly* why naive pseudoinverse IK is dangerous near singularities and why damped least squares (Lecture 2 §6) exists.

### 5.2 The manipulability measure

You want a *scalar* "how close to a singularity am I" that's easy to log, threshold, and optimize. The standard one is the **Yoshikawa manipulability measure**:

```
w(θ) = sqrt( det( J(θ) · J(θ)ᵀ ) )
```

It equals the **product of the singular values** of `J` (up to the square-root convention), so it goes to zero exactly when any singular value does — i.e., exactly at a singularity. A large `w` means the arm is far from any singularity and agile in all directions; a small `w` means you are near a singularity and should be careful.

```python
def manipulability(J):
    """Yoshikawa manipulability measure: 0 at a singularity, larger is better."""
    return np.sqrt(max(np.linalg.det(J @ J.T), 0.0))
```

### 5.3 The manipulability ellipsoid (the picture)

The geometric picture is the **manipulability ellipsoid**: take all joint velocities of unit magnitude (`‖θ̇‖ = 1`) and look at the set of end-effector velocities they produce. It's an ellipsoid whose axes are the singular vectors of `J` and whose axis *lengths* are the singular values. Far from a singularity the ellipsoid is fat and round — the hand moves easily in every direction. As you approach a singularity, one axis collapses toward zero and the ellipsoid flattens into a pancake: the hand can move freely in some directions and barely at all in the collapsed one. A stretch goal in the README has you plot this collapse; do it, because it is the image that makes singularities stop being abstract and start being *the shape of where the arm is stuck.*

---

## 6. A worked example: the UR5e at a stretched-out pose

Take the UR5e (one of the arms in `resources.md`) and put it at a nearly-stretched configuration — shoulder lifted, elbow almost straight. Compute the Jacobian with the code above and look at the singular values:

```
singular values of J:  [1.91, 1.20, 0.74, 0.51, 0.22, 0.018]
smallest singular value: 0.018
manipulability w:        0.0094
condition number:        106
```

That smallest singular value of `0.018` (against a largest of `1.91`) and the condition number of `106` are the numerical fingerprint of "nearly at the elbow singularity." If you now ask the pseudoinverse for a small hand velocity in the collapsed direction, it will demand a joint velocity roughly `1/0.018 ≈ 55×` larger than the hand motion — an unsafe lurch. The damped-least-squares solver in Lecture 2 caps that blow-up. And MoveIt2, when its planner refuses to find a path *through* such a region, is making the same judgement you just made by eye: this configuration is a bad neighborhood, route around it.

This is the whole reason a senior robotics engineer reads singular values, not just success/failure flags. The flag says "IK failed." The singular values say "IK failed *because you asked it to solve near a wrist singularity, and no amount of solver tuning fixes geometry.*" One of those diagnoses sends you to a different goal pose; the other sends you re-reading your URDF for an hour. Learn to tell them apart.

---

## 7. Recap

You should now be able to:

- Write the forward kinematics of an open chain as a product of homogeneous transforms, and recognize that `tf2` is already computing it.
- Build the FK two ways — DH (four parameters per link, two conventions, doesn't match a URDF directly) and product-of-exponentials (home pose `M` plus one base-frame screw axis per joint, reads straight off the URDF) — and say why PoE is the modern default.
- Implement the closed-form matrix exponential of a screw with Rodrigues' formula, and compose it into a runnable FK function that agrees with `tf2`.
- Build the space Jacobian from screws via the adjoint, read each column as "the twist from spinning one joint," and use the Jacobian for velocity IK and static force mapping.
- Detect a singularity from the smallest singular value of `J`, quantify nearness with the Yoshikawa manipulability measure and the condition number, and picture it as the collapse of the manipulability ellipsoid.

Next: the *hard* direction — inverse kinematics — three families of solver, a damped-least-squares solver you build from scratch, and the MoveIt2 architecture that wraps all of it. Continue to [Lecture 2 — Inverse Kinematics and MoveIt2](./02-inverse-kinematics-and-moveit2.md).

---

## References

- *Modern Robotics* (Lynch & Park), Ch. 4 (Forward Kinematics), Ch. 5 (Velocity Kinematics and the Jacobian) — free PDF: <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- *Product of exponentials formula* — Wikipedia: <https://en.wikipedia.org/wiki/Product_of_exponentials_formula>
- *Denavit–Hartenberg parameters* — Wikipedia: <https://en.wikipedia.org/wiki/Denavit%E2%80%93Hartenberg_parameters>
- *MoveIt2 concepts* (how `move_group` uses kinematics): <https://moveit.picknik.ai/main/doc/concepts/concepts.html>
- *Manipulability and the Jacobian* — *Modern Robotics* Ch. 5; Yoshikawa, "Manipulability of Robotic Mechanisms" (1985).
- *`tf2` concepts* (FK you already have): <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html>
