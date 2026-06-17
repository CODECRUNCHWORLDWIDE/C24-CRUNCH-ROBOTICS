#!/usr/bin/env python3
# Exercise 3 -- The defense Q&A bank.
#
# Goal: drill the questions a defense panel actually asks (Lecture 2 section 5).
#       Each question comes with the three-layer structure your answer needs and the
#       trap to avoid. The lesson: the panel digs three layers deep, expects a NUMBER
#       at one layer, and rewards catching a false premise -- reading the answers is
#       not enough; say them out loud, cold.
#
# Estimated time: 50 minutes. Runnable. Pure Python -- a self-quiz harness.
#
# HOW TO USE THIS FILE
#   python3 exercise-03-defense-qa-bank.py            # print the whole bank
#   python3 exercise-03-defense-qa-bank.py --drill    # one at a time, self-rate
#   python3 exercise-03-defense-qa-bank.py --self-check
#
#   For --drill: read the question, ANSWER OUT LOUD (three layers, with a number),
#   then reveal the structure and rate yourself honestly. Track which you can't
#   answer to three layers -- those are your Friday gap-closing list.
#
# ACCEPTANCE CRITERIA
#   [ ] The bank covers the spec's system properties and the common "why" probes.
#   [ ] Each entry names the three layers an answer must hold and the trap.
#   [ ] You drill them out loud and record which you can't hold to three layers.
#   [ ] `python3 exercise-03-defense-qa-bank.py --self-check` prints ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass
class QA:
    question: str
    layers: tuple[str, str, str]   # the three "why" layers your answer must hold
    needs_number: str              # the layer where a measured number is mandatory
    trap: str                      # the non-answer / false premise to avoid


BANK = [
    QA(
        question="Why an EKF for local state estimation, not a factor graph?",
        layers=(
            "EKF: bounded constant-time compute on Orin; my motion is mildly nonlinear.",
            "It met my drift budget; a factor graph buys accuracy I didn't need at compute I couldn't spend.",
            "If the linearization error grew I'd see it in the covariance; I tune Q to absorb it.",
        ),
        needs_number="the drift budget (< 0.5 m over 20 m -- cite your measured number)",
        trap="'an EKF is exact for nonlinear systems' is FALSE -- it linearizes; catch this if the panel asserts it.",
    ),
    QA(
        question="Why MPC (or PID) for the base controller?",
        layers=(
            "Hard actuator + corridor constraints I want INSIDE the optimization.",
            "Clamping an LQR output breaks its optimality near saturation; MPC plans feasible.",
            "If the solver misses its deadline I fall back to the warm-start step, then a controlled stop.",
        ),
        needs_number="the solver p95 vs your control-loop budget (cite the Foxglove panel)",
        trap="'it's what the controls lecture used' is a non-answer -- name the rejected alternative (LQR) and why.",
    ),
    QA(
        question="Why a VLA policy, not a scripted grasp?",
        layers=(
            "The task is language-conditioned across 20 instructions; a script doesn't generalize.",
            "I wrapped it with a safety filter + classical fallback for when the policy is rejected.",
            "The fallback triggers after 3 rejections; I measured the intervention rate.",
        ),
        needs_number="per-instruction success rate (Week 44 eval) and the intervention rate",
        trap="overclaiming the VLA -- be honest about which instruction classes it fails.",
    ),
    QA(
        question="Why INT8 on the detector? What did you give up?",
        layers=(
            "It cleared the 50 ms cycle budget; FP16 alone didn't fit.",
            "I calibrated on representative frames and measured the mAP delta on a held-out set.",
            "Cost 1.4 mAP, within my 3-point floor; below the floor I'd have used mixed precision or QAT.",
        ),
        needs_number="the mAP before/after and the latency before/after (Week 39 report)",
        trap="'INT8 has no accuracy cost' is FALSE -- it cost measured points; never claim it's free.",
    ),
    QA(
        question="How is your robot safe if the learned policy is wrong?",
        layers=(
            "Safety doesn't depend on the smart parts -- the safety layer sits underneath and doesn't trust them.",
            "Software E-stop (200 ms latch) + velocity/workspace clamps bound any action, policy or not.",
            "Layered (Swiss-cheese): for harm, the E-stop AND the clamp AND the hardware stop must all fail.",
        ),
        needs_number="the residual risk, quantified (e.g. <=1.6 cm travel at 0.2 m/s in the clamp-engage gap)",
        trap="'my robot is safe because the policy is good' -- the senior answer is the INVERSE.",
    ),
    QA(
        question="What else could break that you didn't chaos-drill?",
        layers=(
            "Name a real un-drilled failure (e.g. network partition policy<->planner, clock jump).",
            "Why it matters: which mitigation it would stress that I'm least sure of.",
            "How I'd drill it next and what I'd predict.",
        ),
        needs_number="not a number here -- but a SPECIFIC next drill, not 'lots of things'",
        trap="'nothing else, I covered it all' -- a candidate who can't name an un-drilled failure isn't thinking in failure modes.",
    ),
    QA(
        question="Walk me through your cold-boot. Why under 60 seconds?",
        layers=(
            "The launch graph brings up sensors, perception, nav, policy, safety in a measured sequence.",
            "I parallelized independent bring-ups and lazy-load the policy weights.",
            "The bottleneck was X; I measured the timed boot and it's under the spec bar.",
        ),
        needs_number="the measured cold-boot time (spec: < 60 s)",
        trap="claiming a time you never timed -- the panel may ask you to run it live.",
    ),
]


