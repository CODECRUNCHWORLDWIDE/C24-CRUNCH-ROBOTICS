# Week 44 Homework

Five problems that harden the week's apparatus and your understanding of it. The full set should take about **5 hours**. Work in your capstone repo so each problem produces at least one commit you can point to at the defense.

Each problem includes a **problem statement**, **deliverables**, a **hint**, and an **estimated time**. A grading rubric is at the end.

---

## Problem 1 — Unit-test your scorer before you trust it

**Problem statement.** The success rubric is the load-bearing predicate of the entire week. Write `scorer_test.py` that exercises `score_trial` (from exercise 2) against constructed `TrialOutcome` cases and asserts the correct verdict:

1. A clean success (object 2 cm from destination, no collision, 40 s) → `True`.
2. A near-miss placement (object 8 cm from destination) → `False`.
3. A collision during an otherwise-good trial → `False`.
4. A timeout (object placed but at 95 s, timeout 90 s) → `False`.
5. A recovery instruction with a clean abort (NaN destination, reported complete) → `True`.
6. A recovery instruction where the robot grasped a distractor (collision flag set) → `False`.

**Deliverables.** `scorer_test.py` committed; `pytest scorer_test.py` passes all six cases.

**Hint.** Construct `TrialOutcome` directly with `numpy` arrays; you do not need ROS running for this. Case 5 needs `destination_xyz=np.full(3, np.nan)` and `is_recovery=True`. The whole point is that you trust the scorer because you tested it, not because it looks right.

**Estimated time.** 40 minutes.

---

## Problem 2 — Compute and interpret a Wilson interval by hand

**Problem statement.** For each of these `(k, n)` results, compute the 95% Wilson interval (use the `wilson_interval` function from the exercises) and write one sentence interpreting it:

1. `(80, 100)` — a strong suite total.
2. `(3, 5)` — a single instruction at threshold.
3. `(15, 20)` — instructions-passed exactly at the bar.
4. `(0, 5)` — an instruction that never succeeds.

Then answer: for case 2, would you be comfortable claiming the instruction "passes"? Why or why not, given the interval width?

**Deliverables.** `notes/wilson.md` with the four intervals and your interpretations, plus the answer to the case-2 question.

**Hint.** Case 2's interval is *wide* — five trials is not many. The honest read is "passes at this sample size, but I have low confidence in the exact rate; more trials would tighten it." That nuance is exactly what a panel probes for.

**Estimated time.** 45 minutes.

---

## Problem 3 — Stratification audit of your suite

**Problem statement.** Open your frozen `eval_suite.yaml` and produce a stratification audit: a table with one row per failure axis showing how many of your twenty instructions tag it, and a short paragraph answering — *if my policy fails exactly the recovery instructions, will my suite reveal that, or will it be buried in an aggregate?* If any axis has zero or one instruction, justify it or add coverage in a `v1.1.0` (and note that bumping the version voids prior numbers).

**Deliverables.** `notes/stratification-audit.md` with the per-axis count table and the diagnosability paragraph.

**Hint.** A suite where recovery has two instructions out of twenty will show a recovery weakness as "2 of my 4 failures are recovery" — visible. A suite with zero recovery instructions cannot reveal a recovery weakness at all. The audit is checking your suite can *see* the failures it is meant to catch.

**Estimated time.** 45 minutes.

---

## Problem 4 — A demo-leakage check

**Problem statement.** Write `leakage_check.py` that loads your frozen suite's twenty instruction texts and your 50-demo dataset's instruction strings, and asserts that **no demo instruction is an exact match** for any suite instruction. As a softer check, print any demo instruction that shares ≥ 80% of its tokens with a suite instruction, for you to review by hand (high token overlap is allowed — same family — but you should eyeball that the *specific instance* differs).

**Deliverables.** `leakage_check.py` committed; a run log showing zero exact matches and your hand-review notes on any high-overlap pairs.

**Hint.** Exact-match leakage is disqualifying and easy to catch programmatically. Token-overlap is a heuristic, not a rule — "get the red cup off the left bench" (demo) and "bring me the red cup from the left bench" (suite) overlap heavily and that is *fine*, because the scenes and exact phrasing differ. The check surfaces pairs for you to judge; it does not auto-fail them.

**Estimated time.** 1 hour.

---

## Problem 5 — Write the failure-diagnosis dossier for your current failures

**Problem statement.** Run the diff on your latest baseline and fine-tuned reports. For every instruction currently failing (below threshold) or regressed, write a `FAILURE-DIAGNOSIS.md` entry with exactly three parts: (1) the failure mode (one of grounding / grasp / placement / language-binding), (2) evidence (a Foxglove replay screenshot or an action/perception trace), (3) the next concrete fix (named data count or scaffold). If you currently have zero failures, write the diagnosis for the *closest-to-failing* two instructions (lowest `k/N` that still passed) — knowing where the margins are thin is itself a deliverable.

**Deliverables.** `FAILURE-DIAGNOSIS.md` with one rigorous entry per failing/regressed (or thinnest-margin) instruction.

**Hint.** Reuse the failure-mode decision table from challenge 1's hints. The discipline that scores well: every entry's "next fix" is a thing you could start Monday morning — a count and a family, or a named scaffold — not "investigate further." If you genuinely do not know the mode, say so and write the *experiment* that would tell you (e.g., "issue a contrasting instruction to distinguish grounding from language-binding").

**Estimated time.** 1 hour.

---

## Time budget recap

| Problem | Estimated time |
|--------:|---------------:|
| 1 | 40 min |
| 2 | 45 min |
| 3 | 45 min |
| 4 | 1 h 0 min |
| 5 | 1 h 0 min |
| **Total** | **~4 h 10 min** |

---

## Grading rubric

Graded out of 100. This homework is evidence you can *measure and reason about* a policy, which is the skill the defense tests.

| Criterion | Points | What full marks looks like |
|-----------|-------:|----------------------------|
| **Scorer correctness (P1)** | 20 | All six cases pass; the recovery-exception cases (5, 6) are handled, not just the standard ones. |
| **Statistical honesty (P2)** | 15 | Four correct Wilson intervals; the case-2 interpretation acknowledges the wide interval at N=5 rather than overclaiming. |
| **Suite diagnosability (P3)** | 20 | The audit shows the suite can reveal an axis-clustered weakness; thin or missing axes are justified or fixed (with the version-bump caveat noted). |
| **Leakage discipline (P4)** | 20 | Zero exact matches proven programmatically; high-overlap pairs reviewed by hand with a defensible call on each. |
| **Diagnosis quality (P5)** | 20 | Every entry has a mode, real evidence, and a *concrete, startable* next fix — no "needs more work". |
| **Reproducibility** | 5 | Everything is committed; a fresh clone can run P1 and P4 scripts. |

**Passing is 70.** A 90+ homework is one where every number is defensible, every diagnosis is concrete, and a stranger reading it would trust your eval. That stranger is the week-48 panel — write for them.

---

When all five problems are committed, your homework reinforces the mini-project: P1's scorer, P3's audit, and P5's dossier are the same artifacts the mini-project ships. Do the homework first and the mini-project gets shorter. Push your repo and open the [mini-project](./07-mini-project/00-overview.md).
