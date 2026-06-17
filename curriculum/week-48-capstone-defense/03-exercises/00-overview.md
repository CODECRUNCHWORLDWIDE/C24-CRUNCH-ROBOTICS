# Week 48 — Exercises

Three drills that get you defense-ready. The first audits your package against the seven required deliverables; the second checks your robot against the acceptance criteria; the third drills you on the questions the panel will actually ask. Do them in order — you cannot defend a package you haven't assembled or a robot you haven't honestly measured.

## Index

1. **[Exercise 1 — The package checklist](./exercise-01-package-checklist.md)** — audit your defense package against the seven required deliverables (repo, diagram, two videos, safety case, two postmortems, dashboard recording, portfolio) plus the retro. (~40 min)
2. **[Exercise 2 — The acceptance-criteria check](./exercise-02-acceptance-criteria-check.py)** — a runnable checker that scores your robot against the spec's acceptance criteria and flags any fail, so you know where you stand before the panel does. (~40 min)
3. **[Exercise 3 — The defense Q&A bank](./exercise-03-defense-qa-bank.py)** — a drill bank of the questions a panel asks, with the three-layer-deep structure each answer needs. Self-quiz until you can answer every one with a number. (~50 min)

## How to work the exercises

- **Audit the package early** (Exercise 1). Assembling it always surfaces one deliverable that's "basically done" but not committed and navigable (Lecture 1 §1).
- **Measure honestly** (Exercise 2). The checker flags a fail; better you find it now than the panel finds it live. A safety-relevant defect is the one unforgivable fail (Lecture 1 §4).
- **Drill the Q&A out loud** (Exercise 3). Reading the answers isn't enough; the panel asks them cold, and three layers deep (Lecture 2 §5).
- **Bring a number to everything.** Every claim in the defense is evidenced by a measurement or an artifact (Lecture 1 §4).
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match its shape, you're not done.

## Running the Python exercises

Pure-Python — no ROS2, no GPU. Exercise 2 takes your measured numbers; Exercise 3 is an interactive-style drill bank.

```bash
python3 exercise-02-acceptance-criteria-check.py
python3 exercise-03-defense-qa-bank.py
```

There are no solutions checked in. After you finish, search GitHub for `c24-week-48` to compare with other learners' forks.
