# Week 30 — Challenges

The exercises drill the CVAE and temporal ensembling. **The challenge makes you the engineer who has to decide which policy ships** — and defend it with numbers, not reputation. The whole industry has opinions about "ACT vs Diffusion Policy"; the senior move is to run the honest benchmark on *your* task and let the measurements decide.

## Index

1. **[Challenge 1 — The latency shootout](challenge-01-latency-shootout.md)** — profile your ACT and your Week-29 Diffusion Policy *fairly* (warm-up, GPU sync, batch-of-one, deploy precision, median + p99), measure success rate and jerk for both, and produce a defensible "which ships at a 30 Hz budget" recommendation backed by the five-axis comparison table. The trap: an unfair benchmark that flatters one policy. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 4 midterm (Week 32), where the panel asks "you trained three policies — which did you ship, and why?" The only answer that survives scrutiny is a measured comparison with an honest methodology. This challenge *is* that comparison, with the benchmarking rigor that separates a number you can defend from a number you got lucky with.
