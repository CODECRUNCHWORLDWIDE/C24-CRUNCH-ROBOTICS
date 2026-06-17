# Challenge 1 — Drive Per-Instruction Success to ≥ 15 of 20

**Time estimate:** 4–6 hours, spread across Thursday, Friday, and Saturday.

## Problem statement

Take the frozen twenty-instruction suite (exercise 1), the baseline report (exercise 2), and the fine-tuned policy (exercise 3), and drive **per-instruction success to at least 15 of 20 instructions passing** (an instruction "passes" at ≥ 3/5 trials). Then, for **every instruction still failing**, document:

1. **The failure mode** — exactly one of `grounding`, `grasp`, `placement`, `language-binding` (lecture 2 §10), supported by evidence (a Foxglove replay screenshot, the perception output, the action trace).
2. **The next concrete fix** — a specific, small data or scaffolding change that would plausibly close it. "Ten demos of far-shelf instructions." "Recalibrate the gripper TCP." "Add a search-then-ask scaffold for recovery cases." Not "more work" — a named change.

This is the capstone acceptance bar. The week-48 panel grades your policy against exactly this. The challenge is to clear it now, with margin, and to know precisely where you stand on the instructions you do not clear.

## What "driving the number up" looks like

You will not hit 15/20 from a single fine-tune in most cases. The loop is:

1. Run the diff (exercise 3). Read which instructions fail and cluster them by axis.
2. The cluster names your next data. If all four failures are dense-distractor color-grounding, collect ten more demos that disambiguate color in cluttered scenes. If all failures are recovery cases, add a search-then-ask behavior-tree scaffold (this is *scaffolding*, not just data).
3. Re-fine-tune (or add the scaffold), re-select the checkpoint on the dev slice, re-run the frozen suite, re-diff.
4. Stop when you clear 15/20 **or** when you have a documented, honest diagnosis for every remaining failure and have run out of week.

Two hard rules while you do this:

- **You may not edit the frozen suite.** Not the instructions, not the resets, not the rubric. If you touch it, every prior number is void and you restart the baseline. The suite is the fixed target; only the policy moves.
- **The demos you add must stay distinct from the suite.** Same families, different specific phrasings and layouts. Training on the test set is cheating and the panel will check for it.

## Acceptance criteria

- [ ] A final `reports/diff.md` produced by exercise 3's `diff` subcommand, showing **≥ 15/20 instructions passing** on the fine-tuned policy against the frozen suite (commit hash matching the baseline).
- [ ] Every cell is `k/N` with N = 5. No single-run numbers anywhere.
- [ ] The suite total is reported with a **Wilson 95% CI** and an explicit OVER/UNDER acceptance call.
- [ ] Every instruction that does **not** pass has a `FAILURE-DIAGNOSIS.md` entry with: the failure mode (one of the four), evidence (a replay screenshot or trace), and a specific next fix.
- [ ] Every **regression** (any instruction the fine-tune made worse) is called out and explained — fine-tuning that helped overall but broke instruction 7 is a real result you report, not hide.
- [ ] The whole loop is reproducible: the frozen suite, the demo dataset (or a manifest of it), the LoRA adapter, and the reports are committed, and a `README` documents how to re-run the diff.
- [ ] Committed under `challenges/challenge-01/` in your capstone repo.

## Stretch

- **Hit 18/20.** The acceptance bar is 15; a defense-grade result is 18+. The marginal instructions past 15 are usually the recovery and dense-distractor cases — the genuinely hard ones — so closing them demonstrates real depth.
- **Add a scaffold instead of data for the recovery cases.** Rather than collecting recovery demos, wire a behavior-tree fallback: if the perception stack does not find the named object within a confidence threshold after a search sweep, the robot asks the operator (via the week-43 dashboard) or aborts cleanly. Show the recovery instructions pass via the scaffold, and discuss the trade-off (a scaffold is more interpretable and safer than a learned recovery, but less general).
- **Quantify the demo-efficiency curve.** Fine-tune on 10, 25, and 50 demos and plot instructions-passed vs demo count. The shape of that curve is a genuinely interesting result and a great defense slide — it tells you whether you are data-starved (steep curve, collect more) or saturated (flat, the limit is elsewhere).
- **Ablate LoRA rank.** Re-fine-tune at r=8, r=16, r=32 and report whether rank mattered for your 50-demo regime. Most capstones find it does not much — which is itself worth saying.

## Hints

<details>
<summary>How to tag a failure mode from a replay</summary>

Replay the failed trial in Foxglove (you wired this in week 43). Watch the wrist camera and the action trace together:

- The arm goes confidently to the **wrong object** → `grounding`.
- The arm reaches the **right object** and the gripper closes on nothing / slips → `grasp`.
- The arm picks the **right object** and releases it in the **wrong place** (or 8 cm off) → `placement`.
- The arm does the **same thing regardless** of what you said → `language-binding`. Cross-check by issuing two different instructions and confirming the action is identical.

When in doubt between grounding and language-binding: grounding picks a *plausible wrong object the instruction could refer to*; language-binding ignores the instruction *entirely* and does a default behavior.
</details>

<details>
<summary>Translating a failure cluster into a next fix</summary>

| Cluster | Likely fix |
|---------|-----------|
| Color grounding in clutter | 10 demos disambiguating that color among distractors |
| Spatial "left/right/far" | Demos varying object position with the spatial word in the instruction |
| Specific object's grasp | Re-check gripper TCP calibration FIRST, then grasp-specific demos |
| Placement at a destination | Demos ending at that destination; check the scorer's destination frame |
| Phrasing brittleness | Paraphrase demos for the affected family |
| Recovery | A BT search-then-ask scaffold (often better than learned recovery) |

A good fix names the count and the family: "10 demos of {red/blue/green}-cup-in-clutter", not "more grounding data".
</details>

<details>
<summary>Why your number might go DOWN after adding demos</summary>

Three usual causes: (1) the new demos were sloppy and taught a bad habit — filter to successes only; (2) you trained too long and the adapter memorized — select an earlier checkpoint on the dev slice; (3) the new demos shifted the action-normalization statistics — recompute them over the *combined* dataset, not the new demos alone. If a demo addition regresses the suite, revert it and investigate; do not stack more data on top of a regression.
</details>

## Submission

Commit under `challenges/challenge-01/` in your capstone repo: the final `diff.md`, `FAILURE-DIAGNOSIS.md`, the LoRA adapter (or a download manifest if it is large), the demo dataset manifest, and a `README` that lets a fresh clone re-run the diff. Make sure the diff's suite commit hash matches the frozen suite's — the panel checks it.

## Why this matters

This is the capstone, distilled. Everything else — the safety case, the telemetry, the chaos drills — protects and surrounds a robot that can *do the task you ask it to*. The 15/20 bar is the measurable definition of "can do the task." Clearing it is the difference between a capstone that demos well and a capstone that *works*. And the failure diagnosis is the difference between an engineer who got lucky and one who understands their system — which is the exact distinction every robotics interview in week 45, and the panel in week 48, is built to find.
