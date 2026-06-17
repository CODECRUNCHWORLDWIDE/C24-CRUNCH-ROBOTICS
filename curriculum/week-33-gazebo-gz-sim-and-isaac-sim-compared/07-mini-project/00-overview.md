# Mini-Project — `crunchbot_sim_compare`: A Reproducible, Metric-Driven Sim Comparison Harness

> Build a reusable harness that runs the *same* robot and the *same* behavior against any simulator behind the ROS2 bridge, captures the four comparison metrics automatically, and emits a committed comparison report — so "which sim?" is answered by a regenerable table, not a remembered impression.

This is the artifact that turns the challenge's one-off comparison into a tool you run every time the question comes up — when a new Gz release lands, when you finally get an Isaac box, when a teammate claims a config is faster. It is the measurement spine of Phase 5, and next week (Week 34) you extend it into a *domain-randomization* harness by adding "vary the world, hold the robot, measure the gap." Build it sim-agnostic now and it carries forward.

**Estimated time:** ~11 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This harness becomes your standing sim-evaluation tool. **Week 34** adds a randomization layer on top of the same metric-capture core to measure the sim-to-real gap; **Week 40** uses it to sanity-check the capstone system's sim performance before the milestone. The sim-agnostic, config-driven design means a new simulator is a new config, not a rewrite.

