#!/usr/bin/env python3
# Exercise 3 — The pick pipeline: transform, IK-filter, sequence
#
# Goal: Take the ranked grasps from Exercise 2 (in the CAMERA frame) and turn the
#       best reachable one into a MoveIt2 pick: transform to the planning frame,
#       filter the ranked list by IK feasibility (grasp AND pre-grasp), and build
#       the pre-grasp -> approach -> close -> lift sequence. You build the logic
#       that decides WHICH grasp to attempt and HOW to approach it.
#
# Estimated time: 45 minutes. Runnable.
#
# THE STUB
#
#   This file does not require a live MoveIt2 `move_group`. It ships a small
#   FakeArm that answers `ik_feasible(pose)` with a simple reachability model
#   (inside a workspace sphere, away from joint-limit edges) so you can develop
#   and test the FILTER and SEQUENCE logic offline. When `moveit_py` is available
#   and a `move_group` is up, set USE_MOVEIT = True and the same logic drives the
#   real arm. The decision logic you write is identical either way.
#
# HOW TO USE THIS FILE
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-pick-pipeline.py
#
#   It feeds a list of ranked grasps through the pipeline and prints which grasp
#   was selected, why the earlier ones were rejected, and the four-pose sequence.
#
# ACCEPTANCE CRITERIA
#
#   [ ] `first_reachable` skips grasps whose grasp OR pre-grasp is infeasible and
#       returns the highest-ranked grasp for which BOTH are feasible.
#   [ ] The pre-grasp pose is exactly `standoff` meters back along the grasp's
#       approach (+z) axis — verified by the script.
#   [ ] If NO grasp is reachable, the pipeline returns None and the caller logs a
#       fallback (Lecture 2 §5), rather than crashing.
#   [ ] You can name the failure bucket for each rejected grasp (here: 'planning').
#
# Expected output is at the bottom of the file.

import math

import numpy as np

USE_MOVEIT = False        # set True with a live move_group + moveit_py


# =====================================================================
#  Minimal pose type (position + 3x3 rotation), to avoid a hard ROS dep here.
# =====================================================================
class Pose:
    def __init__(self, position, rotation):
        self.position = np.asarray(position, dtype=float)   # (3,)
        self.rotation = np.asarray(rotation, dtype=float)   # (3,3), columns=axes

    @property
    def approach(self):
        return self.rotation[:, 2]                          # +z = approach


def back_off_along_approach(pose: Pose, standoff: float) -> Pose:
    """Pre-grasp pose: `standoff` meters BACK along the grasp's approach (+z).

    Backing off means moving opposite the approach direction (the gripper sits
    further from the object), so we SUBTRACT standoff * approach.
    """
    pre_pos = pose.position - standoff * pose.approach
    return Pose(pre_pos, pose.rotation)


def translate_z_world(pose: Pose, dz: float) -> Pose:
    """Translate a pose by dz along WORLD +z (the lift)."""
    p = pose.position.copy()
    p[2] += dz
    return Pose(p, pose.rotation)


# =====================================================================
#  The arm: real (moveit_py) or a reachability stub.
# =====================================================================
class FakeArm:
    """Stub reachability: feasible iff inside a workspace sphere centered at the
    shoulder and not too close to the base (a crude joint-limit proxy)."""

    def __init__(self):
        self.shoulder = np.array([0.0, 0.0, 0.30])
        self.reach = 0.85
        self.min_reach = 0.20

    def ik_feasible(self, pose: Pose) -> bool:
        d = np.linalg.norm(pose.position - self.shoulder)
        return self.min_reach < d < self.reach


class MoveItArm:
    """Real arm via moveit_py. Calls compute_ik; checks for a returned solution."""

    def __init__(self):
        from moveit.planning import MoveItPy            # imported lazily
        self.moveit = MoveItPy(node_name="pick_pipeline")
        self.arm = self.moveit.get_planning_component("manipulator")

    def ik_feasible(self, pose: Pose) -> bool:
        # In the real system: build a PoseStamped, call the IK service, return
        # whether a within-limits, collision-free solution came back. Left as the
        # mini-project's job to wire to your specific arm; the FakeArm models the
        # same yes/no contract.
        raise NotImplementedError("wire compute_ik for your arm in the mini-project")


