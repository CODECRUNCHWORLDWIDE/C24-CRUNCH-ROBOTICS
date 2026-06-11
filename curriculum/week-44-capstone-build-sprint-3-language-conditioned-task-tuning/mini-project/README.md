# Mini-Project — The Tuned Capstone VLA Policy + Twenty-Instruction Eval Report

> Deliver the tuned capstone VLA policy together with its frozen twenty-instruction evaluation suite and a baseline-vs-fine-tuned per-instruction report. This is the artifact that drives your capstone toward the **15-of-20 acceptance criterion graded at week 48.** Everything you build this week converges here.

This mini-project is not a toy in a sandbox. It operates directly on your capstone robot (Path A) or your hardened sim (Path B). It compounds on the policy you built in the VLA weeks (31–34), the telemetry and replay you wired in week 43, and the safety filter you have carried since the safety-case week (41). By the end you have a single, defensible package: a policy that is measurably better than where it started, a frozen suite that proves the measurement is honest, and a report that says exactly where you stand against the bar.

**Estimated time:** ~8.5 hours (split across Thursday, Friday, and Saturday in the suggested schedule).

---

## What you will deliver

A repository (a subtree of your capstone repo, or a clearly-linked sibling) named `capstone-policy-tuning/` containing five things:

1. **The frozen eval suite** — `suite/eval_suite.yaml` plus its resets and rubric, committed and version-pinned (from exercise 1).
2. **The eval-runner** — the `rclpy` harness that scores the policy against the suite (from exercise 2), packaged so a fresh clone can run it.
3. **The tuned policy** — the LoRA adapter (from exercise 3), with documentation on how to merge it into the deployment action server.
4. **The baseline-vs-fine-tuned report** — `reports/diff.md`, the per-instruction table with `k/N` cells, regressions flagged, a Wilson CI on the total, and an OVER/UNDER acceptance call.
5. **The failure-diagnosis dossier** — `FAILURE-DIAGNOSIS.md`, one entry per still-failing instruction: failure mode, evidence, next fix.

This package is what you hand the week-48 panel as evidence that your robot can do the task it is named after. Build it as if the panel is reading it tomorrow, because in four weeks they are.

---

## Why this is the capstone's spine

The capstone is *Autonomous Mobile Manipulator with Language-Conditioned Pick-and-Place*. Strip away the safety case, the telemetry, the chaos drills — all essential, all surrounding — and what remains is a single claim: **the robot takes a natural-language instruction and carries it out.** This mini-project is the measurement of that claim. The 15/20 bar is the operational definition of "carries it out reliably enough to ship." Without this package you have a robot that demos; with it you have a robot you can defend.

This is also the artifact that does the most work in the interview ramp (week 45) and the defense (week 48). "Here is how I measured my policy, here is the failure I fixed and how, here is the failure I did not fix and what I'd do next" is the single most senior thing you can say about a learned system. This week earns you the right to say it.

---

## Rules

- **You may** reuse everything you have built: the policy from the VLA weeks, the action server, the perception stack, the safety filter, the week-43 telemetry and replay, your teleop.
- **You may** fine-tune only with **LoRA** on **at most 50 capstone-specific demonstrations**. No full-parameter fine-tunes. No more than 50 demos in the headline result (you may collect more for the stretch demo-efficiency curve, but the acceptance result is the 50-demo policy).
- **You may NOT** edit the frozen suite after the first run against it. If you must change it, bump `suite_version`, re-run the baseline, and say so loudly. Suite drift voids your numbers.
- **You may NOT** include any suite instruction text or scene in your training demos. Demos are adjacent-but-distinct. Training on the test set is disqualifying.
- **You must** report `k/N` (N = 5) everywhere. No single-run numbers. No best-of-three.
- **You must** evaluate baseline and fine-tuned against the *same* frozen suite commit. The diff harness refuses to run otherwise — keep it that way.
- Target stack: ROS2 Jazzy on Ubuntu 24.04, `rclpy` for the runner, PyTorch 2.x + PEFT for the fine-tune, your existing `BehaviorTree.CPP` task tree, your perception (OpenCV/Open3D) and state estimate (GTSAM) for the scorer's inputs.

---

## Acceptance criteria

- [ ] A repo/subtree `capstone-policy-tuning/` with the five deliverables above.
- [ ] `suite/eval_suite.yaml` has exactly twenty instructions, stratified across the five failure axes, frozen and committed, with its commit hash recorded.
- [ ] The eval-runner runs the full suite (20 × 5 = 100 trials) end to end without crashing and writes `report.md`, `report.csv`, `report.json`.
- [ ] A baseline report exists for the un-tuned policy, with a commit hash matching the frozen suite.
- [ ] A LoRA fine-tune completed on ≤ 50 demos; the chosen checkpoint was selected on a dev slice (evidence: the dev-eval curve or a short note), **not** on lowest loss.
- [ ] A fine-tuned report exists, same suite commit, and `reports/diff.md` shows the baseline-vs-fine-tuned per-instruction table.
- [ ] The report quotes the suite total as instructions-passed **and** a Wilson 95% CI, with an explicit OVER/UNDER acceptance call against 15/20.
- [ ] Every regression is flagged and explained; every still-failing instruction has a `FAILURE-DIAGNOSIS.md` entry (mode + evidence + next fix).
- [ ] A `README` in the package lets a fresh clone reproduce the diff (it may point at a hosted adapter/dataset for the large binaries).
- [ ] The fine-tuned policy actually deploys: the adapter merges into the action server and the robot executes at least the top three suite instructions live (recorded for the defense video).

