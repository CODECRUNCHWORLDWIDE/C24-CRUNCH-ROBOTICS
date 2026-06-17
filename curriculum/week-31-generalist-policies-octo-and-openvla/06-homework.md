# Week 31 Homework

Six problems that force the VLA literacy into your fingers. The full set should take about **5 hours**. Work in your Week 31 Git repository (the same workspace as the exercises and the `crunchbot_vla_eval` mini-project) so every problem produces at least one commit you can point to at the Phase 4 second midterm in Week 32.

The headline deliverable is **Problem 4 — the VLA failure analysis**, the syllabus artifact ("document the failure modes"). Treat it as the writeup a reviewer reads, not a journal entry.

Have a cloud GPU available for Problems 2 and 4 (the fine-tune and eval). Problems 1, 3, and 5 need no GPU. If your fine-tune from the challenge is already done, Problems 2 and 4 reuse that checkpoint — don't pay for two fine-tunes.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — The architecture comparison memo

**Problem statement.** Write a one-page memo at `notes/week-31/octo-vs-openvla-memo.md` aimed at a teammate who hasn't read the papers. Cover: (a) the two action representations (discrete tokens vs. diffusion chunk) and the consequence of each; (b) OpenVLA's three backbone pieces and what DINOv2 vs SigLIP each contribute; (c) the latency/capability trade-off and a one-line decision rule for "which one (or neither) for a given task."

**Acceptance criteria.**

- `notes/week-31/octo-vs-openvla-memo.md` exists, ~1 page, hitting (a), (b), (c).
- The decision rule names a *concrete* discriminator (latency budget, language complexity, demo count), not "it depends."
- At least one number appears (parameter counts, bin width, or a latency figure you measured in Exercise 1).
- Committed.

**Hint.** Pull the bin-width arithmetic and the latency observation straight from Exercise 1. A good memo ends with a table; reuse the Lecture 1 §3.4 side-by-side and add your own "when neither — use last week's ACT" row.

**Estimated time.** 40 minutes.

---

## Problem 2 — Fine-tune and register your stats correctly

**Problem statement.** Fine-tune `openvla-7b` with LoRA on your Week 29 LeRobot dataset for one epoch (or reuse the challenge checkpoint). The graded part is **the un-normalization discipline**: register your dataset's normalization stats under a named `unnorm_key`, fine-tune with it, and **prove** at inference that a known action round-trips to correct real units using the *deployed* stats.

**Acceptance criteria.**

- A LoRA adapter exists, trained on your LeRobot dataset.
- `notes/week-31/finetune-log.md` records the `unnorm_key` you registered, the key flags, and the final action-token accuracy.
- You demonstrate the round-trip: take one ground-truth action from your data, tokenize/de-tokenize it through the *deployed* `unnorm_key` (your Exercise-2 tokenizer or `predict_action` on a known target), and show it recovers the right real units (within one bin width).
- Committed.

**Hint.** The round-trip proof is your insurance against the Lecture 2 §2.4 trap. If the de-tokenized magnitude is off by a constant factor across all translation dims, you used the wrong stats — that constant factor *is* the ratio of the two datasets' ranges (you saw exactly this in Exercise 2 Part B).

**Estimated time.** 1 hour (excludes GPU wall-time if reusing the challenge run).

---

## Problem 3 — Tokenization edge cases

**Problem statement.** Extend your Exercise-2 tokenizer with three edge-case tests and document the behavior in `notes/week-31/tokenization-edges.md`: (1) an action **outside** `[q01, q99]` — confirm it clamps to the end bin, not wraps; (2) a dimension that **never moves** in the data (`q01 == q99`, e.g., a gripper stuck at 1.0) — confirm it doesn't divide by zero and pick a sane behavior; (3) the **worst-case quantization error** for your task's translation range — compute it in mm and decide whether 256 bins is fine for your task.

**Acceptance criteria.**

- `notes/week-31/tokenization-edges.md` documents all three cases with the observed behavior and your reasoning.
- The clamp case shows an out-of-range value maps to bin 0 or 255 (not an exception, not a wrap).
- The degenerate-dimension case shows your tokenizer handles `q01 == q99` gracefully (the Exercise-2 code already guards this — explain *how*).
- You state, in one sentence, whether 256-bin resolution is adequate for your task and why.
- Committed.

**Hint.** Exercise 2's `ActionTokenizer` already clamps (the `np.clip` in `normalize`) and guards the zero-span case (`span[span == 0.0] = 1e-8`). Your job is to *test and explain* those, then compute `(q99 - q01)/256` in mm for your real translation range.