# =====================================================================
#  The selection logic — THIS is what the exercise is about.
# =====================================================================
def first_reachable(arm, ranked_grasps, standoff=0.10):
    """Return (grasp, pre_grasp) for the highest-ranked grasp whose grasp AND
    pre-grasp are both IK-feasible. Returns (None, None) if none are."""
    for rank, g in enumerate(ranked_grasps):
        pre = back_off_along_approach(g, standoff)
        grasp_ok = arm.ik_feasible(g)
        pre_ok = arm.ik_feasible(pre)
        if grasp_ok and pre_ok:
            print(f"  grasp #{rank}: SELECTED (grasp & pre-grasp both feasible)")
            return g, pre
        reason = ("grasp infeasible" if not grasp_ok
                  else "pre-grasp infeasible (approach leaves the workspace)")
        print(f"  grasp #{rank}: REJECTED -> {reason}  [bucket: planning]")
    return None, None


def build_pick_sequence(grasp: Pose, pre_grasp: Pose, width: float, lift=0.12):
    """The four-stage pick: pre-grasp -> approach -> close -> lift."""
    seq = [
        ("pre_grasp", pre_grasp, None),
        ("approach", grasp, None),                       # Cartesian to grasp
        ("close_gripper", grasp, max(width - 0.005, 0.0)),  # slight over-close
        ("lift", translate_z_world(grasp, lift), None),  # Cartesian up
    ]
    return seq


# =====================================================================
#  Demo: a ranked list where the top grasps are out of reach.
# =====================================================================
def downward_grasp(xyz, width=0.06):
    """A grasp pointing straight down (+z approach = world -z would be ideal; here
    we keep approach=+z for the stub's geometry)."""
    R = np.eye(3)
    return Pose(xyz, R)


def main():
    arm = MoveItArm() if USE_MOVEIT else FakeArm()
    print(f"arm: {'MoveIt2' if USE_MOVEIT else 'FakeArm stub'}")

    # Ranked grasps (best-first). The first two are deliberately out of reach.
    ranked = [
        downward_grasp([1.20, 0.00, 0.50]),   # too far (> reach) -> rejected
        downward_grasp([0.05, 0.00, 0.34]),   # too close to shoulder (< min_reach)
        downward_grasp([0.45, 0.10, 0.45]),   # reachable -> SELECTED
        downward_grasp([0.40, -0.05, 0.46]),
    ]
    widths = [0.061, 0.058, 0.060, 0.063]

    print("filtering ranked grasps by IK feasibility (grasp AND pre-grasp):")
    grasp, pre = first_reachable(arm, ranked, standoff=0.10)

    if grasp is None:
        print("NO reachable grasp -> fall back to antipodal sampler (Lecture 2 §5)")
        return

    # Verify the pre-grasp geometry: standoff back along approach.
    offset = grasp.position - pre.position
    along = float(offset @ grasp.approach)
    print(f"\npre-grasp standoff along approach = {along:.3f} m (expected 0.100)")
    assert abs(along - 0.10) < 1e-6, "pre-grasp is not standoff back along approach"

    idx = ranked.index(grasp)
    seq = build_pick_sequence(grasp, pre, widths[idx])
    print("\npick sequence:")
    for name, pose, arg in seq:
        extra = f"  (gripper -> {arg:.3f} m)" if arg is not None else ""
        p = pose.position
        print(f"  {name:<14} pos=({p[0]:+.3f},{p[1]:+.3f},{p[2]:+.3f}){extra}")
    print("\n[pick] would now execute: plan(pre) -> cartesian(approach) -> "
          "close -> cartesian(lift). SUCCESS on object_held().")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# arm: FakeArm stub
# filtering ranked grasps by IK feasibility (grasp AND pre-grasp):
#   grasp #0: REJECTED -> grasp infeasible  [bucket: planning]
#   grasp #1: REJECTED -> grasp infeasible  [bucket: planning]
#   grasp #2: SELECTED (grasp & pre-grasp both feasible)
#
# pre-grasp standoff along approach = 0.100 m (expected 0.100)
#
# pick sequence:
#   pre_grasp      pos=(+0.450,+0.100,+0.350)
#   approach       pos=(+0.450,+0.100,+0.450)
#   close_gripper  pos=(+0.450,+0.100,+0.450)  (gripper -> 0.055 m)
#   lift           pos=(+0.450,+0.100,+0.570)
#
# [pick] would now execute: plan(pre) -> cartesian(approach) -> close -> cartesian(lift). SUCCESS on object_held().
#
# The lesson: the network's top grasp is frequently UNREACHABLE. The pick pipeline
# must walk the ranked list and pick the best grasp that is feasible for BOTH the
# grasp and its approach — and if none are, hand off to the fallback rather than
# stall. Every rejection here is a 'planning' bucket failure (Lecture 2 §4).
# -----------------------------------------------------------------------------
