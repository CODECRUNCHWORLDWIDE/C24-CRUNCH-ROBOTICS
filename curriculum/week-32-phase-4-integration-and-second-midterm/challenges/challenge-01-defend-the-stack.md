# Challenge 1 — Defend the Learned-Policy Stack

**Estimated time:** ~2 hours (after the wrapper and fallback are wired). **No starter file** — you assemble the defense from your own components.

## The challenge

Run a full dry run of the second-midterm architecture review. You defend your learned-policy stack to a **peer panel** (two or three classmates, or an instructor) against the five-part rubric, with the safety filter and the fallback **firing live**, and the intervention-rate breakdown as your headline number. The panel did not build your stack. Their job is to find the clause you are hoping nobody enforces — exactly as the real panel will at the midterm.

This is the rehearsal that turns review day from a discovery into a confirmation. The skill it grades — defending an architecture you built to someone skeptical, with live evidence and honest numbers — is the skill the midterm grades and the skill that gets you hired.

## The five things you defend (the rubric)

The panel asks about each. You must have a *live demonstration* or a *number with a method* for every one. Prepare all five.

1. **The training pipeline.** How you collected demonstrations (or set up the RL environment), how many, what's in them, how you handled covariate shift (DAgger rounds, augmentation). Be ready for: "How many demos, and is your eval set actually held out from them?"

2. **The eval protocol.** Your success predicate (task-complete, in time, no safety violation), your held-out eval set, your train/eval split. Be ready for: "What counts as a success — does a slow success with one clamp count? Did you leak eval data into training?"

3. **The safety wrapper — demonstrated live.** Run the wrapper and make it reject an action *in front of the panel*. Use the `--demo`'s unsafe burst, or force an out-of-distribution observation. Be ready for: "Show me an action get rejected. What's the filter's p95 latency against the policy's inference time? Is it a CBF or a heuristic projection?"

4. **The fallback path — demonstrated live.** Open Groot 2, force three consecutive rejections, and let the panel watch the `ReactiveFallback` switch from the policy branch to the classical planner, which then completes the task. Be ready for: "Does the counter reset on a safe action? What happens on the *fourth* episode if the policy is still stuck?"

5. **The hazard-log update.** The learned-policy hazards (OOD action, multimodal collapse, silent confidence, reward hacking, filter latency, too-loose filter), each mapped to a mitigation and an owning artifact. Be ready for: "What hazard does the learned policy introduce that your classical stack from Week 24 didn't have, and how do you mitigate it?"

## The headline number

When the panel asks "is your stack safe?", do not say "yes." Give the intervention-rate breakdown:

> "Over 40 episodes: 92.5% success. The filter clamped 17 actions and rejected 22. The fallback fired on 3 episodes and completed all 3. The filter's p95 latency is 4.8 ms against a 31 ms policy. And with the filter *ablated*, 3 episodes drove actions the filter would have caught — a through-the-table grasp and two over-speed twists."

Every claim is a number; every number has a method; the ablation proves the leash is load-bearing. That is a defensible answer. "It felt safe, the demos all worked" is not.

## Acceptance criteria

Each criterion must be demonstrable live or with a number you can reproduce. If you cannot demonstrate it, it is not met.

- [ ] **Live rejection.** You make the safety filter reject an action in front of the panel (the `--demo` unsafe burst or a forced OOD observation). The panel sees the `REJECT` verdict.
- [ ] **Live fallback.** You force three consecutive rejections and the panel watches the BT `ReactiveFallback` switch to the classical planner in Groot 2, and the planner completes the task.
- [ ] **The intervention-rate breakdown** is reported: success rate, clamps by constraint, rejections, fallback-episode rate, and filter p50/p95 latency vs. policy inference time.
- [ ] **The ablation result** is presented: with the filter off, the unsafe actions that now execute, named and counted. This is the proof against the too-loose-filter defect.
- [ ] **The hazard-log update** is shown, with at least the OOD-action and reward-hacking rows, each mapped to a mitigation and an owning artifact.
- [ ] **The training pipeline and eval protocol** are stated: demo count, train/eval split, success predicate.
- [ ] **The panel signs off** — or names the artifact that did not hold up. A peer reviewer records which of the five they probed hardest and whether your answer held.

## The questions the panel must ask (give them this list)

Hand your peer panel this list so the dry run covers the rubric's hard spots:

- "Your success rate is X%. What's your *fallback* rate? Is the policy doing the work or is the planner carrying it?"
- "Show me an action get rejected, right now."
- "Your filter — is it a clamp, or does it roll the action forward? What's its latency?"
- "Force the fallback. I want to see the BT switch."
- "What does your intervention breakdown tell you about *which subtask* to collect more demos for?"
- "If I turn the filter off, what unsafe thing happens? Show me the ablation."
- "What new hazard does the learned policy add over your Week-24 classical stack?"

If you can answer all seven with a live demonstration or a number, you are ready for the real review. If any answer is "um, let me think" or "it should be fine," that is the gap to close this week.

## Deliverable

- A short note `notes/midterm-dry-run.md` recording: the panel members, which of the five artifacts they probed hardest, the questions you could not answer cleanly, and the fixes you applied before the real review.
- A screen recording (≤ 3 minutes) of the live rejection and the live fallback, so you have the demonstration ready to replay if the real review is remote.
- The ablation result table (filter-on vs. filter-off, unsafe actions caught).

## Stretch

- Run the dry run with the filter **deliberately set too loose** (bounds way beyond the real envelope) and have the panel try to catch that it never fires. This rehearses the defense *and* proves to you that you can detect the too-loose-filter defect from the outside — which is exactly what the panel will try to do.
- Defend the **CBF** version: if you built the QP-based projection (stretch goal), be ready to explain `ḣ ≥ -α·h` and why the QP gives the *optimal* projection where the heuristic gives a good-enough one.

This challenge is the rehearsal for the midterm sign-off and, eight weeks out, for the Week 48 capstone defense, which *is* a panel reading your work against the contract. If you can defend the leash now, with live evidence and honest numbers, the real reviews are a rehearsed play instead of a panic.
