#!/usr/bin/env python3
# Exercise 3 — The VLA policy loop (gate + fallback)
#
# Goal: Build the full "ship it with a leash" loop: a VLA proposes an action,
#       a VERIFICATION GATE checks the action's target against an INDEPENDENT
#       open-vocab grounding of the instruction, and after K rejections control
#       hands off to a CLASSICAL FALLBACK. This is the week-32 safety pattern,
#       with a VLA in the policy slot and grounding as the leash.
#
# Estimated time: 55 minutes. Runnable TODAY — no GPU, no weights.
#
# HOW IT RUNS WITHOUT A GPU
#
#   Two functions are stubbed and clearly marked:
#     - vla_propose(image, instruction)  -> a proposed action with a 3D target.
#     - the grounder is imported from Exercise 2 (its stub OWL-ViT).
#   The stub VLA is scripted to be RIGHT on some instructions and WRONG
#   (hallucinating onto the distractor) on another, so you watch the gate ACCEPT
#   and REJECT and the fallback fire. Swap the two "# TODO" stubs for the real
#   OpenVLA + OWL-ViT to run on the robot.
#
#       python3 exercise-03-vla-policy-loop.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] A correct VLA proposal (target agrees with grounding) is ACCEPTED.
#   [ ] A hallucinated proposal (target on the wrong object) is REJECTED with a
#       low agreement score.
#   [ ] After 3 consecutive rejections the loop FALLS BACK to the classical
#       planner, which targets the EXPLICIT grounding's location.
#   [ ] An instruction whose object is absent is rejected at the grounding step
#       ("not in scene") before the agreement check even runs.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import math
from dataclasses import dataclass

# Reuse the explicit grounder from Exercise 2. Its filename has dashes, so we
# load it by path rather than a normal import.
import importlib.util
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "ovgrounding", os.path.join(_here, "exercise-02-open-vocab-grounding.py")
)
ovg = importlib.util.module_from_spec(_spec)
# Register before exec so dataclasses in the loaded module can resolve types.
sys.modules["ovgrounding"] = ovg
_spec.loader.exec_module(ovg)   # type: ignore

# Pixel<->approx 3D: the stub treats image x as world x for the demo. A real
# loop projects the action target into the image via the depth camera + tf2.
AGREEMENT_MIN = 0.30        # min IoU/agreement for the gate to ACCEPT.
MAX_REJECTS = 3             # rejections before the classical fallback takes over.


@dataclass
class Action:
    """A proposed manipulation action with a 3D target (here, in image-ish px)."""
    target_px: tuple[float, float]      # where the action aims, in image coords
    gripper: str                        # "close" / "open"
    source: str                         # "vla" or "fallback"


def box_point_agreement(box, point_px) -> float:
    """Agreement of an action target point with a detection box.

    1.0 if the point is at the box center; decays to 0 as it leaves the box.
    Stands in for IoU between the VLA's targeted region and the grounded box.
    """
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    half_w, half_h = (x2 - x1) / 2.0, (y2 - y1) / 2.0
    px, py = point_px
    # Normalized distance from center; >1 means outside the box.
    dx = abs(px - cx) / max(half_w, 1e-6)
    dy = abs(py - cy) / max(half_h, 1e-6)
    dist = math.hypot(dx, dy)
    return max(0.0, 1.0 - dist / 2.0)   # 1 at center, 0 at ~2 box-radii out


# --- The stub VLA (replace with OpenVLA for the real thing) ------------------

def vla_propose(image, instruction: str, attempt: int) -> Action:
    """STUB VLA: proposes an action with a 3D target for the instruction.

    Scripted so the loop demonstrates ACCEPT, REJECT, and FALLBACK:
      - "bring the red cup"      -> correct target (agrees with grounding).
      - "pick up the tool"       -> HALLUCINATES onto the blue block across the
                                    table (clearly the WRONG object) EVERY
                                    attempt, so it gets rejected MAX_REJECTS times.
    """
    # TODO 1: replace with a real OpenVLA forward pass:
    #   action_tokens = openvla.predict_action(image, instruction, unnorm_key=...)
    #   target_px = project_to_image(action_tokens, depth, tf)   # frames! (L1 §4)
    #   return Action(target_px, gripper_from(action_tokens), "vla")
    if "red cup" in instruction:
        return Action(target_px=(430, 320), gripper="close", source="vla")  # right
    if "tool" in instruction:
        # Hallucinate: aim at the blue block (210,330) — a different object
        # clear across the table from the tool at (650,290). The gate must
        # catch this because the targets disagree.
        return Action(target_px=(210, 330), gripper="close", source="vla")  # wrong
    # Default: aim near the blue block.
    return Action(target_px=(210, 330), gripper="close", source="vla")