**Estimated time.** 45 minutes.

---

## Problem 4 — The VLA failure analysis (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Using your fine-tuned checkpoint and the zero-shot baseline, run a held-out eval (reuse the challenge's protocol or the `crunchbot_vla_eval` mini-project) and write a failure analysis at `notes/week-31/vla-failure-analysis.md` against this template:

1. **Summary** — one sentence: the zero-shot and fine-tuned success rates and the gap closed.
2. **Protocol** — the eval set: conditions, `n` per condition, the success predicate, and how you guaranteed the start states were held out from training.
3. **Results table** — the honest-number A/B (zero-shot vs fine-tuned, per condition).
4. **Failure taxonomy** — every failure classified perception / grounding / control, with counts that sum to the failures, per checkpoint.
5. **Root cause of the dominant class** — including an explicit check that any "control" failures aren't actually un-normalization or EE-delta→IK bugs.
6. **Next fix** — the one concrete change you'd make, tied to the dominant failure class.

**Acceptance criteria.**

- `notes/week-31/vla-failure-analysis.md` exists, hits all six headings, and is the kind of thing you'd defend to a panel.
- The results table has explicit `n` and a defined success predicate; the failure counts sum.
- The root-cause section explicitly addresses whether un-normalization / IK mapping was ruled out for the control failures.
- The next-fix is concrete and tied to the dominant class, not "train more."
- Committed.

**Hint.** If the mini-project is done, this writeup is mostly assembling its generated report into prose. The grading weight is on parts 4–5: a reviewer wants to see you *diagnosed* failures, not just counted them. "11 of 14 failures were grounding (picked the distractor); my fine-tune data had only one phrasing of the instruction, so I'd add paraphrases" is an A; "it failed a lot, needs work" is not.

**Estimated time.** 1 hour 15 minutes (excludes eval wall-time if reusing the challenge run).

---

## Problem 5 — When *not* to use a VLA

**Problem statement.** Make the senior judgment call explicit. In `notes/week-31/vla-or-not.md`, take three hypothetical tasks and argue, for each, whether you'd reach for a fine-tuned OpenVLA, Octo, or a Week-30 specialist (ACT/Diffusion Policy): (a) one fixed pick task, 300 demos, 40 ms latency budget on an Orin; (b) a kitchen robot that must follow 50 distinct spoken instructions over varied objects; (c) a high-speed insertion task needing sub-millimeter precision at 100 Hz.

**Acceptance criteria.**

- `notes/week-31/vla-or-not.md` gives a recommendation for all three with a one-paragraph justification each.
- Each justification names the *deciding factor* (latency, language breadth, precision/quantization, demo count) — not generic praise.
- At least one task recommends *against* the VLA, with the reason.
- Committed.

**Hint.** Task (c) is the trap: 256-bin tokenization at 100 Hz with sub-mm precision is a bad fit for OpenVLA on two counts (binning resolution and latency). Task (b) is where the 7B language prior earns its keep. Task (a) is the "specialist wins" case from Lecture 2 §3.4.

**Estimated time.** 40 minutes.

---

## Problem 6 — Inference latency reality check

**Problem statement.** Measure, don't guess. Time OpenVLA's `predict_action` over 20 forward passes on your GPU and report the mean and p95 latency. Then state what that implies for real-time control (e.g., a 10 Hz control loop needs ≤ 100 ms per action) and which Week-39 optimization you'd reach for first.

**Acceptance criteria.**

- `notes/week-31/latency.md` reports mean and p95 latency over ≥ 20 runs on named hardware.
- You compute the implied max control rate (`1 / mean_latency`) and compare it to a 10 Hz target.
- You name one concrete optimization (4-bit quantization, OpenVLA-OFT parallel decoding, distillation, or moving to Octo) and one sentence on the trade-off.
- Committed.

**Hint.** Warm up with a couple of throwaway passes before timing (first-call compilation/caching skews the mean). The p95 matters more than the mean for a control loop — a single 400 ms stall drops a cycle. This problem is your on-ramp to Week 39's edge-ML optimization and Week 37's "latency reality on edge compute."

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Architecture comparison memo | 40 min |
| 2 — Fine-tune + register stats | 1 h 0 min |
| 3 — Tokenization edge cases | 45 min |
| 4 — VLA failure analysis (headline) | 1 h 15 min |
| 5 — When not to use a VLA | 40 min |
| 6 — Inference latency reality check | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_vla_eval` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 32's midterm and Week 44's capstone eval both build on it. Then take the [quiz](./05-quiz.md) with your notes closed.
