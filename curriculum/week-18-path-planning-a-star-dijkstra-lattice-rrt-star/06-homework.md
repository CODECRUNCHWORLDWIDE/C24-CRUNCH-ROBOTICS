# Week 18 Homework

Six problems that revisit the week's topics and put the planners in your fingers. The full set should take about **5 hours**. Work in your Week 18 Git repository (the same workspace as the exercises and the `crunch_planners` mini-project) so every problem produces at least one commit you can point to in the Phase 3 integration in Week 24.

The headline deliverable is **Problem 4 — the runtime-as-safety fail-safe declaration**, this week's mandatory Phase-3 fail-safe. Treat it as the artifact a safety reviewer reads, not a journal entry.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Use Python 3.12 + numpy + matplotlib. Problems 5 and 6 also use a live Nav2 `planner_server` (bring it up from Week 17); if your sim is broken, the pure-Python comparison is your fallback — say so in your writeup.

---

## Problem 1 — The heuristic-admissibility lab

**Problem statement.** Using your Exercise 2 code, run A* on a fixed grid with four heuristics: zero (= Dijkstra), Euclidean, octile, and `1.3 × octile`. For each, record path length and nodes expanded. Build a table in `notes/week-18/heuristics.md` and classify each heuristic as admissible or inadmissible, with the evidence (does its path length match Dijkstra's?).

**Acceptance criteria.**

- `notes/week-18/heuristics.md` has a row per heuristic with length, nodes expanded, and an admissible yes/no.
- Zero, Euclidean, and octile all match Dijkstra's length (admissible); `1.3 × octile` returns a length ≥ Dijkstra's (inadmissible — flag the rows where it's strictly longer).
- A one-sentence ranking of the admissible heuristics by nodes expanded (octile < Euclidean < zero), with the explanation that the *tighter* admissible heuristic expands fewer nodes.
- Committed.

**Hint.** Use an open or diagonal-rich map so `1.3 × octile` actually returns a longer path on at least some start/goal pairs — on a heavily-walled map an inadmissible heuristic can still stumble onto the optimal length, which is real and worth noting.

**Estimated time.** 40 minutes.

---

## Problem 2 — The weighted-A* trade-off curve

**Problem statement.** Sweep weighted A*'s ε over `[1.0, 1.25, 1.5, 2.0, 3.0, 5.0]` on a maze map. For each ε, record path length and nodes expanded (and wall-clock time). Plot two curves — length vs. ε and nodes-expanded vs. ε — and identify the "knee": the ε that buys most of the node reduction for the least length penalty.

**Acceptance criteria.**

- A plot saved to `notes/week-18/weighted-curve.png` with both curves.
- A `notes/week-18/weighted.md` naming the knee ε and the length penalty and node reduction at that ε vs. ε = 1.
- You confirm every ε's path length stays within ε × the optimal (the bounded-suboptimality guarantee).
- Committed.

**Hint.** The knee is usually around ε = 1.5–2.0: a big drop in nodes for a single-digit-percent length increase. On a maze the misleading heuristic can make high ε *worse* (it chases the Euclidean-close goal down a dead-end corridor) — if you see length spike at high ε, that's the maze punishing greed, and it's worth a sentence.

**Estimated time.** 45 minutes.

---

## Problem 3 — RRT* convergence

**Problem statement.** Run your Exercise 3 RRT* at sample budgets `[250, 500, 1000, 2000, 4000, 8000]` on a fixed obstacle field (fixed seed). For each, record the best path cost found. Plot cost vs. budget and show the asymptotic-optimality convergence — the curve dropping and flattening toward an asymptote.

**Acceptance criteria.**

- A plot `notes/week-18/rrt-star-convergence.png` of best cost vs. sample budget.
- `notes/week-18/rrt-star.md` states the cost at 250 vs. 8000 samples and the approximate asymptote.
- You compare against plain RRT at the same budgets and show RRT does *not* converge (its cost wanders, doesn't monotonically improve).
- Committed.

**Hint.** Average over a few seeds per budget to smooth the curve (RRT* is randomized). The asymptote is the (near-)optimal path cost; RRT* approaches it from above, RRT scatters around a worse value because it lacks `rewire`.

**Estimated time.** 45 minutes.

---

## Problem 4 — The runtime-as-safety fail-safe declaration (headline deliverable)

**Problem statement.** This is the syllabus's Phase-3 fail-safe for this week: *what does the robot do when the planner returns no path, or returns one too slowly to be safe?* Measure your planner's latency distribution, then write a one-page fail-safe declaration at `notes/week-18/failsafe-planner-latency.md` against this template:

1. **Hazard** — one sentence: what physically goes wrong if the planner returns no path (and the robot keeps the last plan), or returns a plan 600 ms late (the world has moved).
2. **Latency budget** — your planner's measured runtime distribution (mean, p95, max) on a representative map, and the budget you set (e.g. 100 ms), with the speed→distance reasoning (at 1.5 m/s, 100 ms = 15 cm of travel on stale info).
3. **No-path response** — what the robot does when the planner returns `None` (controlled stop, signal, replan to a fallback goal or request assist — *not* coast on the last plan).
4. **Too-slow response** — what happens when the planner exceeds the budget (anytime planner returns best-so-far, or hard deadline → stop), and why an *anytime* planner (weighted A*) helps here.
5. **Residual risk** — what this does *not* cover (e.g., a planner that returns a *valid-but-wrong* path quickly — fast and confident is not the same as correct).
6. **Test evidence** — the measured latency table and the observed behavior when you forced a no-path (box the goal in) and a slow plan (a huge map).

**Acceptance criteria.**

- `notes/week-18/failsafe-planner-latency.md` exists, fits on roughly one page (350–550 words), and hits all six headings.
- The latency budget section quotes a **measured p95**, not just a mean, and ties the budget to a speed→distance number.
- The no-path response explicitly rejects "keep the last plan" and specifies a controlled stop.
- The residual-risk section names a real gap, not "none."
- Committed.

**Hint.** Measure with `time.perf_counter()` around your planner over 100 randomized start/goal pairs; report the percentiles with `numpy.percentile(times, [50, 95, 100])`. Force the no-path case by walling the goal in. The honest residual risk: a planner can be *fast and wrong* — it returns a valid path through a region your costmap mis-marked — and latency safety does nothing about correctness; that's what the costmap and perception layers (and Week 17's recovery BT) are for.

**Estimated time.** 1 hour.

---

## Problem 5 — Your A* vs. Nav2's NavFn vs. SMAC

**Problem statement.** On your week-7 costmap, run three planners on the same start/goal: your Exercise 2 A*, Nav2's `NavfnPlanner`, and `SmacPlanner2D` (the SMAC grid planner). Compare path length and runtime. Then switch to `SmacPlannerHybrid` with a `minimum_turning_radius` and compare the path *shape* against the others. Record in `notes/week-18/planner-comparison.md`.

**Acceptance criteria.**

- `notes/week-18/planner-comparison.md` compares your A*, NavFn, and SmacPlanner2D on length and runtime (they should agree on length within a few percent — all grid-optimal).
- You show `SmacPlannerHybrid`'s path differs in *shape*: smoother, turning-radius-respecting curves instead of grid-aligned segments.
- A one-sentence statement of when you'd choose each (grid planners for a diff-drive base; Hybrid-A* when the turning constraint matters).
- Committed.

**Hint.** Swap the planner by editing `planner_server.GridBased.plugin` in your params and restarting. Capture each `/plan` with `ros2 topic echo /plan --once`. NavFn and SmacPlanner2D are both grid-optimal so their lengths match yours; the Hybrid one is the visibly different curve.

**Estimated time.** 40 minutes.

---

## Problem 6 — Wrap your A* as a Nav2 plan-quality checker

**Problem statement.** Write a script `crunch_planners/scripts/plan_check.py` that subscribes to Nav2's `/plan`, runs *your* A* on the same costmap between the plan's endpoints, and reports whether Nav2's plan length is within a tolerance (say 10%) of your A*'s optimal length. It exits `0` if Nav2's plan is within tolerance, non-zero if Nav2's plan is suspiciously long (a sign of a costmap or planner misconfiguration). Demonstrate both outcomes.

**Acceptance criteria.**

- Running it against a well-configured Nav2 prints "plan within tolerance" and exits `0`.
- Running it against a Nav2 with a deliberately bad config (e.g., a huge inflation radius forcing a long detour) prints the length gap and exits non-zero.
- Both runs captured in `notes/week-18/plan-check.md`.
- Committed.

**Hint.** The exit code makes it a regression gate, not a pretty printer. Convert Nav2's `/plan` (a list of `PoseStamped`) to an arc length and compare to your A* cell-path length × resolution. To force the bad case, set `inflation_radius` large so Nav2 takes a wide detour your A* (on a smaller-inflation grid) wouldn't.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Heuristic admissibility lab | 40 min |
| 2 — Weighted-A* trade-off curve | 45 min |
| 3 — RRT* convergence | 45 min |
| 4 — Runtime-as-safety fail-safe (headline) | 1 h 0 min |
| 5 — A* vs. NavFn vs. SMAC | 40 min |
| 6 — Plan-quality checker | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_planners` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 24's integration imports it. Then take the [quiz](./05-quiz.md) with your notes closed.
