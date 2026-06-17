# Week 35 — Challenges

The exercises drill the mechanics. **The challenge makes you the fleet integrator.** You stand up the whole two-robot-plus-merger system, then handle the failure that a real fleet hits constantly: one robot's map frame drifts, the shared map double-walls, and you have to detect it and recover — live, while both robots keep mapping.

## Index

1. **[Challenge 1 — Two-robot shared map with a drifting frame](./challenge-01-two-robot-shared-map.md)** — bring up two namespaced robots, run a live merger producing `/shared_map`, then inject a loop-closure-style jump in one robot's `map` frame. Detect the resulting double-wall, recover the inter-robot transform, and confirm the shared map goes crisp again. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 5 milestone (week 40), where "two simulated robots share a map without collision" is a graded outcome, and for week 36, where the same shared map underpins task allocation. The skill — standing up a multi-robot graph, watching it break in a realistic way, and recovering without taking either robot offline — is exactly what separates someone who "ran the map-merge tutorial" from someone who can operate a fleet.
