# Week 36 — Challenges

The exercises drill the allocation math. **The challenge makes you the fleet-ops engineer.** You're handed a two-robot fleet that contends for a single corridor, and you have to make the contention happen on purpose, watch the deconfliction (or the deadlock), and prescribe the fix — which, as you'll learn, is usually in the *map*, not the code.

## Index

1. **[Challenge 1 — Corridor deadlock](./challenge-01-corridor-deadlock.md)** — drive two robots into a head-on corridor conflict, observe how the traffic schedule negotiates (or fails to), force a true deadlock with a bad nav graph, and prescribe the map-level deconfliction (passing place / one-way lane / hold point). (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 5 milestone in Week 40, where you defend your multi-robot coordination. The skill — looking at two frozen robots and knowing *instantly* whether the fix is a code change or a map change — is exactly what separates a junior who "ran the RMF demo once" from a senior who can keep a real fleet moving at 3 a.m. when a moved pallet turns a two-way corridor into a deadlock trap.
