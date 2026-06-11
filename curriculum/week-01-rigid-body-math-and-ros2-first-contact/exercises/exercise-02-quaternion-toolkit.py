#!/usr/bin/env python3
# Exercise 2 — The quaternion toolkit (implement it, then prove it against scipy)
#
# Goal: Implement the core quaternion operations from scratch — multiply, conjugate,
#       rotate-a-vector, quaternion<->matrix, and axis-angle->quaternion — and verify
#       EVERY one against scipy.spatial.transform.Rotation. When your hand math agrees
#       with the reference, you trust it; the day it disagrees, you have an isolated bug.
#
# Estimated time: 60 minutes. Runnable.
#
# CONVENTION (write it on a sticky note):
#   This file stores quaternions as (w, x, y, z)  -- scalar first.
#   scipy.spatial.transform.Rotation uses (x, y, z, w) -- scalar LAST.
#   The helpers _to_scipy / _from_scipy convert between them. A swapped scalar
#   component is the single most common bug in this exercise.
#
# HOW TO USE THIS FILE
#
#   Standalone. No ROS, no colcon. Just NumPy + SciPy:
#
#       pip install numpy scipy
#       python3 exercise-02-quaternion-toolkit.py
#
#   Fill in the five functions marked "# TODO". The test harness at the bottom
#   checks each against scipy and prints PASS/FAIL per function, then an overall
#   verdict and exit code (0 = all pass, 1 = something failed).
#
# ACCEPTANCE CRITERIA
#
#   [ ] All five functions implemented; the harness prints "ALL CHECKS PASSED" and
#       exits 0.
#   [ ] quat_mul is non-commutative: q1*q2 != q2*q1 for non-parallel rotations
#       (the harness checks this explicitly).
#   [ ] quat_to_matrix output is orthonormal with det +1 (the harness checks this).
#   [ ] You can explain why axis_angle_to_quat uses the HALF angle.
#
# Expected output is at the bottom of the file.

import math
import sys

import numpy as np
from scipy.spatial.transform import Rotation


# --------------------------------------------------------------------------- #
# Convention helpers: our (w,x,y,z) <-> scipy (x,y,z,w)
# --------------------------------------------------------------------------- #
def _to_scipy(q):
    """(w,x,y,z) -> scipy's (x,y,z,w)."""
    w, x, y, z = q
    return [x, y, z, w]


def _from_scipy(q_xyzw):
    """scipy's (x,y,z,w) -> our (w,x,y,z)."""
    x, y, z, w = q_xyzw
    return np.array([w, x, y, z])


# --------------------------------------------------------------------------- #
# The toolkit — implement these.
# --------------------------------------------------------------------------- #
def quat_conjugate(q):
    """Conjugate of (w,x,y,z): negate the vector part -> (w,-x,-y,-z).

    For a UNIT quaternion the conjugate equals the inverse.
    """
    # TODO 1: return the conjugate.
    raise NotImplementedError


def quat_mul(q1, q2):
    """Hamilton product q1 * q2, both (w,x,y,z). Non-commutative.

    w = w1*w2 - v1.v2
    v = w1*v2 + w2*v1 + v1 x v2
    """
    # TODO 2: implement the Hamilton product. (numpy.cross helps for v1 x v2.)
    raise NotImplementedError


def quat_rotate(q, v):
    """Rotate 3-vector v by the rotation that unit quaternion q encodes.

    Embed v as the pure quaternion (0, v), then compute q * (0,v) * q^-1, and
    return the vector part. q^-1 == quat_conjugate(q) for a unit q.
    """
    # TODO 3: implement the sandwich product and return the 3-vector part.
    raise NotImplementedError


def axis_angle_to_quat(axis, theta):
    """Unit quaternion (w,x,y,z) for a rotation of theta (rad) about `axis`.

    q = (cos(theta/2),  k*sin(theta/2)),  k = axis/||axis||.
    The HALF angle is why a 360-deg rotation gives q=(-1,0,0,0), not (1,0,0,0).
    """
    # TODO 4: normalize the axis, apply the half-angle formula, return (w,x,y,z).
    raise NotImplementedError


def quat_to_matrix(q):
    """3x3 rotation matrix for unit quaternion (w,x,y,z).

    Use the standard closed form (Lecture 1 5.5). Transcribe carefully, then the
    harness verifies it against scipy so a sign slip is caught immediately.
    """
    # TODO 5: build and return the 3x3 matrix.
    raise NotImplementedError


# --------------------------------------------------------------------------- #
# Test harness — checks each function against scipy. Do not edit below.
# --------------------------------------------------------------------------- #
def _check(name, ok):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return ok


