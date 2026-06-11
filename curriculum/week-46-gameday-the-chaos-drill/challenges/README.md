# Week 46 — Challenges

One challenge this week, and it *is* the week: the live, graded gameday. Both drills, on the clock, with an adversary injecting the failures and a stopwatch running. This is the syllabus's live-graded chaos drill (5% of the track) — there is no bigger single test of whether your robot is real.

## Index

1. **[Challenge 1 — Survive gameday](challenge-01-survive-gameday.md)** — run both drills live (sensor dropout mid-task, planner deadlock at a doorway), recover or safe-abort inside 60 seconds with operator-detectable events on the dashboard, and write a blameless postmortem for each. (~3 hours including both drills and both postmortems)

## How to work the challenge

- **Bring your Exercise 1 designs.** You grade reality against your *prediction*; without the design, the drill is a demo (Lecture 1 §6).
- **Test the safety path first.** Confirm the E-stop latches under each injection before you run the graded drill (Lecture 2 §1).
- **Bag everything.** `ros2 bag record -a`. The postmortem timeline comes from data.
- **Detection, not crash-avoidance, is the bar.** A robot that detected and safe-aborted *passed*; a robot that sailed through on stale data *failed* (Lecture 2 §6).
- **The postmortem is half the grade.** Surviving and being unable to explain why is not a pass.
