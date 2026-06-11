# Challenge 1 — The Full Mock Defense

**Type:** Live, adversarial, paired. Needs a mock panel (instructor + peer at minimum) and the real rubric.
**Estimated time:** ~3 hours (defense ~90 min, debrief + gap audit ~90 min).
**Difficulty:** Hard — this is the dress rehearsal for the panel that decides whether you graduate.

---

## The setup

Run the *entire* ninety-minute capstone defense, against the *real* rubric, with a mock panel, before the real defense on Saturday. This is not a casual walkthrough — it is the whole performance, scored, so the gaps surface with days left to fix instead of minutes. Solo-path learners: the mini-project explains how to self-run it with a recording and a structured peer review — but assemble a panel if you possibly can; defending to people who will push back is the point.

---

## The ninety minutes (the structure from Lecture 1 §2)

Run it on the clock, with these time budgets:

| Segment | Time | Your job |
|---|---|---|
| Opening pitch | 5 min | Deliver the Week 47 five-minute pitch; set the frame. |
| Stack walkthrough | 15 min | Narrate the architecture diagram; perception → policy → safety. |
| Videos | 10 min | Play the sim + real (or sim-hardened) runs; narrate what to watch. |
| Acceptance-criteria mapping | 10 min | Walk each criterion with its measured number and evidence (Exercise 2). |
| Safety case | 15 min | The hazard log, FMEA, mitigations, validation, residual risk; the "safety doesn't depend on the smart parts" thesis. |
| Chaos drills | 10 min | The two postmortems as validation evidence. |
| Live Q&A | 25 min | The panel probes; three-layer "why," knowledge-edge honesty, false-premise catching. |

---

## What the panel must do

Give your panel the rubric and these instructions:

- **Probe the acceptance criteria.** Ask for the evidence behind each number; consider rerunning the eval or the cold-boot live.
- **Dig three layers on at least two decisions** — EKF vs factor graph, MPC vs LQR, VLA vs scripted, INT8 vs FP16. Pounce on any "it's what the tutorial used."
- **Push on the safety case.** "What if the E-stop fails?" (Swiss-cheese answer expected.) "What's your residual risk?" (Quantified answer expected.) "What else could break?" (A named un-drilled failure expected.)
- **Plant one false premise** ("an EKF is exact for nonlinear systems, right?") and see if you catch it.
- **Score against the rubric** and note the two weakest segments.

---

## Acceptance criteria

You pass the challenge (the *mock*, not yet the real defense) if:

- [ ] You ran all seven segments **on the clock**, within the ninety minutes (running long is the most common failure — note it and fix the pacing).
- [ ] You presented the **acceptance-criteria table** yourself, with measured, evidenced numbers, and were honest about any miss.
- [ ] You held **three-layer "why"** on at least two decisions, each with a number from a real artifact.
- [ ] You presented the **safety case** on the "doesn't depend on the smart parts" thesis, answered "what if X fails" with the Swiss-cheese model, and quantified your residual risk.
- [ ] You **caught the planted false premise** instead of agreeing with it.
- [ ] You and the panel **scored** the mock and you recorded the two weakest segments with a gap-closing plan.

## Deliverable

Commit, next to your capstone:

1. `mock-defense-debrief.md` — the panel's rubric scores, the two weakest segments, and the gap-closing plan for the days before Saturday.
2. The **gap list** — every criterion you're short on, every question you couldn't hold to three layers, every safety hole the panel found — each with a dated fix. (A safety hole is your #1 priority, ahead of all polish.)
3. The updated **acceptance-criteria table** (Exercise 2 output) reflecting any fixes.

This debrief is the bridge to the real defense. The whole value is in finding the gaps now — a mock you sandbagged hands those gaps to the real panel.

---

## Stretch

- **Two panels, two days.** Run the mock with a second, different panel. The delta in what each finds is your true readiness; gaps both panels miss are probably fine, gaps both find are urgent.
- **Defend your weakest part on purpose.** Tell the panel "attack my state estimation" and let them. Surviving an attack on your weakest point is more convincing than a smooth tour of your strongest.
- **The live cold-boot.** Have the panel ask you to cold-boot the robot from power-off on the spot and time it. If it's not under 60 s live (not just in your notes), that's a gap to close now.
- **The "another month" roadmap.** Prepare the two-minute honest next-steps slide. Panels read it as ownership — you see past the deadline.