def print_bank() -> None:
    print("=" * 70)
    print("Defense Q&A bank (Lecture 2 section 5) -- ANSWER OUT LOUD, three layers deep")
    print("=" * 70)
    for i, qa in enumerate(BANK, 1):
        print(f"\nQ{i}. {qa.question}")
        print(f"    layer 1: {qa.layers[0]}")
        print(f"    layer 2: {qa.layers[1]}")
        print(f"    layer 3: {qa.layers[2]}")
        print(f"    NUMBER:  {qa.needs_number}")
        print(f"    TRAP:    {qa.trap}")
    print("\n" + "=" * 70)
    print(f"{len(BANK)} questions. Drill each OUT LOUD; list the ones you can't hold")
    print("to three layers -- those are your Friday gap-closing list.")
    print("=" * 70)


def drill() -> None:
    print("Drill mode: read each question, answer OUT LOUD (three layers + a number),")
    print("then press Enter to reveal the structure and rate yourself.\n")
    weak = []
    for i, qa in enumerate(BANK, 1):
        print(f"Q{i}. {qa.question}")
        try:
            input("   [answer out loud, then Enter to reveal] ")
        except EOFError:
            print("   (non-interactive; printing structure)")
        print(f"   layer 1: {qa.layers[0]}")
        print(f"   layer 2: {qa.layers[1]}")
        print(f"   layer 3: {qa.layers[2]}")
        print(f"   NUMBER:  {qa.needs_number}")
        print(f"   TRAP:    {qa.trap}\n")
    print("Record the questions you couldn't hold to three layers; fix them Friday.")


def self_check() -> bool:
    ok = True
    if len(BANK) < 6:
        print("CHECK FAILED: the bank should cover at least 6 probe areas.")
        ok = False
    for qa in BANK:
        if len(qa.layers) != 3:
            print(f"CHECK FAILED: '{qa.question[:30]}...' must name exactly 3 layers.")
            ok = False
        if not qa.needs_number:
            print(f"CHECK FAILED: '{qa.question[:30]}...' must name where a number is needed.")
            ok = False
        if not qa.trap:
            print(f"CHECK FAILED: '{qa.question[:30]}...' must name the trap.")
            ok = False
    # The safety question must encode the 'inverse' thesis.
    safety = next((q for q in BANK if "safe if the learned policy" in q.question), None)
    if safety is None or "INVERSE" not in safety.trap:
        print("CHECK FAILED: the safety question must teach the 'safety doesn't depend on the smart parts' inverse.")
        ok = False
    return ok


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        if self_check():
            print("ALL CHECKS PASSED")
            return 0
        print("CHECKS FAILED -- see above.")
        return 1
    if "--drill" in argv:
        drill()
        return 0
    print_bank()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT (--self-check):
#   ALL CHECKS PASSED
#
# EXPECTED OUTPUT (default, abbreviated):
#   ======================================================================
#   Defense Q&A bank (Lecture 2 section 5) -- ANSWER OUT LOUD, three layers deep
#   ======================================================================
#   Q1. Why an EKF for local state estimation, not a factor graph?
#       layer 1: EKF: bounded constant-time compute on Orin; ...
#       ...
#       NUMBER:  the drift budget (< 0.5 m over 20 m -- cite your measured number)
#       TRAP:    'an EKF is exact for nonlinear systems' is FALSE ...
#   ... (7 questions total) ...
#
# The takeaway: the panel asks these cold and digs three layers. Reading them isn't
# enough -- drill them OUT LOUD, with a real number at the marked layer, and learn
# to catch the false premises (the EKF-is-exact and INT8-is-free traps especially).
# ---------------------------------------------------------------------------
