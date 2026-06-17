# Challenge 1 — Defend the Perception Stack to a Panel

**Time estimate:** ~2 hours (after the fused node is composed). **No starter file** — you present your own stack.

## The challenge

Conduct a full **midterm-defense rehearsal**: present your fused perception stack to a panel and answer the standard architecture-review questions against the rubric. The panel is a peer, an instructor, or — if you must — yourself with the question list and a brutally honest stance. The goal is to surface every weakness *in rehearsal*, where it costs nothing, before the graded midterm, where it sends you back a week.

This is the hard half of Week 16. The easy half was building the node. The hard half — the half this challenge grades — is *defending* it to someone who didn't build it, with a block diagram, a latency budget, a failure-mode table, and measured numbers, answering "why that choice?" and "what happens when X fails?" without flinching. A senior robotics engineer can defend their stack to a skeptical room; this challenge makes you do it before it's graded.

## Why this is the right challenge for Week 16

The Phase 2 midterm is a live architecture review and a *hard gate* — failures send you back to the offending week. The single highest-leverage preparation is to *run the review first*, against your own stack, with someone playing the panel. Observability of your own weaknesses is not a nicety you add after the node works — it is the difference between a defense you can deliver and a defense you improvise on stage. The exercises gave you the artifacts (the brief, the latency probe, the association); this challenge makes you *use* them under questioning, which is the only way to find the question you can't answer before the panel finds it for you.

## What you must prepare (the brief)

You already have the pieces from Exercise 1 and the homework. Assemble them into the one-page **perception architecture brief** (Lecture 2 §2.4):

1. **The block diagram** — inputs, stages, output, topic names on the edges.
2. **The interface-contract table** — every seam's topic/type/frame/rate/QoS (Exercise 1).
3. **The latency budget** — the block diagram with measured per-hop costs, the critical path, and the p50/p95/p99 from the latency probe (Exercise 2).
4. **The failure-mode table** — one row per failure (LiDAR dropout, ICP degenerate, ambiguous association, stale detection, budget blowout): symptom, gate that catches it, degraded behavior.
5. **The measured numbers** — latency p95, drift (m / path length), association rate (% of objects fused vs. LiDAR-only), each with the script that produces it.

## The panel's question bank

The panel works through these. Have an answer for every one *before* the rehearsal. (A peer playing the panel should ask them in roughly this order — the order a real panel reads a stack, Lecture 2 §2.3.)

**On the architecture:**
1. Draw your data flow in thirty seconds. What are the inputs, the stages, the output?
2. Why is `/perception/objects` in the `map` frame and not `base_link`?
3. Why `best-effort` on `/points` but `reliable` on `/perception/objects`?

**On the latency:**
4. What's your end-to-end latency — p95, under load, sensor-stamp to publish?
5. Where does the time go? Which hop dominates the critical path?
6. If you had to cut 10 ms, which hop would you cut and how?

**On the frames and timing:**
7. At what stamp do you look up the transform to put a detection in `map`? Why?
8. A detection arrives 150 ms stale. What does your node do?

**On the fusion:**
9. How do you associate a 2D detection with a 3D cluster? What if there's no match?
10. Two cups are on the bench. What does your node publish?

**On robustness:**
11. The LiDAR drops out mid-run. What happens to your fused estimate?
12. The ICP hits a degenerate corridor and returns a wrong transform. How does that not corrupt your state estimate?

**On the numbers:**
13. What's your drift? Where does it get worse? Can you run the script for me?

## Acceptance criteria

- [ ] A committed `perception-brief.md` with all five sections (block diagram, contract table, latency budget, failure-mode table, measured numbers).
- [ ] A `defense-rehearsal.md` recording: who played the panel, which of the 13 questions you answered confidently, and — honestly — which you *couldn't*, with an action item for each gap.
- [ ] Every "couldn't answer" gap is closed before you mark the challenge done — either by fixing the stack or by being able to answer (a defensible "here's the trade-off I made and why").
- [ ] At least the latency p95 and the drift are *measured numbers with scripts* you ran in front of (or for) the panel, not asserted.
- [ ] The frame/timing answer (Q7) is correct: you transform detections at the *detection's acquisition stamp* via tf2 time-travel, not at `now()`.
- [ ] The robustness answers (Q11, Q12) name the specific gate (stamp-age, ICP-health-covariance-inflation) and the degraded-but-bounded behavior, not "it would break."
- [ ] Committed to your Week 16 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The question that exposes most students is Q4 — "end-to-end latency, p95, under load, sensor-stamp to publish." The trap is answering with a *component* number: "YOLO runs at 12 ms." That's the inference time of one hop, not the end-to-end path latency, and it's measured idle, not under load. The panel will follow up: "from the sensor stamp? with the clustering also running? p95 or mean?" — and if you measured the wrong thing, you have no answer. **Measure the path, with the whole graph live, at the 95th percentile, before the rehearsal** (Exercise 2). The student who brings "p95 is 28 ms, here's the probe, the critical path is the YOLO hop" passes; the student who brings "it's fast, YOLO is 12 ms" does not. Confusing a hop's latency for the path's latency is the single most common way to fail Q4, and it's entirely avoidable by measuring the right thing.

## Stretch

- **Record the rehearsal.** A 5-minute screen recording where you narrate the brief and answer three questions, so you can watch yourself and catch the hedging and the vague numbers.
- **Adversarial peer.** Have a peer who *didn't* see your stack try to break your numbers — "I don't believe the 28 ms; show me." The number that survives a skeptic survives the panel.
- **Inject a failure live.** During the rehearsal, kill the LiDAR (`ros2 lifecycle deactivate` or a process kill) and narrate what the dashboard/telemetry shows — proving the robustness answer (Q11) is real, not theoretical.

## Why this matters

The Phase 2 midterm is the first hard gate, and it grades the *defense*, not just the code. Two students with identically good perception nodes get different grades if one can defend it and one can't. This challenge is the rehearsal that closes that gap. And it's the same format you face three more times — Week 32, Week 40, Week 48 — each higher-stakes than the last. The student who learns to defend a stack here, calmly, with a brief and the numbers, walks into every later review prepared. The one who improvises here improvises at the capstone defense too, where the stakes are graduation. Rehearse now. It's the cheapest defense you'll ever run.
