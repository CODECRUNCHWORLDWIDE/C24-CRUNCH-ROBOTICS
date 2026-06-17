# Week 32 Homework

Six practice problems that turn this week's lectures into the wrapped, measured, defensible learned-policy stack you submit as the Phase 4 milestone and defend at the second-midterm review. The full set should take about **5 hours**. Work in your Week 32 capstone repository so each problem produces a committed artifact you point at during the review.

The headline deliverable is **Problem 4 — the intervention-rate report**, the number the midterm panel asks for first. Treat it as the artifact a reviewer reads, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Finish the constraint set for your robot

**Problem statement.** Take the `action_bounds.py` and `notes/constraint-set.md` from Exercise 1 and complete them for *your* robot: velocity, acceleration, joint-limit, and workspace bounds, each with a real number from your URDF / datasheet / operating room and a one-line reason. Add the acceleration clamp (bound the delta between consecutive actions) and a keep-out volume around a point in `base_link`.

**Acceptance criteria.**

- `notes/constraint-set.md` has every bound with units and a reason; numbers come from your actual robot, not placeholders.
- `action_bounds.py` includes the acceleration clamp and the keep-out check, with a small test asserting each fires on an out-of-bounds input.
- You can state in one sentence why each bound is what it is (the reason a reviewer will probe).
- Committed.

**Hint.** The URDF `<limit velocity="..." effort="...">` tags give you the joint bounds. The operating room and "a person can react to ≤ 1 m/s" give you the base velocity. The keep-out radius should be at least the arm's reach plus a margin around a standing person.

**Estimated time.** 40 minutes.

---

## Problem 2 — Wrap your best policy with the filter and prove it fires

**Problem statement.** Put the Exercise 2 safety filter *in the action path* between your best learned policy (Weeks 29–31) and the controller. Run a handful of episodes. Confirm the filter clamps over-speed actions and rejects out-of-workspace ones — and that safe actions pass. If your filter never fires across the episodes, your bounds are too loose; tighten them to the real envelope and re-run.

**Acceptance criteria.**

- `notes/wrap-the-policy.md` records the filter sitting between policy and controller, with the topic wiring (`/policy/action` → filter → `/policy/filtered_action`).
- Over the episodes, the filter logs at least some clamps and at least one rejection (or you document why your policy is so well-behaved that you had to inject a deliberate OOD observation to trip it — which is the more honest result).
- The filter's measured p95 latency is recorded alongside the policy's inference latency, confirming the filter is the cheaper of the two.
- Committed.

**Hint.** If your policy is clean enough that nothing trips the filter, inject an out-of-distribution observation (a perceived object pose far outside the training distribution) — the filter should reject the resulting action. A filter that never fires is the too-loose defect; you must show it *can* fire.

**Estimated time.** 60 minutes.

---

## Problem 3 — Wire the three-rejection fallback in the behavior tree

**Problem statement.** Add the classical-fallback branch to your behavior tree (`capstone_pick_place.xml` or your task tree): a `ReactiveFallback` whose first child is the safety-guarded learned policy (fails after three consecutive rejections) and whose second child is the classical planner (MoveIt2 + OMPL for the arm, or a sampling planner for the base). Force three consecutive rejections and confirm the BT switches to the planner, which completes the task.

**Acceptance criteria.**

- The BT XML has a `ReactiveFallback` with the policy branch and the classical-planner branch, viewable in Groot 2.
- Forcing three consecutive rejections (a stuck-policy observation, or the `--unsafe-burst` stub) switches the tree to the planner, which completes the task.
- `notes/fallback.md` records the Groot 2 screenshot of the switch and confirms the rejection counter resets on a safe action.
- Committed.

**Hint.** The `ReactiveFallback` ticks its first child every tick; when the `SafetyGuardedPolicy` node returns `FAILURE` (on the third consecutive rejection), the `ReactiveFallback` ticks the classical branch. Confirm in Groot 2 that you *see* the tick move from the policy branch to the planner branch.

**Estimated time.** 60 minutes.

---

## Problem 4 — The intervention-rate report (headline deliverable)

**Problem statement.** This is the number the midterm panel asks for first. Run a focused eval — tens of episodes on your one constrained pick-and-place task — with the wrapper and fallback live, and produce `notes/intervention-rate.md` reporting: success rate, clamps by constraint, rejections, fallback-episode rate, and the filter's p50/p95 latency vs. policy inference time. Read the breakdown as a diagnosis: which subtask concentrates the rejections, and what that tells you to collect more demos for.

**Acceptance criteria.**

- `notes/intervention-rate.md` reports all five numbers (success, clamps-by-constraint, rejections, fallback rate, latency) over a stated number of episodes.
- The report *interprets* the breakdown — e.g., "rejections concentrate on the grasp subtask, so the next data-collection round targets grasps" — not just lists numbers.
- The fallback rate is reported honestly even if it is high; a high success rate with a high fallback rate is disclosed as "the policy is being carried by the planner here."
- Committed.

