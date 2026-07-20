# Week 47 Homework

Six deliverables that make your work legible and your defense sharp. The full set should take about **6 hours**. Work in your capstone repo (or a dedicated portfolio repo) so each deliverable is a commit a Week 48 reviewer can open.

The headline deliverables are **Problems 1 and 4 — the five-minute pitch and the full-loop debrief**, the two things Week 48 tests most directly. Treat the portfolio as something a stranger reads, not something you admire.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

At the top of your portfolio's `README.md` (or `week-47/README.md`), write the marker block once you've run the loop and the scorer:

```
Loop mock (5 rounds): intro 8/10 · technical 26/30 · system-design 24/30 ·
                      behavioral 17/20 · culture 9/10   → 84/100  (weakest: system-design pacing)
Portfolio: 3 READMEs pass the scorer · 3 Mermaid diagrams · 3 videos all ≤ 3:00
Fix before W48: system-design clock management (rehearse the 7-phase method twice)
```

If you can't fill those in honestly, the homework isn't done.

---

## Problem 1 — The five-minute pitch (headline)

**Problem statement.** Write, record, and time your five-minute capstone pitch (Exercise 1): problem → stack → one hard decision → one failure survived → quantified result.

**Acceptance criteria.**
- `pitch-script.md` (≤ 600 words) and a recording **under 5:00**.
- The problem is one concrete sentence before any how; the hard decision names a rejected alternative; the failure is your real chaos drill with a detection time; the result is a number.
- Committed.

**Hint.** Time it. If you had to rush to fit 5:00, the script is too long — cut, don't speed up (Lecture 1 §5). The result must be a number from your eval suite or latency report, not "it worked well."

**Estimated time.** 50 minutes.

---

## Problem 2 — Three senior-bar READMEs

**Problem statement.** Polish the README for each of your three flagship projects to the senior bar (Lecture 2 §1) and pass Exercise 2's scorer on each.

**Acceptance criteria.**
- Three READMEs, each with: what-and-why paragraph (before any install step), architecture diagram, quickstart, results-with-numbers, limitations.
- Each scores a pass on `exercise-02-readme-scorer.py`; paste the scores.
- Committed.

**Hint.** The most common miss is opening with "## Installation" — move the what-and-why paragraph to the top (Lecture 2 §1.1). The limitations section is the senior tell; write a real one for each (Lecture 2 §1.5).

**Estimated time.** 75 minutes.

---

## Problem 3 — Three Mermaid diagrams + the progression

**Problem statement.** Draw a Mermaid architecture diagram for each project (source + PNG) and write `portfolio.md` stating the three-project progression.

**Acceptance criteria.**
- Three diagrams, each grouped with subgraphs, directional, and including the safety layer; source in the README + a PNG export.
- A peer who hasn't seen your code can read each diagram correctly (note who tested it).
- `portfolio.md` frames the three as one trajectory (perception → safely-shipped policy → integrated robot).
- Committed.

**Hint.** Draft in the Mermaid Live Editor, then paste the source into the README (it renders on GitHub). Most candidate diagrams omit the safety layer — including it signals Week 41 thinking (Lecture 2 §2.2).

**Estimated time.** 60 minutes.

---

## Problem 4 — Run and debrief the full loop (headline)

**Problem statement.** Run the five-round mock (the challenge) with a senior reviewer, score it with both graders, and feed the scores into Exercise 3.

**Acceptance criteria.**
- `loop-debrief.md` with per-round scores from both graders, the weighted total, and the self-vs-interviewer gap.
- The two weakest rounds named with a concrete fix scheduled before Week 48.
- `self-grade.txt` — Exercise 3's output with your real numbers.
- The marker block at the top of your portfolio README filled in.
- Committed.

**Hint.** If you rated yourself 4+ above your interviewer on a round, that's a finding — name it and fix it, don't hide it (Lecture 1 §2; Exercise 3). The Week 48 panel won't go easy, so a mock you went easy on taught you nothing.

**Estimated time.** Covered by the mini-project's loop time; budget 30 minutes here for the write-up and tool run.

---

## Problem 5 — Three walkthrough videos

**Problem statement.** Record a ≤ 3-minute walkthrough video per project (Lecture 2 §3): result first, stack over the diagram, one memorable moment, results + a limitation.

**Acceptance criteria.**
- Three videos, each ≤ 3:00, scripted with voiceover, result shown in the first 15 seconds.
- Each passes the 1.5x test (still followable when sped up).
- Links/files committed or referenced in the project READMEs.
- Committed.

**Hint.** Write the voiceover script first and time it (~120 wpm → ~360 words for 3 min). Record the dashboard segment in Foxglove. Watch each back at 1.5x; if it's a blur, you packed too much in — cut (Lecture 2 §3.2).

**Estimated time.** 75 minutes.

---

## Problem 6 — The clone-and-run check

**Problem statement.** Clone each project to a fresh machine (or a clean container) and run the quickstart exactly as written. Fix every break.

**Acceptance criteria.**
- `clone-and-run.md` recording, per project: did the quickstart run cold? What broke? What you fixed.
- Every break (missing dep, hardcoded path, undocumented model file) is fixed in the README or the repo.
- Committed.

**Hint.** You'll find a globally-installed dependency you forgot to list, or a model file that isn't in the repo. Every one of those is a reviewer forming a bad opinion in real time (Lecture 2 §5). This is the highest-leverage 30 minutes of the week.

**Estimated time.** 45 minutes.

---

## Grading rubric (100 points)

| Problem | Points | Full marks |
|---------|-------:|-----------|
| P1 — Five-minute pitch | 18 | Under 5:00; all five parts; rejected alternative + real failure + numeric result |
| P2 — Three senior-bar READMEs | 18 | All pass the scorer; what-and-why first; numeric results; real limitations |
| P3 — Diagrams + progression | 16 | Three diagrams (safety layer included) read by a peer; `portfolio.md` states the trajectory |
| P4 — Full-loop debrief | 22 | Both graders' scores; honest gap; two weakest rounds + scheduled fix |
| P5 — Three walkthrough videos | 18 | All ≤ 3:00, result-first, scripted voiceover, pass the 1.5x test |
| P6 — Clone-and-run | 8 | Each project run cold; every break fixed |

**Pass threshold: 75/100.** Note the weighting: the full-loop debrief (22) and the pitch (18) carry the most, because the loop and the pitch are what Week 48 tests directly and what an interview turns on. A homework set with a polished portfolio but an inflated debrief, or a pitch you never timed, fails those problems regardless of the rest — they're the load-bearing ones.

---

## Why this homework matters

Every problem here is a rehearsal for Week 48 and for the real interview after it. The pitch is your defense opening line. The READMEs and diagrams are what the panel — and a recruiter — read first. The videos are what gets watched before anyone meets you. The loop debrief is your final-week prep schedule. The clone-and-run is the difference between a reviewer who keeps reading and one who closes the tab. Nothing here is busywork; it's the work of making forty-six weeks of robotics *legible* to the people who decide your career. The robot is done. This week is making sure it gets seen.
