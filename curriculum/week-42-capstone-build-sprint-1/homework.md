# Week 42 Homework

Five deliverables that turn the week's hands-on work into committed, defensible capstone evidence. The full set should take about **5 hours**. Work in your capstone repo so each deliverable produces commits the Week 48 panel can read.

Each problem includes a **statement**, **deliverables**, **acceptance criteria**, a **hint**, and an **estimated time**. The final rubric ties them together.

---

## Problem 1 — The integration-day log

**Statement.** Write `capstone/sprint-01/INTEGRATION_LOG.md`: a timestamped, honest narrative of your integration day. Not a polished retrospective — a log. Every senior engineer keeps one on bring-up day, because the bug you fixed at 14:20 is the bug you will hit again next month and will have forgotten how you fixed.

**Deliverables.**

- A chronological log with real timestamps, one entry per event: what you tried, what happened, what you changed.
- At least one entry documenting a *failure* and its fix. (If you had no failures, you did not actually integrate anything.)
- A closing "what I would do differently next bring-up" paragraph.

**Acceptance criteria.**

- File exists, ≥ 300 words, with at least six timestamped entries.
- At least one entry is a debugged failure with the root cause named.
- Committed.

**Hint.** Keep a terminal scratch file open *during* integration day and paste into it as you go. Reconstructing the log from memory afterward loses exactly the details that make it useful.

**Estimated time.** 45 minutes (most of it captured live during the sprint).

---

## Problem 2 — The Allan-deviation characterization

**Statement.** Compute the Allan deviation of your IMU's gyro (at least the z-axis) from a static `rosbag2`, extract the angle-random-walk and bias-instability numbers, and compare them to the datasheet.

**Deliverables.**

- `characterization/allan_gyro.png` with N and B annotated.
- A short table comparing your measured N and B to the datasheet's noise-density and in-run-bias-stability numbers (converted to the same units).
- One sentence: is your IMU healthy (within ~2× of datasheet), or do you have a mounting/EMI problem?

**Acceptance criteria.**

- The plot is from *your* IMU, not a stock image.
- N and B are stated with units.
- The datasheet comparison is present and the health verdict is justified.

**Hint.** Use the `allan.py` and `extract_gyro.py` from Lecture 1 §2, or `allan_variance_ros`. Let the IMU warm up ten minutes before recording, and record at least 30 minutes perfectly still.

**Estimated time.** 1 hour (plus the passive recording time).

---

## Problem 3 — The headline-number report

**Statement.** Write `capstone/sprint-01/RESULT.md`: the one-page report of your headline metric, in a form a panel can grade in 60 seconds.

**Deliverables.**

- The `[capstone]` PASS/FAIL line for your path's metric (drift for A, cold boot for B).
- Path A: `results/drift.png`. Path B: `results/cold_boot.txt` (the `systemd-analyze`/`journalctl` evidence).
- A two-paragraph gap analysis: the single most impactful sim-to-reality (A) or ad-hoc-to-production (B) difference, *quantified*.
- A link to the rosbag / journal that backs the number.

**Acceptance criteria.**

- The number traces to a committed artifact (no unbacked numbers).
- The gap analysis names a specific cause and quantifies its cost.
- PASS/FAIL is stated against the correct bar (0.5 m, or 60 s).

**Hint.** "It drifted more than in sim" is not a gap analysis. "The 38 ms IMU timestamp lag contributed ~0.5 m until I fixed the driver stamp; after that, residual drift was 0.41 m" is.

**Estimated time.** 1 hour.

---

## Problem 4 — The EKF tuning table

**Statement.** Document the re-tuning of your estimator as a reproducible table, driven by replaying one recorded bag (Lecture 1 §5).

**Deliverables.**

- `config/ekf.yaml` (commented).
- A table in `RESULT.md` (or a linked file) with columns: *parameter changed*, *old value*, *new value*, *terminal drift on the replayed bag*, *covariance bounded? (y/n)*.
- At least four rows (i.e. you tried at least four configurations on the same bag).

**Acceptance criteria.**

- All rows use the *same* replayed bag (the table is an apples-to-apples comparison).
- The chosen final config is the one with bounded covariance and lowest drift, and is the one in `ekf.yaml`.
- The table makes clear which knob mattered most.

**Hint.** Change one parameter per row. If you change three things and drift drops, you have learned nothing about which one helped.

**Estimated time.** 1 hour.

---

## Problem 5 — The "what's still broken" punch list

**Statement.** Every integration sprint ends with known defects. Write `capstone/sprint-01/PUNCHLIST.md`: the honest list of what is still wrong, prioritized, with an estimate of the effort to fix each.

**Deliverables.**

- A prioritized list of at least four open issues (there are always four).
- For each: a one-line description, the suspected cause, the rough effort to fix, and which later week (43–47) is the right place to fix it.
- One item flagged as "must fix before Week 48 defense."

**Acceptance criteria.**

- At least four items, prioritized.
- Each has a suspected cause and an effort estimate.
- The "must fix before Week 48" item is identified.

**Hint.** This is the most valuable file you write all week for *future-you*. The punch list you write now is the backlog you burn down across the remaining sprints. Be specific: "covariance trace creeps up after ~80 s, suspect odometry covariance too tight, ~2 h, fix in Week 43" beats "localization could be better."

**Estimated time.** 30 minutes.

---

## Rubric (100 points)

| Deliverable | Points | Full marks |
|-------------|-------:|------------|
| **Integration log** | 15 | Live, timestamped, ≥ 6 entries, ≥ 1 debugged failure with root cause. |
| **Allan characterization** | 20 | Your own plot, N and B with units, datasheet comparison, health verdict justified. |
| **Headline-number report** | 30 | `[capstone]` line backed by a committed artifact; quantified gap analysis; correct bar. |
| **EKF tuning table** | 20 | ≥ 4 rows on the *same* replayed bag, one change per row, final config matches the table's best. |
| **Punch list** | 15 | ≥ 4 prioritized items with cause + effort + target week; one "must fix before Week 48" flagged. |

**Passing is 70.** The single fastest way to lose points is an unbacked number — a drift figure with no rosbag, a cold-boot time with no journal. Every number this week must trace to an artifact.

---

## A short reflection (not graded, but do it)

In `capstone/sprint-01/REFLECTION.md`, ~250 words:

1. What surprised you most about the gap between sim and reality (A) or hand-run and production (B)?
2. Which of the four common drift causes (timestamp lag, `use_sim_time`, untuned Q, actuator lag) bit you, and how did you find it?
3. If you had one more day this week, what would you spend it on?
4. How confident are you, on a scale of 1–10, that you will clear the 0.5 m bar in the Week 48 defense — and what is the biggest risk to that?

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 | 45 min |
| 2 | 1 h 0 min |
| 3 | 1 h 0 min |
| 4 | 1 h 0 min |
| 5 | 30 min |
| **Total** | **~4 h 15 min** |

When you have finished all five, push your `capstone/sprint-01/` directory and open the [mini-project](./mini-project/README.md) to assemble them into the graded sprint artifact.
