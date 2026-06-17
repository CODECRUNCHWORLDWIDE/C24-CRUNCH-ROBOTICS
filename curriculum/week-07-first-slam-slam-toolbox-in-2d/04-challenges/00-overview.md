# Week 7 — Challenge

One challenge this week. It is harder and more open-ended than the exercises: you deliberately *break* SLAM by building a world where a loop closure is hard to find, observe the broken map fold or double, and then *fix* it by tuning `slam_toolbox`'s loop-closure parameters until the loop closes — and you document the exact constraint that fixed it. It is the difference between "SLAM works" and "the loop did not close because `loop_search_maximum_distance` was 3 m and my accumulated drift was 3.4 m, so the true revisit was never even a candidate; raising it to 6 m made the candidate appear and the fine response of 0.52 cleared the 0.45 gate." The second sentence is the one you say in a design review, and it is the one that proves you understand SLAM rather than just running it.

## Index

1. **[Challenge 1 — Force a missed loop closure, then tune it closed](./challenge-01-force-and-fix-a-loop-closure.md)** — construct (or modify) a world where `slam_toolbox` *misses* a real loop closure and produces a visibly inconsistent map (doubled walls / a folded corridor). Diagnose *why* the loop was missed. Tune the loop-closure parameters until it closes automatically. Prove it with a before/after map and document the single constraint that made the difference. ~2 hours.

## How the challenge differs from the exercises

The exercises ask you to *run* SLAM and *observe* that, when it works, loops close and the map is consistent. The challenge asks you to operate at the **knife-edge of Lecture 1, §1.6**: the gap between "loose enough to catch a true loop" and "strict enough to reject a false one." You produce:

- A world (or a drive) that reliably reproduces a *missed* loop closure — a real revisit the front-end fails to match.
- A diagnosis naming *which* mechanism failed: the candidate search distance, the chain size, or the response threshold (these are the three knobs from Lecture 2, §2.2's loop-closure group).
- A confirmation that the loop *can* close — using the RViz panel's **manual loop closure** to add the edge by hand and watch the back-end fix the map (Lecture 2, §2.9). This proves the back-end was never the problem; the *front-end candidate/threshold logic* was.
- A tuned parameter set that makes the loop close *automatically*, with a before/after map and the one-line statement of the constraint that fixed it.

This is the through-line to the rest of the track: every estimation system you build after this — the EKF (Week 10), AMCL (Week 11), the 3D SLAM stacks of Phase 2+ — has the same loose-vs-strict trade-off in its data-association step. A reviewer who reads your challenge writeup should be convinced you can tune a SLAM front-end without flailing, because you did it once, deliberately, with a documented cause and fix.

## A note on the danger of "just lower the threshold"

The lazy fix for a missed loop closure is to crank every loop-closure parameter to its loosest setting until *something* matches. Resist it. A threshold low enough to catch every true loop is also low enough to catch *false* ones, and a false loop closure does not bend your map — it *folds* it, confidently and cleanly (Lecture 1, §1.8, experiment 2). The challenge grades you on closing the *true* loop without opening the door to *false* ones. The disciplined approach is to find the *minimal* change that closes the true loop — raise the search distance just enough that the real candidate appears, lower the response gate just enough that the real match clears it — and to argue why your change does not also admit a false positive in this world. "I lowered every threshold to zero and it closed" fails the challenge even if the map looks right, because it would fold on the next symmetric corridor.

## Submission

Commit to your Week 7 repository under `challenges/challenge-01-loop-closure/` with the world file (or the bag of the failing drive), the before/after maps (PGM + RViz screenshots), the two parameter files (failing and fixed), and a 1–2 page `results.md`. The acceptance criteria in the challenge file are the rubric.
