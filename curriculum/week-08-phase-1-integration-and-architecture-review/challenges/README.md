# Week 8 — Challenges

One challenge this week. It is the practical heart of the Phase 1 milestone: prove that your bring-up package is fast, reproducible, and operable by timing a cold-start mapping run of a world you have never seen, all from a single command.

## Index

1. **[Challenge 1 — Cold start to saved map in under fifteen minutes](challenge-01-cold-start-map-under-15.md)** — open-ended. Take a multi-room world you have not mapped before, bring the full stack up with one command, drive it, and save a complete map in under fifteen minutes wall-clock. Report the timed run. (~120 min including practice runs)

## How to work the challenge

- Build on the `crunchbot_bringup` package from exercises 1 and 2 and the `map_run_timer` node from exercise 3. Do not start the challenge until those work.
- Practice on a *known* world first to get your driving and save workflow smooth. The clock starts on the *unseen* world.
- The fifteen minutes is wall-clock from the single launch command to the saved `.pgm`/`.yaml` map pair on disk, including bring-up time. Measure it; do not estimate it.
- The challenge is graded on the timed run *and* the reproducibility — a reviewer must be able to run your one command on the same unseen world and get a comparable result.

The challenge is harder than it looks. The fifteen-minute budget is generous if your bring-up is clean and your driving is deliberate, and impossible if you are still typing `ros2 run` in three terminals or your TF tree throws extrapolation errors halfway through. That is the point: the challenge measures whether your Phase 1 work has become a *product* or is still a *demo*.
