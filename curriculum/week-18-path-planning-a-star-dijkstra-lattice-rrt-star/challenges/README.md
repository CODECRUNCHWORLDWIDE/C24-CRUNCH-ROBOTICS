# Week 18 — Challenges

The exercises drill each planner in isolation. **The challenge makes you the engineer who chooses.** You're handed three maps and four planners, and you have to produce the benchmark table that *justifies* a planner choice — path quality against runtime, the way a real planning decision is made.

## Index

1. **[Challenge 1 — The planner bake-off](challenge-01-planner-bakeoff.md)** — benchmark A*, weighted A*, RRT*, and Nav2's SMAC Hybrid-A* across an open map, a maze, and a narrow-corridor map. Produce a path-length × runtime × success-rate table, then defend, for each map, which planner you'd ship and why. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for every planning decision you'll make from here to the capstone. The skill — running a controlled bake-off and reading the trade-off table to choose a planner *for the state space and the latency budget*, not by habit — is exactly what separates a junior who "knows A* and RRT*" from a senior who can stand up in a design review and say "Hybrid-A* here, weighted A* there, and here's the runtime data that proves it."
