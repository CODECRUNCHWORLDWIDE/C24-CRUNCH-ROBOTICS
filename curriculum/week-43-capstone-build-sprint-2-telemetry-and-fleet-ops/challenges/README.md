# Week 43 — Challenges

One challenge this week. It is the operationally load-bearing one: proving that your teleop takeover is *safe*, not just that the button works. This is the exact capability the Week 46 chaos drill (drill 2 — planner deadlock at a doorway) will exercise under live grading, so treat it as a dress rehearsal.

## Index

1. **[Challenge 1 — Clean takeover and return](challenge-01-clean-takeover-and-return.md)** — demonstrate, with a recorded MCAP and an automated checker, that the one-click takeover pauses autonomy, transfers control to teleop, and returns control to autonomy without ever leaving the robot in an inconsistent or unsafe state, with every transition visible on the dashboard. (~90–120 min)

## How challenges differ from exercises

Exercises build a piece and check it works. Challenges are open-ended: you are given acceptance criteria and a hard property to prove, and *how* you prove it is part of the work. The deliverable is evidence — an MCAP recording, a checker script's green output, and a short writeup — not just running code. The instructor reviews the evidence and re-runs your checker.