def classical_fallback(grounded) -> Action:
    """The week-32 classical fallback: a scripted grasp at the EXPLICIT
    grounding's location. Less clever than the VLA, but predictable."""
    cx, cy = grounded.center()
    return Action(target_px=(cx, cy), gripper="close", source="fallback")


def run_instruction(image, instruction: str) -> Action | None:
    """The full gated loop for one instruction. Returns the dispatched Action,
    or None if grounding failed outright (absent object)."""
    print(f"\n[vla] instruction: {instruction!r}")
    grounded, reason = ovg.ground(image, instruction)
    if grounded is None:
        print(f"[gate] grounding FAILED before any action: {reason}  -> ABORT")
        return None
    print(f"[gate] explicit grounding: {reason}, box center {grounded.center()}")

    rejects = 0
    while rejects < MAX_REJECTS:
        action = vla_propose(image, instruction, attempt=rejects)
        agree = box_point_agreement(grounded.box, action.target_px)
        if agree >= AGREEMENT_MIN:
            print(f"[vla] proposed target {action.target_px}, gripper {action.gripper}")
            print(f"[gate] agreement {agree:.2f} >= {AGREEMENT_MIN}  -> ACCEPT")
            print(f"[bt] dispatching {action.source} action to MoveIt2...")
            return action
        rejects += 1
        print(f"[vla] proposed target {action.target_px} (gripper {action.gripper})")
        print(f"[gate] agreement {agree:.2f} < {AGREEMENT_MIN}  -> REJECT "
              f"(VLA targeting wrong object); rejection {rejects}/{MAX_REJECTS}")

    print(f"[fallback] {MAX_REJECTS} consecutive rejections -> CLASSICAL FALLBACK")
    action = classical_fallback(grounded)
    print(f"[bt] dispatching FALLBACK grasp at grounding center {action.target_px}")
    return action


def main() -> None:
    image = None    # stubs ignore it; the real loop passes the camera frame.

    # 1) A clean accept.
    run_instruction(image, "bring the red cup")

    # 2) A persistent hallucination -> 3 rejects -> fallback.
    run_instruction(image, "pick up the tool")

    # 3) An absent object -> aborted at grounding.
    run_instruction(image, "bring the green bottle")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# [vla] instruction: 'bring the red cup'
# [gate] explicit grounding: grounded 'red cup' at conf 0.88, box center (430.0, 320.0)
# [vla] proposed target (430, 320), gripper close
# [gate] agreement 1.00 >= 0.3  -> ACCEPT
# [bt] dispatching vla action to MoveIt2...
#
# [vla] instruction: 'pick up the tool'
# [gate] explicit grounding: grounded 'tool' at conf 0.66, box center (650.0, 290.0)
# [vla] proposed target (645, 300) (gripper close)
# [gate] agreement ... < 0.3  -> REJECT (VLA targeting wrong object); rejection 1/3
# ... (rejection 2/3, rejection 3/3) ...
# [fallback] 3 consecutive rejections -> CLASSICAL FALLBACK
# [bt] dispatching FALLBACK grasp at grounding center (650.0, 290.0)
#
# [vla] instruction: 'bring the green bottle'
# [gate] grounding FAILED before any action: 'green bottle' not detected ... -> ABORT
#
# THE LESSON: three outcomes, three lessons. (1) Agreement -> accept the VLA.
# (2) Persistent disagreement -> the gate refuses the VLA's wrong-object grasp
# and the classical fallback grasps the ACTUALLY-grounded location instead.
# (3) Absent object -> abort before any motion. The VLA never reaches the motors
# unless an INDEPENDENT signal agrees with it. That's the leash.
# -----------------------------------------------------------------------------
