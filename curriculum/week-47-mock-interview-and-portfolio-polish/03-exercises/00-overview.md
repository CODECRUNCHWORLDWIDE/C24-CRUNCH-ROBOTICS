# Week 47 — Exercises

Three drills. The first writes and times your capstone pitch; the second and third are runnable Python tools that grade your portfolio READMEs and your loop mock. Do them in order — exercise 3 grades the mock that the challenge runs.

## Index

1. **[Exercise 1 — The five-minute pitch](./exercise-01-five-minute-pitch.md)** — write, record, and *time* your five-minute capstone pitch (problem → stack → one hard decision → one failure survived → quantified result). (~50 min)
2. **[Exercise 2 — The README scorer](./exercise-02-readme-scorer.py)** — a runnable tool that checks a portfolio README against the senior bar (what-and-why paragraph, architecture diagram, quickstart, results-with-numbers, limitations). Run it on all three READMEs. (~40 min)
3. **[Exercise 3 — The loop scorecard](./exercise-03-loop-scorecard.py)** — feed your five-round mock scores into the rubric tool, get a weighted total, and have it rank your two weakest rounds for the pre-Week-48 fix. (~30 min)

## How to work the exercises

- **Time the pitch** (Exercise 1). A pitch you've never timed runs long and meanders in the room (Lecture 1 §5). Record it; the recording is the deliverable.
- **Run the scorer on all three READMEs** (Exercise 2), not just the capstone. The reviewer opens whichever one catches their eye first.
- **Grade the loop honestly** (Exercise 3). An inflated mock is a lie the Week 48 panel uncovers for free.
- **Bring a number to everything.** The exercises reward concrete results (a latency p95, an eval-suite count) over adjectives, because the loop does (Lecture 1 §2).
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match its shape, you're not done.

## Running the Python exercises

Pure-Python tools — no ROS2, no GPU. Exercise 2 reads a Markdown file; exercise 3 reads your scores.

```bash
python3 exercise-02-readme-scorer.py            # scores the built-in sample, then run on your READMEs
python3 exercise-02-readme-scorer.py path/to/your/README.md
python3 exercise-03-loop-scorecard.py
```

There are no solutions checked in. After you finish, search GitHub for `c24-week-47` to compare with other learners' forks.
