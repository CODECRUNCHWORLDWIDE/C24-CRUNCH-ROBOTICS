# Week 34 Homework

Six problems that force the sim-to-real discipline into your fingers. The full set should take about **5 hours**. Work in your Week 34 Git repository (the same workspace as the exercises and the `crunchbot_domain_rand` mini-project) so every problem produces at least one commit you can point to at the Phase 5 milestone (Week 40) and the capstone safety case (Week 41).

The headline deliverable is **Problem 4 — the gap-closure write-up**, the syllabus artifact ("quantify the gap closure"). Treat it as the evidence a safety reviewer reads, not a journal entry.

Have a GPU available for Problems 2 and 4 (the randomized training and eval). Problems 1, 3, 5, and 6 need no GPU. If your challenge run is done, Problems 2 and 4 reuse it. Path B substitutes episode-level Gz randomization for parallel Isaac throughout; say so.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Name your gap

**Problem statement.** For your Week 28 task, write `notes/week-34/my-gap.md` enumerating which of the four gap families (visual, dynamics, sensor, latency) your policy is *actually exposed to*, and why. Then state which families you'll randomize and which you'll skip, with a one-line justification for each skip.

**Acceptance criteria.**

- `notes/week-34/my-gap.md` addresses all four families: exposed or not, with a reason.
- A randomize/skip decision per family, each justified by the policy's inputs/physics.
- At least one family is justified as *skip* (you should not randomize everything blindly).
- Committed.

**Hint.** A state-based reach policy that reads joint states and outputs torques is barely exposed to the *visual* gap — skipping visual DR there is correct and frees capacity for dynamics. Match the family to the exposure (Lecture 1 §2.4).

**Estimated time.** 35 minutes.

---

## Problem 2 — Train with randomization and read the curve

**Problem statement.** Augment your Week 28 PPO with the Exercise-2 randomization config (≥ 2 families) and train. The graded part is reading the training dynamics: capture the **reward curve** under randomization next to the nominal run and explain the difference.

**Acceptance criteria.**

- A randomized training run exists, using the Exercise-2 config applied on every env reset.
- `notes/week-34/training-curves.md` shows the nominal vs. randomized reward curves (TensorBoard screenshots or logged values).
- You explain *why* the randomized curve is noisier/slower (the task is harder across worlds) and what it would mean if it converged identically to nominal (ranges too narrow).
- Committed.

**Hint.** A randomized run that matches nominal's curve exactly is a red flag — your ranges aren't doing anything. Widen them and the curve should separate (noisier, slower, often a lower asymptote). Slower-but-broader is the signal of real randomization (Lecture 2 §2.1).

**Estimated time.** 1 hour (excludes GPU wall-time if reusing the challenge run).

---

## Problem 3 — Two recipes, justified

**Problem statement.** Polish the Exercise-1 recipes into a clean reference at `notes/week-34/recipes.md`: the manipulation recipe and the navigation recipe, each as a table (parameter, family, nominal, range, why), plus a paragraph contrasting them and a "do NOT randomize" list for each.

**Acceptance criteria.**

- Both recipes as tables, ≥ 6 parameters each, ≥ 3 families each.
- A contrast paragraph explaining why the two recipes differ (different exposures).
- A "do NOT randomize" list per task (parameters that would change the task itself if randomized — e.g., the goal location).
- Committed.

**Hint.** The "do NOT randomize" list is the senior touch. Randomizing the goal pose for a nav policy doesn't build robustness — it changes the task. Knowing what to hold fixed is as important as knowing what to vary (Exercise 1 stretch).

**Estimated time.** 40 minutes.

---

## Problem 4 — The gap-closure write-up (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Using your nominal and randomized policies and a held-out "real-style" world, write the gap-closure analysis at `notes/week-34/gap-closure.md` against this template:

