# Week 6 — Challenge

One challenge this week. It is harder and more open-ended than the exercises: you take the square-drive infrastructure from Exercise 3, run it as a controlled experiment across speed and turn rate, and then *fix* the dominant systematic error with a calibration you fit from your own data. It is the difference between "my odometry drifts" and "my odometry drifts 1.4% of path length, dominated by heading, and a 0.982 wheel-radius scale brings it to 0.4%." The second sentence is the one you say in a design review.

## Index

1. **[Challenge 1 — Quantify drift vs speed/turn-rate, then calibrate it away](challenge-01-quantify-and-calibrate-drift.md)** — drive the square at three speeds and two turn rates, fit a single calibration correction (wheel-radius scale or UMBmark wheelbase correction) from the closure error, re-run, and demonstrate with numbers that the systematic component drops. ~2 hours.

## How the challenge differs from the exercises

The exercises ask you to *build* the odometry node and *observe* that it drifts. The challenge asks you to *characterize* the drift as a function of the two variables that drive it (speed → slip, turn rate → heading injection) and then *act* on the characterization. You produce:

- A table of closure error / drift across the experimental grid.
- A claim about which error class dominates, backed by the speed-vs-turn-rate signature (Lecture 1, §1.8: systematic error is speed-independent, slip grows with speed).
- A fitted correction and a before/after closure-error comparison proving it helped.

This is the through-line to the rest of the track: Week 10's EKF re-drives this square and you compare *its* drift to your calibrated raw odometry. A reviewer who reads your challenge writeup should be able to predict how much the EKF will improve before they run it.

## Submission

Commit to your Week 6 repository under `challenges/challenge-01-drift-calibration/` with the trajectory CSVs, the plots, the fitted correction, and a 1–2 page `results.md`. The acceptance criteria in the challenge file are the rubric.