**Suggested order of work (so you don't get stuck):**

1. Start with `metrics.py` — lift the Exercise-2 `SimMetrics`, add the sensor-quality stat, and get `test_metrics.py` green. This is pure logic and needs no sim; do it first.
2. Build `runner.py` against *one* sim (Gz/DART). Get a single result JSON out, with the under-sample guard working.
3. Add `report.py` and confirm a one-sim report renders.
4. Add a *second* config (Gz/Bullet on Path B, or Isaac on Path A) and confirm the report's side-by-side and "differs in" line.
5. Polish: the README, the tests, the fairness warnings.

Do not try to build all three deliverables at once against two sims — you'll be debugging the harness and the sim simultaneously and won't know which is broken. One piece, one sim, then widen.

---

## What you will build

A small ROS2/Python package `crunchbot_sim_compare` with three deliverables:

1. **`crunchbot_sim_compare/metrics.py`** — the metric core (lift the `SimMetrics` class from Exercise 2 and harden it): from `/clock` + a sensor topic, compute RTF, mean step-time, sensor Hz, and a sensor-quality statistic (e.g., scan range mean/variance), plus a contact counter if your sim exposes contacts. Pure logic, unit-tested, ROS-decoupled.
2. **`crunchbot_sim_compare/runner.py`** — the harness node: given a **run config** (which sim launch, which behavior, the window, the metrics), it triggers the fixed patrol behavior, collects metrics for the window, and writes a structured result. Sim-agnostic: it only knows ROS2 topics, so the same runner measures Gz/DART, Gz/Bullet, and Isaac/PhysX.
3. **A config + report** (`runs/<sim>.yaml` + a generated `reports/comparison.md`) so each run is fully described by a file and produces a committed, diffable artifact — including the side-by-side table across all sims you've run.

By the end you have a repo of ~300–400 lines that runs `sim-compare --config runs/gz_dart.yaml` per sim and then `sim-compare report` to emit the combined table.

---

## Why a harness and not a stopwatch

You *could* eyeball `gz stats` and jot numbers. Don't — not as the source of truth. A harness gives you:

- **Fairness by construction.** The runner enforces "same behavior, same window, same metrics" across sims — you can't accidentally measure a 45 s window in one and 60 s in another. The fixed parts are in the config, version-controlled.
- **Reproducibility.** A run is a committed YAML, regenerable. "Gz/DART got RTF 0.98" is an artifact with the exact config beside it, not a number from memory.
- **Sim-agnosticism.** Because the runner reads only ROS2 topics, adding Isaac (or a new Gz release) is a new config row, not new measurement code. That is the same "decision in one place" discipline as Week 5's QoS auditor and Week 31's VLA evaluator, applied to simulators.

---

## Package layout

```
crunchbot_sim_compare/
├── package.xml
├── setup.py
├── crunchbot_sim_compare/
│   ├── __init__.py
│   ├── metrics.py          # SimMetrics (from Exercise 2), hardened + sensor-quality stat
│   ├── runner.py           # the harness node: trigger behavior, collect, write result
│   ├── report.py           # combine per-sim results into reports/comparison.md
│   └── cli.py              # `sim-compare` entry point (run | report)
├── runs/
│   ├── gz_dart.yaml        # sim launch, behavior, window, metrics
│   ├── gz_bullet.yaml
│   └── isaac_physx.yaml    # (Path A) or a second Gz engine (Path B)
├── reports/                # generated, committed comparison reports
└── test/
    ├── test_metrics.py     # RTF / step-time / Hz math (the Exercise-2 self-test, formalized)
    └── test_report.py      # the table-assembly + "which differs" logic
```

---

## Deliverable 1 — `metrics.py` (the metric core)

Lift `SimMetrics` from Exercise 2 and add:

- A **sensor-quality statistic**: for `/scan`, the mean and variance of finite ranges over the window (so you can say "Isaac's scan had higher variance — its noise model differs"). For `/imu`, the angular-velocity noise floor while stationary.
- A **contact counter** (optional, sim-dependent): subscribe to the sim's contact topic if it bridges one, and count contacts/second.
- A `to_dict()` so a run's metrics serialize into the result file.

It must stay **ROS-decoupled** (pure functions fed samples) so `test_metrics.py` can test it without a running sim — exactly as the Exercise-2 self-test does.

```python
class SimMetrics:
    def on_clock(self, sim_t: float, wall_t: float) -> None: ...
    def on_sensor(self, wall_t: float, ranges=None) -> None: ...
    def real_time_factor(self) -> float: ...
    def mean_step_time_ms(self) -> float: ...
    def sensor_hz(self) -> float: ...
    def sensor_quality(self) -> dict: ...      # mean/var of ranges, etc.
    def to_dict(self) -> dict: ...
```

---

## Deliverable 2 — `runner.py` (the harness)

The runner must:

1. Read a **run config** YAML naming the sim (for the record), the behavior to trigger, the window length, and the topics to measure.
2. **Trigger the fixed behavior** — publish the patrol goal / start the BT — so every run executes the same motion. (Abstract "trigger the behavior" behind a tiny interface so it's the same call regardless of sim.)
3. Collect metrics for the window via `SimMetrics`.
4. Write a structured result to `runs/results/<sim>.json` (the metrics dict + the config + a timestamp).
5. Refuse to record a run with **too few `/clock` or sensor samples** (the "is the sim even publishing?" guard from Exercise 2) — a bad run must fail loudly, not silently produce zeros.

The fairness guard is the load-bearing bit: the window, the behavior, and the metric set come from config, so two runs are comparable by construction.

---

## Deliverable 3 — the report

`report.py` reads all `runs/results/*.json` and emits `reports/comparison.md`:

```
=== crunchbot_sim_compare ===
behavior: patrol_3wp   window: 60s   robot: crunchbot (week-3)

sim / engine        RTF     step(ms)   /scan Hz   scan var   contacts/s
gz_dart             0.98    1.63       9.8        0.012      12
gz_bullet           1.02    1.41       9.9        0.013      14
isaac_physx         1.21    0.92       10.0       0.021      11
--------------------------------------------------------------------
differs in: RTF, step-time, scan-variance, contacts   ->  see sim-selection note
```

It must flag **which metrics differ** across sims (the "this is a real difference, not noise" signal) and link to your selection write-up. The report is regenerable from the result files — re-running `sim-compare report` reproduces it exactly.

---

## Rules

- **You may** read the Gz Sim, Isaac Sim, and `ros_gz` docs and your own exercise solutions.
- **You must not** let the runner measure different windows or behaviors per sim — the fixed parts come from a shared config schema; if two run configs disagree on window length, the report must warn. The whole project's validity rests on this.
- **You must not** hard-code a simulator into the metric core or the runner — both read only ROS2 topics. Adding a sim is a new config, not new code. (`grep -rn "gz\|isaac" crunchbot_sim_compare/metrics.py crunchbot_sim_compare/runner.py` should be empty of sim-specific logic.)
- Python 3.12, `rclpy` on Jazzy. No third-party metric libraries beyond NumPy.
- The runner must fail loudly on an under-sampled run (too few `/clock`/sensor messages).

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-33-crunchbot-sim-compare-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_sim_compare` succeeds with no warnings.
- [ ] `metrics.py` computes RTF, step-time, sensor Hz, and a sensor-quality stat; ROS-decoupled.
- [ ] `sim-compare --config runs/gz_dart.yaml` and `... runs/gz_bullet.yaml` (Path B) — or a Gz and an Isaac config (Path A) — each produce a result JSON.
- [ ] `sim-compare report` emits `reports/comparison.md` with the side-by-side table and a "differs in" line.
- [ ] The runner **fails loudly** on an under-sampled run (demonstrate by pointing it at a non-existent sensor topic).
- [ ] `colcon test` passes: `test_metrics.py` (RTF/step/Hz, the formalized Exercise-2 self-test) and `test_report.py` (table assembly + differs-detection).
- [ ] A `README.md` with the run commands, the config schema, and a paragraph on why the harness is sim-agnostic.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Metric correctness** | 25 | RTF/step-time/Hz/quality computed right; matches `gz stats` within tolerance; ROS-decoupled core. |
| **Fairness by construction** | 25 | Window + behavior + metric set from shared config; report warns on mismatched configs; same tool every sim. |
| **Sim-agnosticism** | 20 | No sim-specific logic in the core/runner; adding a sim is a config; the grep check is clean. |
| **Reproducibility & report** | 15 | Results are committed JSON; report regenerable; "differs in" line correct. |
| **Tests** | 10 | Metric math and report logic tested; green. |
| **Docs & hygiene** | 5 | Clear README; no build artifacts committed; sensible commits. |

**90+** is portfolio-grade and ready to extend into Week 34's randomization harness. **70–89** works but has a fairness hole or sim-specific leakage. **Below 70** means the comparison isn't fair-by-construction — fix the config-driven fixed-parts first.

---

## How this connects to the rest of C24

- **Week 34 (next week)** extends this exact harness into a *domain-randomization* harness: same metric-capture core, but now you vary the *world parameters* per episode and measure the *gap* between a nominal policy and a randomized one. The `metrics.py` and `runner.py` you build here are the foundation; you add a randomization layer on top. Build the metric core cleanly now and next week is a layer, not a rewrite.
- **Week 40 (Phase 5 milestone)** stands up the full capstone system in sim. This harness is how you'd produce a credible "the capstone runs at RTF X with sensor rates Y" sanity check before the milestone — evidence, not a vibe.
- **The capstone** benefits from the sim-agnostic discipline: a capstone you can run in either Gz Sim or Isaac Sim (because the ROS2 stack doesn't care) is more robust and more impressive than one welded to a single simulator. This harness *is* that sim-agnosticism, made measurable.

## Common pitfalls (read before you start)

These are the mistakes that cost people the most time on this project:

- **Forgetting `use_sim_time`.** If your nodes timestamp against wall-clock instead of `/clock`, your metrics and your behavior tree desync, and the numbers are garbage. Set it everywhere.
- **A QoS mismatch on the bridged sensor.** The Week 5 silent failure: a `RELIABLE` subscriber against a `BEST_EFFORT` bridge reads nothing, and your `/scan` Hz reads 0. The runner's under-sample guard should catch this, but the fix is the QoS, not the guard.
- **Different windows or behaviors across sims.** The whole project's validity rests on "only the simulator differs." If one run measured 45 s and another 60 s, the report must warn — and you must fix it before trusting the comparison.
- **Sim-specific logic leaking into the core.** If `metrics.py` or `runner.py` imports a simulator, you've broken portability. Keep all sim-awareness in the config and the launch, never in the measurement code.
- **Trusting a single run.** Run-to-run noise is real. The "confidence over repeats" stretch goal isn't optional polish — a difference within run-to-run noise is not a difference.

## Stretch goals

- **Boot-time metric.** Add "launch → first `/scan`" to the report. Iteration speed is a real cost the physics metrics hide and a big reason Gz stays the debugging default.
- **Confidence over repeats.** Run each sim 3× and report mean ± std per metric, so "RTF 0.98" comes with a spread — a reviewer's first question is "is that difference real or run-to-run noise?".
- **Isaac Lab throughput cell.** (Path A) Add a separate measurement of *parallel-environment* steps/second in Isaac Lab (64, 256, 1024 envs) — the one number Gz Sim structurally cannot produce, and the bridge to Week 34/Week 28.
- **CI smoke test.** A GitHub Action that launches a headless Gz Sim, runs one short patrol, and asserts the runner produces a valid result JSON — so the harness itself can't silently rot.

## What "done" looks like

When this project is finished, you can hand a teammate a single command and a config file and they can reproduce your entire comparison:

```bash
sim-compare --config runs/gz_dart.yaml      # measure sim A
sim-compare --config runs/gz_bullet.yaml    # measure sim B (Path B) or isaac (Path A)
sim-compare report                          # emit reports/comparison.md
```

and the resulting `reports/comparison.md` answers "which sim, and how do you know?" with a measured table, not an opinion. That reproducibility — anyone, any time, same numbers — is the difference between a one-off experiment and an engineering tool, and it's what makes this a portfolio piece rather than a homework artifact. A recruiter or a senior reviewer who sees "here's my sim-comparison harness, here's the regenerable report" reads it as exactly the kind of rigor a robotics team wants.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
