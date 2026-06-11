# Exercise 1 — Rotate a Vector Three Ways, By Hand

**Goal:** Take one vector and one rotation, and produce the rotated vector *three independent ways* — by a rotation matrix, by Rodrigues' axis-angle formula, and by the quaternion sandwich `q v q⁻¹` — on paper, then confirm all three agree in NumPy. You will build the single most important reflex of the week: **never trust one rotation computation; trust three that agree.**

**Estimated time:** 50 minutes. Guided.

---

## Setup

No ROS this exercise. You need Python with NumPy and SciPy:

```bash
pip install numpy scipy
```

The problem, fixed for everyone so you can check yourself:

> Rotate the vector **v = [1, 2, 0]ᵀ** by **θ = 120°** about the axis **k = [0, 0, 1]ᵀ** (the z-axis).

Do each part **on paper first**, then verify in NumPy. The paper work is the point; the code is the check.

---

## Step 1 — The rotation matrix way

Write `Rz(120°)`. With `cos 120° = −1/2` and `sin 120° = √3/2 ≈ 0.8660`:

```
          ⎡ −0.5     −0.8660    0 ⎤
Rz(120°) = ⎢  0.8660  −0.5       0 ⎥
          ⎣  0        0         1 ⎦
```

Compute `v' = Rz(120°) · [1, 2, 0]ᵀ` by hand. You should get:

```
v'_x = (−0.5)(1) + (−0.8660)(2) + 0  = −0.5 − 1.7320 = −2.2320
v'_y = ( 0.8660)(1) + (−0.5)(2) + 0  =  0.8660 − 1.0  = −0.1340
v'_z = 0
```

So `v' ≈ [−2.2320, −0.1340, 0]ᵀ`. Write it down. This is your ground truth.

Verify in NumPy:

```python
import numpy as np

c, s = np.cos(np.deg2rad(120)), np.sin(np.deg2rad(120))
Rz = np.array([[c, -s, 0],
               [s,  c, 0],
               [0,  0, 1]])
v = np.array([1.0, 2.0, 0.0])
print(np.round(Rz @ v, 4))     # [-2.232  -0.134   0.   ]
```

---

## Step 2 — The Rodrigues axis-angle way

Now ignore the matrix you just wrote and rebuild it from `(k, θ)` using Rodrigues:

```
R = I + sin θ · [k]× + (1 − cos θ) · [k]×²
```

For `k = [0,0,1]ᵀ`:

```
       ⎡ 0  −1   0 ⎤            ⎡ −1   0   0 ⎤
[k]× = ⎢ 1   0   0 ⎥   [k]×² =  ⎢  0  −1   0 ⎥
       ⎣ 0   0   0 ⎦            ⎣  0   0   0 ⎦
```

Plug in `sin θ = 0.8660`, `(1 − cos θ) = 1.5`:

```
R = I + 0.8660·[k]× + 1.5·[k]×²
```

Work the top-left 2×2: `1 + 1.5·(−1) = −0.5` on the diagonal, `0.8660·(−1) = −0.8660` and `0.8660·(1) = 0.8660` off-diagonal. You **reconstruct exactly `Rz(120°)`** — which it must, because Rodrigues about z *is* `Rz`. That's the check: your Rodrigues implementation reproduces the elementary rotation.

Verify in NumPy:

```python
def skew(k):
    return np.array([[0, -k[2], k[1]],
                     [k[2], 0, -k[0]],
                     [-k[1], k[0], 0]])

def rodrigues(k, theta):
    k = np.asarray(k, float)
    k = k / np.linalg.norm(k)      # ALWAYS normalize the axis
    K = skew(k)
    return np.eye(3) + np.sin(theta)*K + (1 - np.cos(theta)) * (K @ K)

R_rod = rodrigues([0, 0, 1], np.deg2rad(120))
print(np.round(R_rod @ v, 4))    # [-2.232  -0.134   0.   ]  same as Step 1
```

> **The single most common Rodrigues bug:** forgetting to normalize `k`. If `‖k‖ ≠ 1` the formula is wrong and `det R ≠ 1`. Normalize first, every time.

---

## Step 3 — The quaternion way

Build the unit quaternion for `(k, θ)` with the half-angle formula:

```
q = (cos(θ/2),  k · sin(θ/2))
```

With `θ = 120°`, `θ/2 = 60°`, `cos 60° = 0.5`, `sin 60° = 0.8660`, and `k = [0,0,1]`:

```
q = (0.5,  0, 0, 0.8660)        # (w, x, y, z)
```

Rotate `v` by forming the pure quaternion `p = (0, v) = (0, 1, 2, 0)` and computing `q · p · q⁻¹`, where `q⁻¹ = q* = (0.5, 0, 0, −0.8660)` (conjugate, since `q` is unit-norm). Doing the two Hamilton products by hand is tedious but instructive — do it once. You will land on the pure quaternion `(0, −2.2320, −0.1340, 0)`, i.e. `v' = [−2.2320, −0.1340, 0]ᵀ`. **Same answer, third independent method.**

Verify in NumPy against scipy:

```python
from scipy.spatial.transform import Rotation

# scipy wants (x, y, z, w)!  Our (w,x,y,z)=(0.5,0,0,0.866) -> (0,0,0.866,0.5)
q_xyzw = [0.0, 0.0, np.sin(np.deg2rad(60)), np.cos(np.deg2rad(60))]
v_quat = Rotation.from_quat(q_xyzw).apply(v)
print(np.round(v_quat, 4))      # [-2.232  -0.134   0.   ]
```

---

## Step 4 — Confirm all three agree

```python
print("matrix :", np.round(Rz @ v, 4))
print("rodrig :", np.round(R_rod @ v, 4))
print("quat   :", np.round(v_quat, 4))
assert np.allclose(Rz @ v, R_rod @ v, atol=1e-9)
assert np.allclose(Rz @ v, v_quat,  atol=1e-9)
print("ALL THREE AGREE")
```

When that prints `ALL THREE AGREE`, you have computed a rotation three ways from three different formulas and they match to machine precision. That agreement is what lets you *trust* rotation code — and what makes the day they *disagree* a clean, isolated bug hunt.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] You produced `v' ≈ [−2.2320, −0.1340, 0]ᵀ` **on paper** by the matrix method.
- [ ] Your hand Rodrigues reconstruction reproduced `Rz(120°)` and gave the same `v'`.
- [ ] Your quaternion `q = (0.5, 0, 0, 0.8660)` and the sandwich `q p q⁻¹` gave the same `v'`.
- [ ] The NumPy `assert np.allclose(...)` checks pass and print `ALL THREE AGREE`.
- [ ] You can state, in one sentence, why normalizing the axis `k` matters for Rodrigues.

---

## Stretch

- Repeat the whole exercise for a **non-trivial axis** like `k = [1, 1, 1]ᵀ / √3` and `θ = 90°`. Now the matrix isn't an elementary `Rz`, so the three-way agreement is a real test, not a tautology.
- Confirm `det(R) = +1` and `RᵀR = I` for your Rodrigues output with `np.linalg.det` and `R.T @ R`. A `det` of `−1` means you built a reflection (sign bug); a non-identity `RᵀR` means a normalization bug.
- Rotate `v` by `θ` and then by `−θ` and confirm you return to the original `v` exactly — the group inverse, verified numerically.

---

When this feels comfortable, move to [Exercise 2 — The quaternion toolkit](exercise-02-quaternion-toolkit.py).
