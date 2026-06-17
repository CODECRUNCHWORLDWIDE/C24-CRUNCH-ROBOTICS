# Week 40 — Challenges

One challenge this week, and it is the bridge between the exercises and the mini-project. The exercises gave you the kickoff ritual: a "what I heard" contract restatement, a pre-flight check node, and a telemetry spine. The challenge makes you *prove* — not assert, prove — that a single happy-path, language-conditioned pick-and-place runs with **every layer observable in telemetry and no manual intervention**. That observability property is the entire point of the Week 40 milestone, and it is the property the mini-project's sign-off depends on.

| # | File | What you build | Est. time |
|---|------|----------------|-----------|
| 1 | [challenge-01-observable-happy-path.md](./challenge-01-observable-happy-path.md) | A clean happy-path pick-and-place where perception → planner → controller → policy → safety wrapper are each observable in telemetry, with zero manual intervention, captured as a narratable Foxglove run. | ~2h |

## How challenges differ from exercises

Exercises are guided — they hand you the structure and most of the code. A challenge hands you a spec and acceptance criteria and expects you to architect the solution yourself. There is no starter file. You will reuse your Exercise 2 pre-flight check and Exercise 3 telemetry spine, your composed stack from the mini-project, and your Lecture-1 contract restatement, but the wiring that makes every layer observable, the run that needs no intervention, and the proof-by-narration are yours to assemble.

The acceptance criteria are testable. If you cannot run a command — or play a recording — that demonstrates each checkbox, you have not met it. The challenge's central test is the "narrate the run from the screen" test: a reviewer watching only your Foxglove dashboard can describe what the robot is doing at each moment, layer by layer, without reading a log line. If a layer goes dark on the screen, the layer is invisible, and an invisible layer fails the challenge regardless of whether the robot completed the task.
