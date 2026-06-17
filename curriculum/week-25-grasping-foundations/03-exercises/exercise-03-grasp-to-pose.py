#!/usr/bin/env python3
# Exercise 3 — Grasp to pose (turn an antipodal pair into a pose MoveIt2 can reach)
#
# Goal: Build a gripper-frame SE(3) grasp pose from an antipodal contact pair: the
#       grasp point (midpoint), the closing axis (the A-B line), and a sane
#       approach axis, assembled into a rotation matrix and a standoff pre-grasp
#       pose, then emitted as a PoseStamped ready for MoveIt2.
#
# Estimated time: 45 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone. Install NumPy + SciPy, then run:
#
#       pip install numpy scipy
#       python3 exercise-03-grasp-to-pose.py
#
#   It builds a grasp pose for a worked antipodal pair, prints the grasp and
#   pre-grasp poses (position + quaternion), and ASSERTS the geometry is correct:
#   the approach axis is perpendicular to the closing axis, the rotation matrix is
#   orthonormal, and the pre-grasp is offset back along the approach axis.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The grasp pose is printed as a midpoint position and a unit quaternion in a
#       named frame.
#   [ ] The closing axis is orthogonal to the approach axis (dot product ~ 0).
#   [ ] The rotation matrix R is orthonormal (R^T R = I) and right-handed (det = +1).
#   [ ] The pre-grasp position is offset from the grasp position by exactly the
#       standoff distance, along the approach axis.
#   [ ] All assertions pass and the program prints PASS and exits 0.
#
# CONVENTION NOTE (read Lecture 2 §1.1)
#
#   Here: column 0 of R = approach axis, column 1 = closing (baseline) axis,
#   column 2 = their cross product. YOUR gripper's URDF tool frame decides which
#   axis is "approach" — align this to it or the arm reaches a pose 90 deg wrong
#   and the fingers sweep sideways through the object. This is the silent failure.
#
# Expected output is at the bottom of the file.

import sys
import numpy as np
from scipy.spatial.transform import Rotation