You do **not** have to clear 15/20 to *pass the mini-project* — but you do have to clear it (or have a fully-documented honest gap) to pass the *capstone* at week 48. If you are under the bar this week, the mini-project still passes provided the measurement is honest and the diagnosis is complete; you then have weeks 45–47 to close the gap. The one unforgivable outcome is a number you cannot defend.

---

## Suggested build order

### Thursday — fine-tune and re-run (≈ 2 h hands-on + GPU time)

1. Confirm your frozen suite (exercise 1) is committed and your baseline report (exercise 2) exists. If not, do those first — they are prerequisites, not parts of Thursday.
2. Collect or finalize your 50 demos in LeRobot v2 format, observation/action space matching deployment exactly. Filter to successes only.
3. Kick off the LoRA fine-tune (exercise 3 `train`). Start it early — it is the long pole. While it runs, write the dev slice (a handful of held-out instructions distinct from the frozen suite) and wire the dev-eval loop.
4. When checkpoints land, evaluate each on the dev slice and select the best. Merge it into the action server.

### Friday — diff, diagnose, package (≈ 2.5 h)

5. Re-run the eval-runner on the merged fine-tuned policy against the frozen suite → `reports/finetuned/report.json`.
6. Run the diff (`exercise-03 diff`) → `reports/diff.md`. Read it.
7. Cluster the failures by axis. Write the first pass of `FAILURE-DIAGNOSIS.md` — mode + evidence + next fix per failure. Replay failures in Foxglove for the evidence screenshots.
8. If you are under 15/20 and have time, run one improvement loop (challenge 1): add the data or scaffold the cluster demands, re-fine-tune, re-diff.

### Saturday — drive the number and finalize (≈ 3 h)

9. Continue the improvement loop until you clear 15/20 or run out of week with a complete diagnosis.
10. Record the deploy proof: merge the final adapter, run the top three instructions live, capture the clip for the defense video.
11. Finalize the package: commit the suite, runner, adapter (or manifest), reports, diagnosis, and the reproduce-the-diff README.

### Sunday — write the report (≈ 1 h)

12. Write the one-page summary that fronts the package: the headline number with its CI, the OVER/UNDER call, the three biggest wins, the regressions and why, and the next-fix list for the remaining failures. This page is what the panel reads first.

---

## The report — what "good" looks like

The headline `reports/diff.md` plus its one-page summary is the deliverable a senior reviewer judges in two minutes. A strong one reads like this:

```
Capstone policy tuning — summary
Suite: capstone-acceptance v1.0.0 (commit 4f2a9c1, 20 instructions, 5 trials each)
Baseline: openvla-7b, no fine-tune.   Fine-tuned: openvla-7b + capstone-lora (step-2000, 50 demos).

Headline: 9/20 -> 16/20 instructions passing. OVER the 15/20 bar.
Trial-success: 41/100 -> 80/100. 95% Wilson CI on fine-tuned rate [0.71, 0.87].

Biggest wins:
  - Color grounding in clutter (id 11,12,13): +2/+3/+2. The disambiguation demos worked.
  - Placement at the shelves (id 2,15): the destination demos closed both.

Regression:
  - id 7 "grab the cup next to the toolbox": 2/5 -> 1/5. The fine-tune over-fit toward
    bench grasps and weakened the relational-reference case. Next fix: 8 relational demos.

Still failing (diagnosis in FAILURE-DIAGNOSIS.md):
  - id 18 (recovery, cup-on-wrong-side): grounding -> grasps the distractor. Fix: search-then-ask BT scaffold.
  - id 19 (recovery, object-absent): language-binding -> proceeds anyway. Fix: confidence-gated abort.
  - id 14 (cup-behind-box): grasp -> reaches it, fumbles the occluded grasp. Fix: 10 occluded-grasp demos.
  - id 7 (regression, above).
```

Every claim is a number with a trial count. Every failure has a mode and a next step. No "it works now." That is the bar.

---

## Stretch

- **The demo-efficiency curve.** Fine-tune at 10/25/50 demos and plot instructions-passed vs demo count. A defense slide that says "I'm data-starved here, saturated there" is rare and impressive.
- **A scaffold for recovery.** Wire a behavior-tree search-then-ask fallback for the recovery instructions and show they pass via the scaffold. Discuss why a scaffold can beat learned recovery for safety and interpretability.
- **Per-axis breakdown.** Report instructions-passed broken out by failure axis (grounding / spatial / distractor / phrasing / recovery). It turns one number into a map of your policy's competence.
- **Cross-seed stability.** Re-run the suite under two additional master seeds and report whether your 16/20 holds. A number that is stable across seeds is one you can defend hard.

---

## What this sets up

Week 45 begins the interview ramp, and the very first thing a robotics-startup interviewer wants is for you to walk them through a real result on a real system. This package *is* that result. Week 47 polishes your three flagship portfolio projects — and the capstone is one of them; this report is the centerpiece of its README. Week 48 is the defense, where the panel reads this report, watches your deploy clip, and asks why instruction 18 still fails — and you will have the answer written down. Every hour you spend here is an hour you do not have to scramble for later. Build the package well.

---

*Push the package to your capstone repo when the report is honest and complete. Then go to [Week 45 — Capstone build sprint 4 + interview-prep ramp].*