1. **Summary** — one sentence: the nominal and randomized held-out success rates and the gap closed.
2. **Setup** — the task, the randomization recipe (families + ranges), and how you built the held-out world so its parameters are genuinely out-of-training.
3. **Results** — the gap-closure table from the Exercise-3 script: both policies on both worlds, explicit `n`, CIs, the gap, and the sanity verdict.
4. **What carried the gap** — which family did the most work (ablate if you can), with a number.
5. **Honest limits** — what randomization could *not* close for your task, why the held-out world is a proxy for reality, and why the safety filter still matters.

**Acceptance criteria.**

- `notes/week-34/gap-closure.md` exists, hits all five headings.
- The results table has explicit `n` (≥ 50), CIs, the gap-closed number, and an **OK sanity verdict** (or a documented diagnosis if it was SUSPECT).
- The held-out world's parameters are explicitly shown to be out-of-training.
- The honest-limits section names a specific thing randomization didn't close and reaffirms the safety wrapper.
- Committed.

**Hint.** If the mini-project's `gap.py` is done, this is mostly assembling its `reports/gap.md` into prose. The grading weight is on parts 4–5: a reviewer wants the *honest* engineer who says "visual DR carried 40 of 53 points; it can't close the genuine-novel-object gap, so the safety filter stays." A write-up claiming "sim-to-real solved" fails on its face.

**Estimated time.** 1 hour 15 minutes (excludes eval wall-time if reusing the challenge run).

---

## Problem 5 — Find the over-randomization cliff

**Problem statement.** Deliberately widen one or two ranges (friction, mass) until your policy *can't learn the task* — the reward flatlines low and the policy goes maximally conservative. Document the boundary in `notes/week-34/over-randomization.md`: the range at which learning still works vs. the range at which it collapses.

**Acceptance criteria.**

- `notes/week-34/over-randomization.md` shows at least one "learns fine" range and one "collapses" range for the same parameter, with the reward outcome of each.
- You correctly identify the collapse as **over-randomization** (conservative policy, low flat reward) and not a trainer bug.
- A one-sentence statement of the practical rule: widest distribution the policy can *still solve*, not widest period.
- Committed.

**Hint.** You don't need full training runs — short runs are enough to see the reward flatline under absurdly wide ranges (e.g., friction 0.05–5.0). The point is to *recognize* the failure mode so you don't misdiagnose it as a broken reward later (Lecture 2 §2.3, challenge stretch).

**Estimated time.** 45 minutes.

---

## Problem 6 — System ID to center the distribution

**Problem statement.** Argue, in `notes/week-34/system-id.md`, how a *measured* real parameter would improve your randomization. Pick one parameter (say floor friction): describe how you'd measure it on the real robot, and explain why centering your randomization range on the measured value (rather than a guessed nominal) closes more of the gap — connecting to Lecture 1's "can't close a gap you never sampled."

**Acceptance criteria.**

- `notes/week-34/system-id.md` picks one parameter, describes a concrete real-world measurement, and explains the centering argument.
- It correctly frames system ID as *complementary* to DR (center the distribution), not a replacement for it (don't chase one perfect value).
- It connects to the "bracket reality" requirement: a range centered on the measured mean is more likely to contain the true value.
- Committed.

**Hint.** The synthesis is: system ID alone (chase one perfect sim) loses; DR alone (guess the center) is good; DR *centered* on a quick system-ID measurement is best — wide enough to bracket reality, centered where reality actually is. That's the 2026 best-practice (Lecture 1 §1.2, mini-project stretch).

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Name your gap | 35 min |
| 2 — Train with randomization | 1 h 0 min |
| 3 — Two recipes, justified | 40 min |
| 4 — Gap-closure write-up (headline) | 1 h 15 min |
| 5 — The over-randomization cliff | 45 min |
| 6 — System ID to center the distribution | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_domain_rand` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 40's capstone-in-sim and Week 41's safety case both cite gap-closure evidence. Then take the [quiz](./05-quiz.md) with your notes closed.
