#!/usr/bin/env python3
# Exercise 3 -- The planner-deadlock detector + recovery ladder.
#
# Goal: build the deadlock half of gameday (Lecture 2 section 3). Detect the
#       replan-WITHOUT-progress signature -- the conjunction of "replanning often"
#       AND "not moving" -- then walk the recovery ladder: relax -> clear -> request
#       operator assist -> controlled stop. The lesson: either signal alone is a
#       false positive; the CONJUNCTION is the deadlock; and escalation is a defined
#       ladder, not a panic.
#
# Estimated time: 50 minutes. Runnable. Pure-Python simulator -- no ROS2 needed.
#
# HOW TO USE THIS FILE
#   python3 exercise-03-deadlock-detector.py
#   Fill in the two TODOs (the deadlock conjunction and the ladder escalation).
#
# ACCEPTANCE CRITERIA
#   [ ] is_deadlocked() is True ONLY when replanning AND not progressing (conjunction).
#   [ ] Replanning WHILE progressing (normal dynamic-obstacle avoidance) is NOT a
#       deadlock. Stationary WITHOUT replanning (waiting) is NOT a deadlock.
#   [ ] The ladder escalates relax -> clear -> operator_assist -> controlled_stop,
#       stopping at the first rung that recovers.
#   [ ] `python3 exercise-03-deadlock-detector.py` prints ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import sys
from dataclasses import dataclass

PROGRESS_THRESHOLD_M = 0.1   # meters of forward progress over the window
REPLAN_THRESHOLD = 3         # replans within the window that count as "cycling"
WINDOW_S = 5.0


@dataclass
class PlannerState:
    replans_in_window: int
    meters_in_window: float


def is_deadlocked(state: PlannerState) -> bool:
    """The deadlock signature is the CONJUNCTION (Lecture 2 section 3):
       replanning a lot AND not making forward progress. Either alone is a false
       positive -- replanning while moving is normal; stationary without replanning
       is just waiting."""
    replanning = state.replans_in_window >= REPLAN_THRESHOLD
    progressing = state.meters_in_window > PROGRESS_THRESHOLD_M
    # TODO 1: return True only when replanning AND NOT progressing.
    return replanning and not progressing


# The recovery ladder. Each rung is a callable that returns True if it recovered.
# In the real robot these call Nav2 (relaxed tolerances, clear costmap), publish an
# operator-assist request, or trip the controlled stop. Here they are simulated by
# a scenario that says which rung will succeed.
LADDER = ["relax", "clear", "operator_assist", "controlled_stop"]


def walk_ladder(recovering_rung: str | None) -> list[str]:
    """Escalate through the ladder, stopping at the first rung that recovers.
    `recovering_rung` is the rung that succeeds in this scenario, or None if nothing
    works until the controlled stop (which always 'succeeds' by stopping safely)."""
    taken: list[str] = []
    for rung in LADDER:
        taken.append(rung)
        # TODO 2: stop escalating at the rung that recovers. The controlled_stop
        #         rung ALWAYS terminates the ladder (stopping safely is a valid
        #         terminal outcome -- Lecture 2 section 3, rung 4).
        if rung == recovering_rung:
            break
        if rung == "controlled_stop":
            break
    return taken


def run_scenarios() -> bool:
    ok = True

    # Detection scenarios -------------------------------------------------
    # Deadlock: 4 replans, 0.02 m progress in the window -> True.
    s_deadlock = PlannerState(replans_in_window=4, meters_in_window=0.02)
    d1 = is_deadlocked(s_deadlock)
    print(f"detect  replan=4, moved=0.02m  -> deadlocked={d1}  (expect True)")
    ok &= (d1 is True)

    # Normal avoidance: 4 replans BUT 1.2 m progress -> NOT a deadlock.
    s_avoid = PlannerState(replans_in_window=4, meters_in_window=1.2)
    d2 = is_deadlocked(s_avoid)
    print(f"detect  replan=4, moved=1.2m   -> deadlocked={d2}  (expect False: moving)")
    ok &= (d2 is False)

    # Waiting at a light: 0 replans, 0 progress -> NOT a deadlock.
    s_wait = PlannerState(replans_in_window=0, meters_in_window=0.0)
    d3 = is_deadlocked(s_wait)
    print(f"detect  replan=0, moved=0.0m   -> deadlocked={d3}  (expect False: waiting)")
    ok &= (d3 is False)

    print("-" * 60)

    # Ladder scenarios ----------------------------------------------------
    # The relaxed replan recovers (the common case, Lecture 2 section 3 timeline).
    t1 = walk_ladder(recovering_rung="relax")
    print(f"ladder  relaxed replan works   -> {t1}")
    ok &= (t1 == ["relax"])

    # Relax fails, clearing the stale costmap recovers.
    t2 = walk_ladder(recovering_rung="clear")
    print(f"ladder  clear costmap works    -> {t2}")
    ok &= (t2 == ["relax", "clear"])

    # Autonomy can't solve it -> escalate to operator assist (a PASS, not a fail).
    t3 = walk_ladder(recovering_rung="operator_assist")
    print(f"ladder  escalate to operator   -> {t3}")
    ok &= (t3 == ["relax", "clear", "operator_assist"])

    # Nothing works and no assist arrives -> controlled stop terminates the ladder.
    t4 = walk_ladder(recovering_rung=None)
    print(f"ladder  last resort: stop      -> {t4}")
    ok &= (t4 == ["relax", "clear", "operator_assist", "controlled_stop"])

    return ok


def main() -> int:
    print("=" * 60)
    print("Planner-deadlock detector + recovery ladder (Lecture 2 section 3)")
    print("=" * 60)
    if run_scenarios():
        print("-" * 60)
        print("ALL CHECKS PASSED")
        return 0
    print("-" * 60)
    print("CHECKS FAILED -- see scenarios above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT:
#
#   ============================================================
#   Planner-deadlock detector + recovery ladder (Lecture 2 section 3)
#   ============================================================
#   detect  replan=4, moved=0.02m  -> deadlocked=True  (expect True)
#   detect  replan=4, moved=1.2m   -> deadlocked=False  (expect False: moving)
#   detect  replan=0, moved=0.0m   -> deadlocked=False  (expect False: waiting)
#   ------------------------------------------------------------
#   ladder  relaxed replan works   -> ['relax']
#   ladder  clear costmap works    -> ['relax', 'clear']
#   ladder  escalate to operator   -> ['relax', 'clear', 'operator_assist']
#   ladder  last resort: stop      -> ['relax', 'clear', 'operator_assist', 'controlled_stop']
#   ------------------------------------------------------------
#   ALL CHECKS PASSED
#
# The takeaway: the deadlock signature is the CONJUNCTION of replanning AND not
# progressing -- so normal dynamic-obstacle avoidance (moving while replanning) and
# a robot waiting at a light are both correctly NOT flagged. Recovery is an ordered
# ladder; escalating to a human operator is a PASS, and a controlled stop is the
# defensible last resort -- never grinding the planner forever.
# ---------------------------------------------------------------------------
