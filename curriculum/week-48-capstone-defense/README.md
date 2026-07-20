# Week 48 — Capstone Defense

This is the last week. Forty-seven weeks of math, ROS2, perception, fusion, SLAM, planning, control, manipulation, learned policies, sim-to-real, fleet ops, edge optimization, safety, and chaos drills come down to ninety minutes in front of a panel. They read your safety case, watch your videos, review your chaos-drill postmortems, and ask you live questions until they find the edge of what you know. At the end, they sign the rubric — or they don't. This week is how you walk in ready.

Here is what the defense actually is, stripped of ceremony: it is the moment you stop being a learner and become a peer engineer. The panel is not trying to fail you; they are trying to find out whether they would trust you on a robot that operates near people. That trust is built from three things, and this week assembles all three: a robot that *works* (the demo), a safety case that proves you thought about how it *hurts someone if it goes wrong* (the document), and a defense where you can answer "why" three layers deep without bluffing (the conversation). A graduate of this track can do all three. This week is the dress rehearsal and the performance.

You have already built everything. Week 39 made the graph fit the hardware. Weeks 41–44 built and hardened the robot and its safety case, telemetry, and eval suite. Week 45 ramped your interview muscle. Week 46 proved the robot fails well. Week 47 made the work legible and rehearsed the loop. This week you *assemble the defense package*, run a full mock defense against the real rubric, close the last gaps, and present. There is no new robotics content — the content is everything you built, presented to a panel that decides whether you graduate.

## Learning objectives

By the end of this week, you will be able to:

- **Assemble** the complete capstone defense package — the integrated repo with a top-level README, the Mermaid architecture diagram, two videos, the signed safety case, the two chaos-drill postmortems, the operator-dashboard recording, the polished portfolio, and the public retro.
- **Present** a ninety-minute capstone defense: a tight opening (the five-minute pitch), a structured walkthrough of the stack and the videos, the safety case, the chaos drills, and a live Q&A you steer toward your strengths.
- **Defend** every system property in the capstone spec — perception latency, fused-estimate drift, planning, control, the VLA policy, the safety layer, telemetry, fleet heartbeat, OTA-readiness — each against the *measured* acceptance criteria.
- **Present a safety case** to a panel: walk the hazard log, the FMEA, the mitigations, the validation plan, and the residual risk, and defend the claim that "safety does not depend on the smart parts."
- **Map** your robot against the acceptance criteria honestly — 15/20 instructions, < 0.5 m drift, signed safety case, two recovered chaos drills, < 60 s cold-boot — and know, before the panel does, exactly where you stand and what you'd say about any gap.
- **Survive** the live Q&A: three-layer "why" defense across the whole stack, graceful handling of your knowledge edge, and catching a deliberately-false premise instead of agreeing with it.
- **Write** the public retro — the honest one-page "what I'd do differently" — that turns the whole year into a reflective artifact a future employer respects.
- **Run** a full mock defense against the real rubric *before* the real one, find the gaps while they're cheap to fix, and close them.

## Prerequisites

This is the capstone defense; it assumes the *entire track*. Specifically, you arrive with:

- The **integrated capstone** that meets (or honestly falls short against) the acceptance criteria: ≥ 15/20 language-conditioned instructions, < 0.5 m drift over 20 m, < 60 s cold-boot, the full perception → planner → controller → policy stack with the safety layer.
- The **Week 41 signed safety case** — hazard log, FMEA, mitigations, validation plan, residual risk, peer-reviewed.
- The **two Week 46 chaos-drill postmortems** — sensor-dropout and doorway-deadlock — each passing the rubric.
- The **Week 43 telemetry** and **Week 44 eval suite** — your numbers, on the dashboard.
- The **Week 39 latency report** — the proof the autonomy fits the robot's compute.
- The **Week 47 polished portfolio** — three projects, READMEs, diagrams, videos, and the rehearsed five-minute pitch.
- A **panel** (instructor + peer reviewer at minimum) to defend to. Solo-path learners: the mini-project explains how to run the full mock defense with a recording and a structured self-and-peer review — but assemble a panel if you possibly can; defending to strangers is the point.

You do **not** build new robot capability this week. If your robot does not yet clear the acceptance criteria, this week's honest mock defense will tell you exactly which criterion to spend your remaining hours on.

## Topics covered

