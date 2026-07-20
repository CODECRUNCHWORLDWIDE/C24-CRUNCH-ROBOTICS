# Week 48 Homework

The final homework of C24. Six deliverables that assemble, verify, and defend your capstone. The full set should take about **6 hours** (the defense itself is in the mini-project). Work in your integrated capstone repo so every deliverable is a public commit a panel — and a future employer — can open.

The headline deliverables are **Problems 2 and 5 — the acceptance-criteria table and the public retro**: the honest map of where your robot stands, and the reflective close of the whole year.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

At the top of the integrated repo's `README.md`, place the marker block once the panel has signed:

```
Capstone acceptance (live-graded):
  Instructions:  17/20      (≥ 15 required)            → PASS
  Drift:         0.38 m / 20 m  (< 0.5 m required)     → PASS
  Cold-boot:     52 s       (< 60 s required)          → PASS
  Chaos drills:  2/2 recovered, operator-detectable    → PASS
  Safety case:   signed by peer reviewer + panel        → PASS
  --> DEFENSE PASSED. Panel signed 2026-XX-XX.
```

If you can't fill it in honestly with measured numbers, the work isn't done.

---

## Problem 1 — The package audit

**Problem statement.** Run Exercise 1's checklist. Assemble the seven required deliverables + the retro into the integrated repo with a top-level README that routes a reader to each.

**Acceptance criteria.**
- `package-audit.md` with every item marked and a verification note (what you opened/played/ran to confirm it).
- The top-level README routes a stranger to all seven deliverables in under a minute.
- Every gap has a dated plan; any missing *safety* deliverable is flagged as top priority.
- Committed.

**Hint.** The deliverables most often "done but not really": the top-level README as a router, the PNG diagram export, and unambiguous Path-B video labels (Lecture 1 §1; Exercise 1 hint).

**Estimated time.** 40 minutes.

---

## Problem 2 — The acceptance-criteria table (headline)

**Problem statement.** Run Exercise 2 with your real measured numbers. Build the honest acceptance-criteria table with evidence links for every criterion.

**Acceptance criteria.**
- The table (in the repo README and as `acceptance.md`) with each criterion, its bar, your measured result, the evidence link, and the status.
- Every number is measured and evidenced (eval bag, drift comparison, timed boot, postmortems, signed safety case).
- No unaddressed safety-relevant defect (if one exists, fixing it is your top priority this week).
- Committed.

**Hint.** Present this table *yourself* in the defense; don't wait to be asked (Lecture 1 §4). A partial miss gets the honest number plus a failure analysis and fix plan — that's a strong position, not a weak one.

**Estimated time.** 50 minutes.

---

## Problem 3 — The safety-case presentation

**Problem statement.** Prepare the safety-case presentation: the "doesn't depend on the smart parts" narrative, the Swiss-cheese answer to "what if X fails," and the quantified residual risk.

**Acceptance criteria.**
- `safety-presentation.md` outlining the narrative order (intended use → hazards → FMEA → layered mitigations → validation → residual risk).
- A written Swiss-cheese answer to at least two "what if X fails" questions.
- The residual risk named, quantified, and standard-framed (e.g. against ISO 13482), with a pointer to its validation.
- Committed.

**Hint.** The flinch is claiming no residual risk; the senior move is quantifying it (Lecture 2 §3). "≤ 1.6 cm travel at 0.2 m/s in the 80 ms clamp-engage gap, below the ISO contact-force threshold, confirmed by the bump test."

**Estimated time.** 60 minutes.

---

## Problem 4 — Drill the defense Q&A

**Problem statement.** Run Exercise 3's Q&A bank out loud, three layers deep, with a number at the marked layer. List the questions you can't hold and close them.

**Acceptance criteria.**
- `qa-prep.md` listing, per bank question, whether you can hold it to three layers and the number you cite.
- The questions you *couldn't* hold are listed with a fix (the artifact to re-read, the derivation to redo).
- You can catch both planted false premises (EKF-is-exact, INT8-is-free).
- Committed.

**Hint.** Reading the answers isn't enough; the panel asks them cold (Lecture 2 §5). Drill out loud with a peer playing the prober, and have them dig past your prepared three layers to find your real edge.

**Estimated time.** 50 minutes.

---

## Problem 5 — The public retro (headline)

**Problem statement.** Write the one-page public retro: specific technical regrets with transferable lessons, plus the decision you're proud of and why it held.

**Acceptance criteria.**
- `retro.md`, one page, public, with 2–3 *specific* regrets (not platitudes), each ending in a transferable principle.
- At least one thing you'd keep, with why it held up.
- Honest enough that a thoughtful interviewer learns something true about how you work.
- Committed.

**Hint.** "I'd manage time better" is a platitude; "I'd build the latency budget in week 1, not week 39 — retrofitting meant re-profiling a graph I could have measured all along" is a real lesson (Lecture 2 §6). The retro is the artifact a thoughtful interviewer reads closest.

**Estimated time.** 45 minutes.

---

## Problem 6 — The mock-to-real bridge

**Problem statement.** After the mock defense (the challenge), write the bridge: the gaps it found, the fixes you made, and the final readiness check before the real defense.

**Acceptance criteria.**
- `mock-debrief.md` with the mock panel's rubric scores, the two weakest segments, and the dated gap-closing plan.
- Each gap (criterion short, question you couldn't hold, safety hole) is closed or honestly carried with a plan — safety holes closed first.
- A one-line readiness statement: where you stand against the spec going into the real defense.
- Committed.

**Hint.** The mock's whole value is finding the gaps now (Lecture 1 §6). Running long is the most common finding; if you did, the fix is cutting the walkthrough so the Q&A survives, not talking faster.

**Estimated time.** 45 minutes.

---

## Grading rubric (100 points)

| Problem | Points | Full marks |
|---------|-------:|-----------|
| P1 — Package audit | 14 | All seven deliverables + retro committed, navigable; gaps dated |
| P2 — Acceptance-criteria table | 22 | Honest, measured, evidenced; no unaddressed safety-relevant defect |
| P3 — Safety-case presentation | 16 | "Doesn't depend on the smart parts"; Swiss-cheese answers; quantified residual risk |
| P4 — Q&A drill | 16 | Three layers + a number per question; both false premises caught; edges named |
| P5 — Public retro | 16 | Specific technical regrets, transferable lessons, what you'd keep and why |
| P6 — Mock-to-real bridge | 16 | Mock debrief; gaps closed (safety first); readiness statement |

**Pass threshold: 75/100.** The capstone itself passes per the spec's acceptance criteria, live-graded by the panel — that is the binding gate. Note the weighting: the acceptance-criteria table (22) carries the most, because an honest, evidenced map of where your robot stands is the foundation of the whole defense. A homework set with a fudged acceptance number, or an unaddressed safety defect, fails regardless of the rest — they're the load-bearing ones.

---

## Why this homework matters

This is the last homework you'll do in C24, and every problem is the defense itself, broken into pieces you can rehearse. The package audit is what the panel reads. The acceptance table is the honest map of where you stand. The safety presentation is where they decide to trust you near people. The Q&A drill is where they find your edge. The retro is the reflection an employer respects most. And the mock-to-real bridge is how you find the gaps while they're cheap. Do it honestly, close the gaps, and present the robot you actually built. When the panel signs, you are a Crunch Robotics graduate — an engineer who can architect, ship, and operate an autonomous mobile manipulator, safely, near people, and prove it across a table. You earned this.
