# Week 7 Homework

Five practice problems that revisit the week's topics. The full set should take about **6 hours**. Work in your Week 7 Git repository so each problem produces at least one commit you can point to later.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

---

## Problem 1 — Read the `slam_toolbox` parameter source

**Problem statement.** Open the `slam_toolbox` repository on GitHub: <https://github.com/SteveMacenski/slam_toolbox>. Find where the loop-closure parameters are declared and used — `loop_search_maximum_distance`, `loop_match_minimum_response_fine`, `loop_match_minimum_chain_size`. Trace one of them from where it is *declared* (the ROS parameter) to where it is *used* (the Karto scan-matcher / mapper logic in `lib/karto_sdk`). Save a 250-word note at `notes/loop-closure-params.md` explaining:

1. The file(s) where the parameter is declared and where it is consumed.
2. In plain English, what `loop_match_minimum_response_fine` gates — i.e. what "response" is, and what it means for a candidate to be above or below the threshold (tie this back to Olson's correlative scan match, Lecture 1, §1.4).
3. One sentence on why raising it reduces false loop closures *and* increases missed ones.

**Acceptance criteria.**

- `notes/loop-closure-params.md` exists, is 220–280 words, and cites at least two specific filenames or class names from the repo.
- The note correctly identifies the "response" as the correlative-scan-match score (sum over the lookup table at the transformed scan points).
- The note explains the loose-vs-strict trade-off in one sentence.
- File is committed.

**Hint.** Search the repo for `loop_match_minimum_response_fine`. The declaration is in the toolbox node; the use is in `lib/karto_sdk/src/Mapper.cpp`. The "response" is the `ScanMatcher` correlation score.

**Estimated time.** 45 minutes.

---

## Problem 2 — Render an occupancy grid from a saved map by hand

**Problem statement.** Take the PGM/YAML map you saved in exercise 1 (or the mini-project). Write a small Python script `notes/render_grid.py` that loads the PGM, applies the YAML's `occupied_thresh` and `free_thresh` to classify each pixel as occupied / free / unknown, and prints:

1. The grid dimensions (cells) and the real-world size in metres (cells × resolution).
2. The count and fraction of occupied, free, and unknown cells.
3. The world coordinates of the map's bottom-left corner (the YAML `origin`) and of its top-right corner (origin + size).

Then render the classified grid to a PNG with matplotlib (occupied=black, free=white, unknown=grey) and confirm by eye it matches RViz.

**Acceptance criteria.**

- `notes/render_grid.py` loads the PGM and YAML and prints the three items above.
- The printed real-world size matches `width × resolution` and `height × resolution`.
- The rendered PNG visually matches the RViz map (same rooms, same walls).
- The script and the PNG are committed, with a 100-word note interpreting the numbers.

**Hint.** Reuse the PGM reader and `classify` function from exercise 3's analyzer. The YAML `origin` is `[x, y, yaw]` of the bottom-left pixel in the world frame; the top-right is `origin + [width*res, height*res]`.

**Estimated time.** 60 minutes.

---

## Problem 3 — Watch `map → odom` jump on a loop closure

**Problem statement.** Run a mapping session (exercise 1's setup) and, while you drive a loop, record the `map → odom` transform over time. The cleanest way: write a tiny node (or use `tf2_echo` piped to a file, or PlotJuggler from Week 6) that logs the `map → odom` translation `(x, y)` and yaw at, say, 10 Hz. Drive a loop. Plot the three time series. Annotate the *discontinuity* — the jump — at the moment the loop closed (cross-reference the `slam_toolbox` log's `Loop closure found` timestamp).

Write a 150-word note at `notes/map-odom-jump.md` explaining why this jump is *correct behavior* per REP-105 (Lecture 2, §2.7) — and why the *same* jump must NOT appear in `odom → base_link`.

**Acceptance criteria.**

- A plot of `map → odom` `(x, y, yaw)` over time, with the loop-closure moment annotated.
- The note correctly explains that `map → odom` jumps because the back-end re-optimized the estimate, and that the jump is isolated in this link so the controller's smooth `odom → base_link` is undisturbed.
- The jump magnitude (in cm and degrees) is reported — it is the drift the loop closure corrected.
- The note and plot are committed.

**Hint.** `ros2 run tf2_ros tf2_echo map odom` prints the transform; redirect to a file with a timestamp, or subscribe to `/tf` and filter for the `map → odom` pair. PlotJuggler can stream `/tf` directly and show the step.

**Estimated time.** 60 minutes.

---

## Problem 4 — Quantify how node spacing affects the graph

**Problem statement.** Map the same world (off a recorded bag, for repeatability) three times with three values of `minimum_travel_distance`: `0.2`, `0.5`, `1.0` m. For each run, record:

1. The number of graph nodes created (count the `Created new node` log lines, or read it from the serialized graph).
2. Whether loops still closed (and how many).
3. The map quality (coverage and wall thickness, exercise 3's analyzer).

Write the results as a Markdown table at `notes/node-spacing.md` with a 150-word interpretation: how does denser node spacing trade off graph size / CPU against loop-closure opportunity and map quality?

**Acceptance criteria.**

- `notes/node-spacing.md` has a table with three rows (one per `minimum_travel_distance`) and the columns above.
- The interpretation correctly ties smaller spacing → more nodes → more loop-closure opportunities + more CPU/memory, and larger spacing → sparser graph → fewer chances + more drift between nodes (Lecture 1, §1.9).
- All three runs used the *same* bag (controlled experiment).
- File is committed.

**Hint.** Record the bag once (exercise 3 shows how). The node count is the most informative number — `0.2` m spacing on a 60 m drive creates roughly three times as many nodes as `0.5` m. Watch whether the densest run gets slower in real time (a sign you are CPU-bound).

**Estimated time.** 75 minutes.

---

## Problem 5 — Localization vs. mapping: a decision memo

**Problem statement.** Write a one-page decision memo at `notes/mode-decision.md` for a hypothetical deployment: a hospital delivery robot that operates 24/7 in a building whose layout is stable on the scale of months but whose *furniture* (carts, beds, equipment) moves daily. The memo must recommend, with justification, which `slam_toolbox` mode the robot runs (a) when first commissioned in a new wing, (b) during normal daily operation, and (c) what cadence (if any) of re-mapping or lifelong mapping you would adopt, and why.

Address explicitly: why you would *not* run mapping mode in daily operation, why you would *not* default to lifelong mode despite the moving furniture, and what would have to be true about the environment (or the safety case) for lifelong mode to become the right call (Lecture 2, §§2.5–2.6).

**Acceptance criteria.**

- `notes/mode-decision.md` is ~1 page and makes a concrete recommendation for each of (a), (b), (c).
- The memo correctly recommends mapping mode for commissioning, localization mode for daily operation, and treats lifelong mode as a deliberate, justified choice — not a default.
- The memo names a *specific* risk of lifelong mode (the map silently re-drawing under a path planner / safety zone) and a condition under which it is nonetheless warranted.
- The memo cites the relevant lecture sections.
- File is committed.

**Hint.** The production-normal pattern is "map once, localize daily, re-map deliberately when the *structure* (not the furniture) changes." Moving furniture is handled by Nav2's costmap layers (Phase 3), not by re-mapping — a point worth making in the memo. Lifelong mode trades a stable, auditable map for an adaptive one; the safety case has to accept that trade.

**Estimated time.** 60 minutes.

---

## Submission

Push the entire `notes/` directory and any code/plots to your Week 7 Git repository. The instructor reviews by:

1. Reading each note in `notes/`.
2. Re-running any scripts attached (the grid renderer, the node-spacing runs) and confirming the numbers reproduce within reason on the reviewer's machine.
3. Cross-checking the cited URLs are real and the claims in the notes are consistent with the source and the lectures.

A submission whose `notes/` are present and whose runs reproduce is a pass. The most common review-fail is "the note claims a loop closed but the log shows none" — verify your claims against the `slam_toolbox` logs before submitting.

## Rubric

| Problem | Weight | What earns full marks |
|---|---:|---|
| P1 — parameter source | 20% | Correct file trace, correct "response" definition, the trade-off in one sentence |
| P2 — render the grid | 20% | Correct dimensions/sizes/origin, a PNG matching RViz, a sound interpretation |
| P3 — `map → odom` jump | 20% | A plot with the jump annotated, the REP-105 explanation correct, the magnitude reported |
| P4 — node spacing | 20% | Three controlled runs, the table, the size-vs-quality interpretation correct |
| P5 — mode decision memo | 20% | Concrete (a)/(b)/(c) recommendations, lifelong treated as a justified choice with a named risk |

Pass threshold for the homework component is **75%** (i.e. four of five problems substantially correct). The mini-project is graded separately against its own rubric.

If anything is unclear, post the question in the Week 7 channel before the homework deadline.

---

**References**

- `slam_toolbox` README and configuration: <https://github.com/SteveMacenski/slam_toolbox>
- `nav2_map_server` / `map_saver_cli` (the PGM/YAML format): <https://docs.nav2.org/configuration/packages/configuring-map-server.html>
- REP-105 — coordinate frames (the `map → odom` jump): <https://www.ros.org/reps/rep-0105.html>
- Olson — "Real-Time Correlative Scan Matching" (the response score): <https://april.eecs.umich.edu/pdfs/olson2009icra.pdf>
- Macenski et al. — "SLAM Toolbox: SLAM for the dynamic world" (the three modes): <https://joss.theoj.org/papers/10.21105/joss.02783>