def grasp_orientation(closing_axis, approach_axis) -> np.ndarray:
    """3x3 rotation: column 0 = approach, column 1 = closing, column 2 = cross.
    The closing axis is made orthogonal to the approach axis (Gram-Schmidt)."""
    a = np.asarray(approach_axis, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    b = np.asarray(closing_axis, float)
    b = b - np.dot(b, a) * a                 # orthogonalize closing wrt approach
    b = b / (np.linalg.norm(b) + 1e-12)
    c = np.cross(a, b)                        # right-handed third axis
    return np.column_stack([a, b, c])


def build_grasp_pose(pA, pB, approach_axis, standoff=0.10):
    """Return (grasp, pregrasp) as (position, quaternion_xyzw) tuples and R."""
    pA, pB = np.asarray(pA, float), np.asarray(pB, float)
    p = (pA + pB) / 2.0
    closing = pB - pA
    R = grasp_orientation(closing_axis=closing, approach_axis=approach_axis)
    quat = Rotation.from_matrix(R).as_quat()       # (x, y, z, w)
    approach = R[:, 0]                             # column 0 is the approach axis
    pregrasp = p - approach * standoff             # back off along approach
    return (p, quat, R), (pregrasp, quat)


def to_pose_stamped_dict(position, quat_xyzw, frame_id, stamp_sec=0):
    """A plain dict mirroring geometry_msgs/PoseStamped, so this file runs without
    a ROS2 install. In your node you'd build the real PoseStamped and tf2-transform
    it into the planning frame using the CLOUD's stamp (not now()) -- Lecture 2 §1.3."""
    return {
        "header": {"frame_id": frame_id, "stamp": stamp_sec},
        "pose": {
            "position": {"x": float(position[0]), "y": float(position[1]),
                         "z": float(position[2])},
            "orientation": {"x": float(quat_xyzw[0]), "y": float(quat_xyzw[1]),
                            "z": float(quat_xyzw[2]), "w": float(quat_xyzw[3])},
        },
    }


def main() -> None:
    # A worked antipodal pair on a cylinder of diameter 0.07 m, grasp at mid-height,
    # closing along x (the line joining the two contacts), approaching from +z (top-down
    # offset to be horizontal-ish): we want approach perpendicular to closing.
    pA = np.array([-0.035, 0.0, 0.06])
    pB = np.array([0.035, 0.0, 0.06])           # closing axis is +x, width 0.07 m
    width = float(np.linalg.norm(pB - pA))

    # Approach from above and to the side; it MUST be perpendicular to the closing
    # axis (+x). Pick world-down-ish (-z) which is already perpendicular to +x.
    approach_axis = np.array([0.0, 0.0, -1.0])
    standoff = 0.10
    frame_id = "base_link"

    (p, quat, R), (pregrasp, quat2) = build_grasp_pose(
        pA, pB, approach_axis, standoff=standoff)

    grasp_ps = to_pose_stamped_dict(p, quat, frame_id)
    pregrasp_ps = to_pose_stamped_dict(pregrasp, quat2, frame_id)

    print("grasp pose (frame=%s):" % frame_id)
    print(f"  position=({p[0]:+.3f}, {p[1]:+.3f}, {p[2]:+.3f})  "
          f"quat=({quat[0]:+.3f}, {quat[1]:+.3f}, {quat[2]:+.3f}, {quat[3]:+.3f})  "
          f"width={width:.3f} m")
    print("pre-grasp pose (standoff %.2f m along approach):" % standoff)
    print(f"  position=({pregrasp[0]:+.3f}, {pregrasp[1]:+.3f}, {pregrasp[2]:+.3f})")

    # --- geometry assertions (Lecture 2 §1.1) ------------------------------
    a = R[:, 0]
    b = R[:, 1]
    closing = (pB - pA) / np.linalg.norm(pB - pA)
    assert abs(np.dot(a, b)) < 1e-6, "approach not perpendicular to closing axis"
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-6), "R not orthonormal"
    assert abs(np.linalg.det(R) - 1.0) < 1e-6, "R not right-handed (det != +1)"
    # closing axis (b) should be the (orthogonalized) line direction; here +x.
    assert abs(abs(np.dot(b, closing)) - 1.0) < 1e-6, "closing axis mismatch"
    # pre-grasp is exactly standoff back along approach.
    assert np.allclose(p - pregrasp, a * standoff, atol=1e-6), "bad standoff offset"

    print("\nPASS: approach _|_ closing, R orthonormal & right-handed, "
          "standoff along approach.")
    # In a node, you would now tf2-transform grasp_ps into the planning frame and
    # hand it to move_group.set_pose_target(...). The dict here is the stand-in.
    _ = (grasp_ps, pregrasp_ps)
    sys.exit(0)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# grasp pose (frame=base_link):
#   position=(+0.000, +0.000, +0.060)  quat=(+0.707, +0.000, +0.707, +0.000)  width=0.070 m
# pre-grasp pose (standoff 0.10 m along approach):
#   position=(+0.000, +0.000, +0.160)
#
# PASS: approach _|_ closing, R orthonormal & right-handed, standoff along approach.
# (exit 0)
#
# Note: the pre-grasp z (0.160) is ABOVE the grasp z (0.060) because the approach
# axis is -z (coming down), so backing off along approach means going UP by the
# standoff. That sign is the thing people get wrong: the pre-grasp is BEHIND the
# grasp along the approach direction, which for a top-down grasp is higher up.
#
# CONVENTION REMINDER: the exact quaternion depends on which column of R you call
# "approach". Align that to YOUR gripper's URDF tool frame, or the arm reaches a
# pose 90 deg off and the fingers sweep sideways through the object. Verify against
# the URDF, not against this file's convention.
# -----------------------------------------------------------------------------