def main() -> int:
    rng = np.random.default_rng(0)
    results = []

    # Random unit quaternions for testing, in our (w,x,y,z) order.
    def random_quat():
        return _from_scipy(Rotation.random(random_state=rng).as_quat())

    print("Testing the quaternion toolkit against scipy...\n")

    # 1. conjugate: q * conj(q) == identity (1,0,0,0) for unit q.
    ok_all = True
    for _ in range(20):
        q = random_quat()
        prod = quat_mul(q, quat_conjugate(q))
        ok_all &= np.allclose(prod, [1, 0, 0, 0], atol=1e-9)
    results.append(_check("quat_conjugate: q * conj(q) == identity", ok_all))

    # 2. multiply vs scipy composition.
    ok_all = True
    for _ in range(20):
        q1, q2 = random_quat(), random_quat()
        mine = quat_mul(q1, q2)
        # scipy: (R1 * R2) corresponds to q1 (x) q2 in Hamilton convention.
        ref = _from_scipy(
            (Rotation.from_quat(_to_scipy(q1)) * Rotation.from_quat(_to_scipy(q2))).as_quat()
        )
        # q and -q are the same rotation (double cover): compare up to sign.
        ok_all &= (np.allclose(mine, ref, atol=1e-8) or np.allclose(mine, -ref, atol=1e-8))
    results.append(_check("quat_mul matches scipy composition (up to sign)", ok_all))

    # 2b. non-commutativity sanity.
    qa = axis_angle_to_quat([0, 0, 1], math.radians(90))
    qb = axis_angle_to_quat([0, 1, 0], math.radians(90))
    noncomm = not np.allclose(quat_mul(qa, qb), quat_mul(qb, qa), atol=1e-6)
    results.append(_check("quat_mul is non-commutative (q1*q2 != q2*q1)", noncomm))

    # 3. rotate vs scipy apply.
    ok_all = True
    for _ in range(20):
        q = random_quat()
        v = rng.standard_normal(3)
        mine = quat_rotate(q, v)
        ref = Rotation.from_quat(_to_scipy(q)).apply(v)
        ok_all &= np.allclose(mine, ref, atol=1e-8)
    results.append(_check("quat_rotate matches scipy apply", ok_all))

    # 4. axis_angle_to_quat vs scipy from_rotvec.
    ok_all = True
    for _ in range(20):
        axis = rng.standard_normal(3)
        axis = axis / np.linalg.norm(axis)
        theta = rng.uniform(-math.pi, math.pi)
        mine = axis_angle_to_quat(axis, theta)
        ref = _from_scipy(Rotation.from_rotvec(axis * theta).as_quat())
        ok_all &= (np.allclose(mine, ref, atol=1e-8) or np.allclose(mine, -ref, atol=1e-8))
    results.append(_check("axis_angle_to_quat matches scipy from_rotvec", ok_all))

    # 5. quat_to_matrix vs scipy as_matrix, plus orthonormality + det.
    ok_all = True
    for _ in range(20):
        q = random_quat()
        M = quat_to_matrix(q)
        ref = Rotation.from_quat(_to_scipy(q)).as_matrix()
        ortho = np.allclose(M.T @ M, np.eye(3), atol=1e-8)
        detok = np.isclose(np.linalg.det(M), 1.0, atol=1e-8)
        ok_all &= np.allclose(M, ref, atol=1e-8) and ortho and detok
    results.append(_check("quat_to_matrix matches scipy; orthonormal; det=+1", ok_all))

    print()
    if all(results):
        print("ALL CHECKS PASSED")
        return 0
    print("SOME CHECKS FAILED — re-read Lecture 1 5 for the function that failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())


# -----------------------------------------------------------------------------
# Expected output (once all five functions are implemented correctly)
# -----------------------------------------------------------------------------
#
# Testing the quaternion toolkit against scipy...
#
#   [PASS] quat_conjugate: q * conj(q) == identity
#   [PASS] quat_mul matches scipy composition (up to sign)
#   [PASS] quat_mul is non-commutative (q1*q2 != q2*q1)
#   [PASS] quat_rotate matches scipy apply
#   [PASS] axis_angle_to_quat matches scipy from_rotvec
#   [PASS] quat_to_matrix matches scipy; orthonormal; det=+1
#
# ALL CHECKS PASSED
#
# Until you implement the TODOs, you'll see NotImplementedError tracebacks — that
# is expected. Implement one function at a time and re-run; watch the PASS lines
# light up one by one. That incremental green is the whole satisfaction of the
# exercise: each function is proven against an independent reference before you
# move on.
# -----------------------------------------------------------------------------