- The defense package: the seven required deliverables from the capstone spec, what each must contain, and how a panel reads them.
- The ninety-minute defense structure: the opening pitch, the stack walkthrough, the safety-case presentation, the chaos-drill review, and the live Q&A — with time budgets.
- Mapping the robot to the acceptance criteria: each criterion, how it's measured, what evidence proves it, and how to talk about a criterion you partially miss.
- Presenting a safety case to a panel: the hazard log and FMEA as a narrative, the "safety doesn't depend on the smart parts" thesis, and defending residual risk.
- The chaos-drill review: presenting the two postmortems as evidence the robot fails well, and answering the "what else could break?" follow-up.
- The live Q&A as a performance: three-layer "why" across the whole stack, the knowledge-edge answer, catching false premises, and steering toward your strengths.
- The public retro: the honest "what I'd do differently," and why a reflective one-pager is a stronger artifact than a list of wins.
- The full mock defense against the real rubric, and the gap-closing sprint it produces.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target — the gap-closing time is yours to spend on whichever acceptance criterion or defense weakness the mock exposes.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The defense package + the 90-minute structure                  |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Mapping the robot to acceptance criteria; the safety-case talk |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | The chaos-drill review; assemble the package; gap audit        |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     1h       |    0.5h    |     6.5h    |
| Thursday  | The full mock defense against the rubric + debrief             |    0h    |    1.5h   |     1h     |    0.5h   |   1h     |     1.5h     |    0h      |     6h      |
| Friday    | Close the gaps; rehearse the Q&A; write the retro              |    0h    |    0h     |     1.5h   |    0.5h   |   1h     |     2h       |    0.5h    |     5.5h    |
| Saturday  | THE DEFENSE (90 min) + package finalization                    |    0h    |    0h     |     0h     |    0h     |   0h     |     3.5h     |    0h      |     3.5h    |
| Sunday    | Submit the package; the public retro; track close-out          |    0h    |    0h     |     0h     |    1h     |   1h     |     1h       |    0h      |     3h      |
| **Total** |                                                                | **5h**   | **6.5h**  | **5h**     | **3.5h**  | **6h**   | **9h**       | **1.5h**   | **36.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | Defense, safety-case, ISO-framing, and presentation references, current to 2026 |
| [lecture-notes/01-the-defense-package-and-the-ninety-minutes.md](./lecture-notes/01-the-defense-package-and-the-ninety-minutes.md) | The seven deliverables, the 90-minute structure, and mapping the robot to the acceptance criteria |
| [lecture-notes/02-defending-the-safety-case-and-the-live-qa.md](./lecture-notes/02-defending-the-safety-case-and-the-live-qa.md) | Presenting the safety case and chaos drills, surviving the live Q&A, and the public retro |
| [exercises/README.md](./exercises/README.md) | Index of this week's three exercises |
| [exercises/exercise-01-package-checklist.md](./exercises/exercise-01-package-checklist.md) | Audit your defense package against the seven required deliverables |
| [exercises/exercise-02-acceptance-criteria-check.py](./exercises/exercise-02-acceptance-criteria-check.py) | A runnable acceptance-criteria checker that scores your robot against the spec and flags any fail |
| [exercises/exercise-03-defense-qa-bank.py](./exercises/exercise-03-defense-qa-bank.py) | A Q&A drill bank that quizzes you on the questions the panel will actually ask |
| [challenges/README.md](./challenges/README.md) | Index of this week's challenge |
| [challenges/challenge-01-the-full-mock-defense.md](./challenges/challenge-01-the-full-mock-defense.md) | Run the full 90-minute mock defense against the real rubric and close the gaps |
| [quiz.md](./quiz.md) | 13 questions with an answer key |
| [homework.md](./homework.md) | The final deliverables with a grading rubric |
| [mini-project/README.md](./mini-project/README.md) | The complete defense package + the mock defense + the public retro |

## The "panel signs the rubric" promise

Every week in C24 ended in something concrete. The final week ends in the most concrete thing of all: **a panel signs your rubric and you become a Crunch Robotics graduate.** The marker we use here is not `Build succeeded`. It is this, written at the top of your defense package:

```
Capstone acceptance (live-graded):
  Instructions:  17/20      (≥ 15 required)            → PASS
  Drift:         0.38 m / 20 m  (< 0.5 m required)     → PASS
  Cold-boot:     52 s       (< 60 s required)          → PASS
  Chaos drills:  2/2 recovered, operator-detectable    → PASS
  Safety case:   signed by peer reviewer + panel        → PASS
  --> DEFENSE PASSED. Panel signed 2026-XX-XX.
```

If you cannot fill in those numbers — measured, against the spec, with the panel's signature — the defense is not done. Everything in this week exists to get you to that block, honestly.

## A note on honesty

The single most dangerous way to fail the defense is to hide a gap. A robot that clears 14/20 instructions and a candidate who *says so* — "I'm at 14, one short; here's the failure analysis and the two instruction classes that need work" — is in a far stronger position than a candidate who fudges it to 15 and gets caught when the panel reruns the eval. The panel respects an honest gap with a plan more than a hidden one. And the one unforgivable failure, per the spec, is a **safety-relevant defect unaddressed in the safety case** — that fails the capstone regardless of how well the robot demos. Surface every gap. The defense rewards the engineer who knows exactly where their robot stands, including where it falls short.

## Stretch goals

If you finish the regular work early:

- Run the **full mock defense twice**, with two different panels. The second panel asks different questions and finds different gaps; the delta between the two is your true readiness.
- Prepare a **two-minute "if we had another month" slide** — the honest next-steps roadmap. Panels love it; it shows you see past the deadline and think like an owner.
- Defend the **single weakest part of your stack** on purpose — invite the panel to attack it. Surviving an attack on your weakest point is more convincing than a smooth tour of your strongest.
- Write the **track-completion retro** not just as "what I'd do differently" but as advice to a week-1 learner. Teaching is the deepest proof of understanding, and it's a strong portfolio coda.

## Up next

There is no next week. This is the end of C24 · Crunch Robotics. When the panel signs your rubric, you are a graduate: an engineer who can architect, ship, and operate the autonomy stack of a mobile manipulator that takes a natural-language instruction and carries it out, safely, near people, and who can prove it across a table. The capstone goes at the top of your résumé; the safety case and the chaos-drill postmortems win the second-round interview. Go build robots that make the world a little more capable and a lot safer. You earned this.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
