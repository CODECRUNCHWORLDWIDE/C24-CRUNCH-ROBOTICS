# Challenge 1 — Corridor Deadlock: Deconfliction and Its Failure

**Time estimate:** ~90 minutes.

## Problem statement

You are on call. A teammate's two-robot fleet "works fine in the demo" but in your building it freezes: two robots meet nose-to-nose in the single corridor between the east and west wings, and neither moves. The dispatcher keeps the tasks `underway`, the robots report `MOVING` mode but their positions don't change, and an operator has to walk over and shove one robot backward to break it.

You will reproduce this, understand *why* the traffic schedule sometimes resolves it and sometimes can't, and prescribe a fix. The crucial lesson: **a deadlock in a fleet is almost always a map problem, not a code problem.** You will not fix it by editing the dispatcher; you will fix it by editing the nav graph.

## Part A — Make the conflict happen (on a good map)

Start from the RMF office demo, which has a corridor wide enough that the schedule can deconflict.

```bash
ros2 launch rmf_demos_gz office.launch.xml
```

Send two robots toward each other through the same corridor at the same time. The simplest reliable way is two patrols crossing:

```bash
# Robot heads east-to-west through the corridor.
ros2 run rmf_demos_tasks dispatch_patrol -p east_wing west_wing -n 1 --use_sim_time
# Immediately: another robot west-to-east through the same corridor.
ros2 run rmf_demos_tasks dispatch_patrol -p west_wing east_wing -n 1 --use_sim_time
```

(Use the actual waypoint names from the office nav graph — list them with the RMF visualization or by reading the demo's `nav_graph` YAML. The point is two robots, opposite directions, one corridor, overlapping time.)

Watch the deconfliction:

```bash
ros2 topic echo /fleet_states          # watch both robots' mode + location
ros2 node list | grep schedule          # confirm the schedule node is up
```

**Observe and record:** Which robot proceeds and which waits? Does the waiting robot stop at a hold point, slow down, or reroute? On a good map, the schedule's negotiation (Lecture 2 §3.2) makes one robot yield and the other pass — note *which* and reason about *why* (the cost-based outcome, not first-come-first-served).

## Part B — Force a true deadlock (with a bad map)

Now break it on purpose. Author (or edit a copy of) a minimal nav graph with a **single bidirectional corridor and no passing place**: east room → one lane → corridor waypoint → one lane → west room, with nothing else connecting the two rooms. Two robots sent in opposite directions through it have *no feasible joint plan* — the negotiation cannot find a way for both to pass, and you get a true deadlock.

You can build this two ways:

- **The clean way:** use `rmf_traffic_editor` to author a tiny two-room building with one connecting corridor and no passing bay, generate the nav graph, and run a minimal two-robot fleet on it.
- **The fast way:** copy the office nav graph YAML, delete every lane between the east and west wings *except* one single bidirectional corridor lane, and relaunch. (Keep a backup of the original.)

Send the two opposing patrols again. This time:

**Observe and record:** Both robots enter the corridor (or one enters and the other waits at the mouth), the negotiation runs but finds no feasible joint trajectory, and the robots freeze. Capture:
- The `/fleet_states` showing both stuck (mode possibly `MOVING` or `PAUSED`, positions static).
- Any schedule/negotiation log lines indicating a failed or stalled negotiation.
- The wall-clock time the deadlock persists (it does not self-resolve on a truly infeasible map).

## Part C — Prescribe and apply the fix

For the deadlock you forced, produce a fix and prove it works. The fix is **map-level**. Choose and justify one:

1. **Add a passing place.** Insert a short side lane (a bay) off the corridor where one robot can pull aside while the other passes. The negotiation now has a feasible joint plan: one robot waits in the bay.
2. **Make the pinch one-way.** Mark the corridor lane as unidirectional and add a *separate* return lane (a loop). No two robots ever oppose in the same lane. This is how real warehouses lay out aisles.
3. **Add an explicit hold point with capacity reasoning.** A waypoint where a robot can wait that does *not* block the corridor, so a yield is feasible.

Apply your chosen fix to the nav graph, relaunch, send the two opposing patrols again, and show both robots complete their patrols. Record the before (deadlock) and after (both complete) `/fleet_states` traces.

## Your task

Produce a file `challenge-01-deadlock-report.md` with:

1. **Part A finding** — on the good map, which robot yielded, and your explanation of *why* (cost-based negotiation; the first-arriving robot may be the one told to wait — explain when and why).
2. **Part B reproduction** — the bad nav graph you used (paste the relevant lanes), the deadlock trace, and the persistence time.
3. **Part C fix** — which of the three map-level fixes you chose, *why* that one, the edited nav graph, and the after-trace showing both robots complete.
4. **The one-sentence rule** — "a fleet deadlock is a ___ problem, fixed by ___, not by ___."

## Acceptance criteria

- [ ] `challenge-01-deadlock-report.md` with all four sections.
- [ ] Part A correctly identifies the negotiation outcome and explains the cost-based (not FCFS) deconfliction.
- [ ] Part B genuinely deadlocks — both robots stuck, negotiation cannot resolve, does not self-recover. (If it self-recovers, your "bad" map still had a passing option; remove it.)
- [ ] Part C's fix is **map-level** and demonstrably works (both robots complete after the edit).
- [ ] You did *not* attempt to fix the deadlock by editing the dispatcher or the allocation code — and you explain why that wouldn't work.
- [ ] Committed to your Week 36 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The tempting wrong fix is to "make the allocator smarter" — e.g., never assign two tasks that route through the same corridor in opposite directions at the same time. You *can* paper over the symptom this way, and a naive reviewer might accept it. But it is the wrong layer: it couples your task allocator to the building's geometry, it breaks the moment a third robot or a re-route puts two robots in that corridor anyway, and it doesn't help a *human-driven* forklift (read-only fleet, Lecture 2 §1.3) that RMF can't schedule at all. The corridor must be physically passable for two opposing agents, or it must be one-way. That's a map invariant, and the map is where you enforce it. Prescribing "make the allocator avoid the corridor" is the wrong fix and you must not write it as your primary answer.

## Stretch

- **Three robots, one corridor.** Add a third robot and send all three into the (fixed) corridor. Confirm the passing-place fix scales — or find its limit (one bay can let one robot pass at a time; three opposing robots may queue). Measure the throughput.
- **Read the negotiation.** Dig into `rmf_traffic`'s negotiation: find where a conflict opens a negotiation room and how proposals are scored. Write three sentences on the search the negotiation actually runs.
- **Quantify the cost of yielding.** On the good map (Part A), measure how many extra seconds the yielding robot spent versus an unobstructed run. That delta is the "price of sharing the corridor" — the number a fleet-ops engineer reports to justify a second corridor.

## Why this matters

At the Phase 5 milestone (Week 40) you defend your multi-robot coordination. The reviewer will not ask you to recite the RMF architecture — they'll show you two frozen robots and ask "what's wrong, and what's the fix?" If your instinct is "let me add a special case to the allocator," you've failed the question. If your instinct is "the corridor needs a passing place or a one-way rule — this is a map invariant, not a code bug," you've passed. Every fleet-ops rotation eventually hands you a deadlock when a moved obstacle turns a passable corridor into a trap. The engineer who reaches for the map editor, not the code, is the one who keeps the fleet moving.
