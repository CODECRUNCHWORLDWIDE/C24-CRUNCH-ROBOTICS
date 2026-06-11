# Week 15 — Challenges

The exercises drill the mechanics on two scans. **The challenge makes you the perception engineer who has to report a number.** You chain pairwise ICP over a 100-scan dataset sequence, measure the accumulated drift against ground truth, and — the real skill — explain *where* the drift comes from and *why* it spikes where it does.

## Index

1. **[Challenge 1 — Quantify drift over a 100-scan sequence](challenge-01-drift-over-a-sequence.md)** — run scan-to-scan ICP odometry over 100 consecutive scans from a public dataset (Newer College or KITTI), chain the transforms into a trajectory, compare the final pose to ground truth, and report the drift as a percentage of path length. Then find the sections where drift spikes and explain them with the ICP failure modes from Lecture 2. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Week 16 midterm, where you defend your perception stack to a panel. The reviewer will ask "how does your perception bound drift, and what's your number?" — and the honest answer requires having *measured* it, *located* it, and *understood* it. This challenge is that measurement, rehearsed. The skill — taking a registration pipeline, running it over a real sequence, and reporting a defensible drift number with a root-cause story — is exactly what separates a junior who "ran ICP" from a senior who can tell you, looking at a drift curve, which hallway the robot was in when the estimate went bad.
