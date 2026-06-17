# Week 13 — Challenges

The exercises walk the deployment path. **The challenge makes you the edge engineer with a budget to hit.** You're handed a detection pipeline that's too slow, and you have to profile it, find where the milliseconds actually went, and optimize the right stage to get under a fixed latency budget — the core skill of edge robotics perception.

## Index

1. **[Challenge 1 — Hit the latency budget](./challenge-01-hit-the-latency-budget.md)** — take a detection pipeline that misses a 30 ms budget, profile it per-stage, identify the real bottleneck (which is often *not* the model), apply the right optimization, and produce a latency block diagram that proves you cleared the budget. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 2 midterm in Week 16 (the "30 ms perception cycle" gate) and for the Week 39 edge-optimization week. The reviewer will point at your pipeline and ask "where do your milliseconds go, and what's your next optimization?" — and a latency block diagram with the bottleneck circled is the answer that separates an engineer who *ran* a model from one who *deployed* it to a budget. Every edge-robotics interview eventually asks "how would you make this faster?"; the engineer who profiles before optimizing answers it right.
