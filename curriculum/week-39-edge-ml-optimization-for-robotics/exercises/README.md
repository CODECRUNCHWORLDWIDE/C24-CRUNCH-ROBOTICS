# Week 39 — Exercises

Three drills that turn the measure-first discipline into a reflex. Do them in order — exercise 1 builds the profile that exercises 2 and 3 act on. Run everything on your **Jetson Orin** (Path A) or your documented x86+GPU stand-in with capped power/clocks (Path B). Both paths clear the week; Path B learners note their stand-in conditions in every report.

## Index

1. **[Exercise 1 — Profile the integrated graph](exercise-01-profile-the-graph.md)** — stand up the Week 13 detector + Week 29 policy + a depth stage, profile with `tegrastats`/`nsys`/`trtexec`/Foxglove, and produce a Gantt-style latency block diagram with a per-stage p95. (~60 min, guided)
2. **[Exercise 2 — INT8 calibrate and measure the cost](exercise-02-int8-calibrate.py)** — calibrate the detector to INT8 with a representative set, measure the mAP delta on a held-out set, and decide accept/reject against a floor. Runnable; falls back to a synthetic model + dataset if you lack the Week 13 checkpoint. (~50 min)
3. **[Exercise 3 — The latency-budget gate](exercise-03-latency-budget.py)** — a runnable budget checker that loads a budget table, ingests measured per-stage p95s, and *fails* (non-zero exit) when the sum regresses past the cycle target. This is your CI gate. (~40 min)

## How to work the exercises

- **Profile before you optimize, every time.** Exercise 1 is first for a reason: you cannot do 2 or 3 honestly without a real profile. If your sim/hardware is down, each runnable exercise has a synthetic fallback so you are never blocked — but say so in your report.
- **Pin the power mode.** `sudo nvpmodel -m 0 && sudo jetson_clocks` before any measurement, and record the mode in your report. Numbers in different power states are not comparable (Lecture 1 §5).
- **Warm up, then measure 500+ cycles.** A p95 over 20 samples is noise. The tail is where deadlines die.
- **Measure both columns.** Every optimization gets a latency win *and* a named accuracy cost. A speedup with no accuracy number is half an answer (Lecture 1 §7).
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match the shape of it, you're not done.

## Running the Python exercises

The two `.py` files run in your standard C24 environment. Exercise 2 uses TensorRT + ONNX if present and falls back to a pure-NumPy quantization simulator (so the *measurement discipline* is exercised even without a Jetson). Exercise 3 is pure Python — no GPU needed.

```bash
python3 -c "import numpy; print('numpy', numpy.__version__)"
# Optional, for the real INT8 path in exercise 2:
python3 -c "import tensorrt; print('TensorRT', tensorrt.__version__)" 2>/dev/null || echo "TRT absent — exercise 2 uses its NumPy fallback"

python3 exercise-02-int8-calibrate.py
python3 exercise-03-latency-budget.py
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-39` to compare.