**Hint.** Use the Exercise 3 `InterventionMeter`. The intervention *rate* is fallback-episodes / total-episodes (the strong signal); report the action-level clamp/reject counts alongside it (the training-quality signal). If your fallback rate is 0% over many episodes, run Problem 5's ablation before claiming success — zero may be the too-loose-filter defect.

**Estimated time.** 60 minutes.

---

## Problem 5 — The ablation: prove the leash is load-bearing

**Problem statement.** Disable the safety filter and re-run the episodes from Problem 4. Document the unsafe actions that now execute — the table-strikes, the over-speed twists, the out-of-workspace reaches — that the filter previously caught. Produce a filter-on-vs-filter-off comparison table. This is the strongest evidence for the midterm that the leash is real, not decorative.

**Acceptance criteria.**

- `notes/ablation.md` has a table comparing filter-on and filter-off over the same episodes: success rate, and (filter-off) the count and type of unsafe actions that executed.
- At least one concrete unsafe action is named (e.g., "episode 7: the gripper drove 4 cm below the table surface; with the filter on, this action was rejected and the fallback completed the grasp").
- The ablation is run in **sim only** (you are deliberately letting unsafe actions execute to measure them) and the note says so explicitly.
- Committed.

**Hint.** If disabling the filter changes *nothing* — no unsafe actions appear — then either your policy is genuinely clean (rare) or your filter was too loose to begin with (likely). Either way, that result is informative and you report it honestly.

**Estimated time.** 45 minutes.

---

## Problem 6 — Update the hazard log for learned controllers

**Problem statement.** Expand your Week-24 hazard log with the learned-policy hazards from Lecture 2 §3: OOD action, multimodal collapse, silent-confidence failure, reward-hacked behavior, filter-latency spike, and too-loose filter. For each, give the failure mode, the effect, a provisional severity, the mitigation, and the node/topic that implements the mitigation.

**Acceptance criteria.**

- `safety-case/hazard-log-learned-policy.md` lists at least six learned-policy hazards, each with mode, effect, severity, mitigation, and owning artifact.
- The reward-hacking row explicitly connects to the eval protocol (you evaluate on held-out / randomized worlds so a sim-only behavior is exposed) — the bridge to Phase 5.
- Each mitigation names a real component in your stack (the filter, the confidence gate, the fallback, the eval protocol), not "be more careful."
- Committed.

**Hint.** Mirror the table in Lecture 2 §3. The OOD-action hazard is mitigated by the action clamps + state guards (which catch by consequence) plus the fallback; the reward-hacking hazard is mitigated by the filter (action) *and* the randomized eval (behavior). A hazard with no mitigation is a finding the panel catches — so don't leave any blank.

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Finish the constraint set | 40 min |
| 2 — Wrap the policy, prove it fires | 60 min |
| 3 — Wire the fallback BT branch | 60 min |
| 4 — Intervention-rate report (headline) | 60 min |
| 5 — The ablation | 45 min |
| 6 — Hazard-log update | 45 min |
| **Total** | **~5 h 10 min** |

---

## Submission

Push the entire `notes/`, `safety-case/`, the wrapped BT, and `action_bounds.py` to your Week 32 capstone repository. The instructor (and the midterm panel) reviews by:

1. Reading the intervention-rate report and confirming it reports the five numbers with methods.
2. Re-running your wrapper and watching a live rejection and a live fallback.
3. Confirming the ablation demonstrates the filter catches real unsafe actions.
4. Confirming the hazard log names real mitigations with owning artifacts.

A submission whose wrapper fires, whose fallback switches, whose intervention rate is reported honestly, and whose ablation proves the leash is load-bearing is a pass. The most common review-fail is an intervention-rate report with no method, or a wrapper that never fires (the too-loose defect) presented as a clean run — report what you measured and how, and prove the filter *can* fire.

---

## Rubric (100 points)

| Problem | Points | What earns them |
|---------|-------:|-----------------|
| P1 — Constraint set | 15 | Every bound with units and a reason; accel clamp + keep-out added with tests. |
| P2 — Wrapped policy fires | 20 | Filter in the action path; clamps + at least one rejection shown; filter cheaper than policy. |
| P3 — Fallback BT branch | 15 | `ReactiveFallback` in Groot 2; three-rejection switch demonstrated; counter resets. |
| P4 — Intervention-rate report | 20 | Five numbers with methods; breakdown interpreted; fallback rate disclosed honestly. |
| P5 — Ablation | 15 | Filter-on-vs-off table; concrete unsafe action named; sim-only stated. |
| P6 — Hazard-log update | 15 | Six+ learned-policy hazards; each with mitigation + owning artifact; reward-hacking → eval bridge. |

---

**References**

- C24 Week 24 — the original hazard log; Week 28 — the reward-hacking problem.
- *Safe Learning in Robotics (Brunke et al.)*: <https://arxiv.org/abs/2108.06266>
- *Control Barrier Functions (Ames et al.)*: <https://arxiv.org/abs/1903.11199>
- *Specification gaming / reward hacking (DeepMind)*: <https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/>
- *BehaviorTree.CPP — control nodes*: <https://www.behaviortree.dev/docs/nodes-library/control-nodes/>
- *MIL-STD-1629A — FMEA*: search "MIL-STD-1629A FMEA"
