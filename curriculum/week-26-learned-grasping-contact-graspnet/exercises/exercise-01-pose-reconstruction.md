# Exercise 1 — Reconstruct a Grasp Pose From Raw Network Outputs

**Goal:** Take the four raw quantities Contact-GraspNet predicts per point — a contact point, an approach direction, a baseline direction, and a width — and assemble the full `4x4 SE(3)` gripper transform in the correct gripper-frame convention. Then *prove* it is a valid rotation and that the gripper, placed at that pose, actually straddles the contact point. This is the single most error-prone step in the whole pipeline, and the bug (a non-orthonormal `R`, or a sign-flipped offset) is invisible until the arm goes to the wrong place.

**Estimated time:** 45 minutes. Guided.

---

## Setup

You need PyTorch and (for the visual check) Open3D. No GPU required.

```bash
source /opt/ros/jazzy/setup.bash
python3 -c "import torch, open3d; print('ok')"
```

If Open3D isn't installed: `pip install open3d`. The numeric checks work without it; only the rviz2/Open3D overlay needs it.

---

## Step 1 — The reconstruction function

Create `reconstruct.py`. Fill in the two TODOs. The math is in Lecture 1 §3; do not copy it blindly — derive the axis assignment from the convention (z = approach, x = baseline, y = z × x).

```python
import torch


def reconstruct_grasp_pose(contact, approach, baseline, width):
    """Assemble one 4x4 gripper transform from Contact-GraspNet outputs.

    Convention: gripper origin = grasp center (midway between fingers).
                +z = approach (forward into the grasp)
                +x = baseline (the finger-closing axis)
                +y = z cross x  (right-handed)
    Args:
        contact:  (3,) the observed contact point, camera frame.
        approach: (3,) unit approach vector.
        baseline: (3,) unit baseline vector (should be ⟂ approach).
        width:    scalar grasp width in meters.
    Returns:
        (4, 4) homogeneous transform.
    """
    z = approach / approach.norm()
    # TODO 1: Gram-Schmidt orthogonalize `baseline` against z, then normalize -> x.
    #         (Subtract the component of baseline along z, then normalize.)
    x = ...
    y = torch.cross(z, x, dim=0)

    R = torch.stack([x, y, z], dim=1)         # columns are the axes

    # TODO 2: the grasp center is half a width along x from the contact point
    #         (the contact is on one finger; the center is between the fingers).
    center = ...

    T = torch.eye(4)
    T[:3, :3] = R
    T[:3, 3] = center
    return T
```

---

## Step 2 — Prove the rotation is valid

A `4x4` that *looks* like a transform but whose `R` is not orthonormal will be silently mangled when you convert it to a quaternion for `geometry_msgs/Pose`. Assert it:

```python
import torch
from reconstruct import reconstruct_grasp_pose

contact  = torch.tensor([0.30, 0.05, 0.50])
approach = torch.tensor([0.0, 0.0, 1.0])      # straight down the camera +z
baseline = torch.tensor([1.0, 0.2, 0.0])      # NOT yet orthogonal to approach
width    = torch.tensor(0.06)

T = reconstruct_grasp_pose(contact, approach, baseline, width)
R = T[:3, :3]

# A valid rotation: R^T R = I and det(R) = +1.
I_err = (R.T @ R - torch.eye(3)).abs().max().item()
det = torch.det(R).item()
print(f"max |R^T R - I| = {I_err:.2e}   det(R) = {det:+.4f}")
assert I_err < 1e-5, "R is not orthonormal — did you orthogonalize the baseline?"
assert abs(det - 1.0) < 1e-5, "det(R) != +1 — your axis order is left-handed."
print("rotation OK")
```

If `I_err` is large, you skipped the Gram–Schmidt step (TODO 1). If `det(R) = -1`, your axis order is left-handed — re-check `y = z × x` vs `x × z`.

---

## Step 3 — Prove the offset is correct

The grasp center must sit *off* the contact point by half a width along the baseline. Check the geometry directly:

```python
center = T[:3, 3]
offset = center - contact
along_x = (offset @ R[:, 0]).item()          # component along the gripper x-axis
print(f"offset along baseline = {along_x:.4f} m (expected {0.5 * width.item():.4f})")
assert abs(along_x - 0.5 * width.item()) < 1e-5, "contact-to-center offset is wrong"
print("offset OK")
```

A sign-flipped offset (center on the wrong side of the contact) passes the rotation check but fails this one. If `along_x` is negative, flip the sign of your offset in TODO 2.

---

## Step 4 — Visual sanity check (Open3D)

Render the contact point, the grasp center, and a simple gripper made of two finger lines so you can *see* that the gripper straddles the object:

```python
import numpy as np
import open3d as o3d

R = T[:3, :3].numpy()
c = T[:3, 3].numpy()
half_w = 0.5 * width.item()
x_axis = R[:, 0]                              # baseline (finger spread direction)
z_axis = R[:, 2]                              # approach

finger_len = 0.04
f1 = c + half_w * x_axis                      # right finger base
f2 = c - half_w * x_axis                      # left finger base
f1_tip = f1 + finger_len * z_axis
f2_tip = f2 + finger_len * z_axis

pts = np.array([c, contact.numpy(), f1, f2, f1_tip, f2_tip])
lines = [[2, 3], [2, 4], [3, 5]]             # palm + two fingers
ls = o3d.geometry.LineSet(
    o3d.utility.Vector3dVector(pts),
    o3d.utility.Vector2iVector(lines))
spheres = o3d.geometry.TriangleMesh.create_sphere(radius=0.004).translate(contact.numpy())
o3d.visualization.draw_geometries([ls, spheres])
```

You should see the contact point sitting **between** the two finger tips, with the fingers opening to roughly the grasp width. If the contact point is *outside* the fingers, your offset sign is still wrong.

---

## Step 5 — Batch it

Real inference returns hundreds of grasps at once. Generalize your function to operate on `(N, 3)` inputs without a Python loop (vectorize the cross products and the `stack`). Confirm the batched version matches the single-grasp version on the test case above. (The batched form is exactly what the inference node in Exercise 2 imports.)

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `reconstruct_grasp_pose` produces an `R` with `max|R^T R - I| < 1e-5` and `det(R) = +1` on the Step 2 test.
- [ ] The contact-to-center offset is `+0.5 * width` along the baseline (Step 3 passes).
- [ ] The Open3D render shows the contact point *between* the gripper fingers.
- [ ] A batched `(N,3) -> (N,4,4)` version exists and matches the single-grasp version.
- [ ] You can state, in one sentence, why skipping the Gram–Schmidt orthogonalization breaks the quaternion conversion downstream.

---

## Stretch

- Convert your `R` to a quaternion (the week-1 routine) and back, and confirm it round-trips to within `1e-6`. A non-orthonormal `R` will *not* round-trip — this is the failure the assertion in Step 2 prevents.
- Add the second contact point. Contact-GraspNet predicts one contact; the *other* finger's contact is implied by the width along the baseline. Compute it and render both contacts.
- Take a real grasp from the Exercise 2 output and render it on top of the actual object cloud. Eyeball whether the gripper would collide with the table — a preview of the collision-filtering stretch goal.

---

When this feels comfortable, move to [Exercise 2 — Grasp inference and ranking](exercise-02-grasp-inference.py).
