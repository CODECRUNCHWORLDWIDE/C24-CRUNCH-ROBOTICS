# Week 25 Homework

Six problems that revisit the week's grasp geometry and force it into your fingers. The full set should take about **5 hours**. Work in your Week 25 Git repository (the same workspace as the exercises and the `crunch_grasp` mini-project) so every problem produces at least one commit you can point to when you compare against Contact-GraspNet in Week 26.

The headline deliverable is **Problem 4 — the grasp-failure postmortem**. Treat it as the artifact a reviewer reads, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — The friction-cone tolerance table

**Problem statement.** For a single antipodal grasp on a cylinder (the Exercise-2 best grasp), compute how much **pose error** the grasp tolerates before it stops force-closing, as a function of friction. Perturb the closing line's angle and find the maximum angle at which the grasp still passes the friction-cone test, for `mu ∈ {0.2, 0.3, 0.5, 0.8}`. Build a table.

**Acceptance criteria.**

- `notes/friction-tolerance.md` has a table: `mu | alpha = arctan(mu) | max tolerated angle | tolerance margin`.
- The max tolerated angle equals `alpha` (the cone boundary) for a perfectly-opposed start, and the table shows it growing with `mu`.
- A one-line conclusion: higher-friction objects tolerate more pose error, which is why slick objects are unforgiving.
- Committed.

**Hint.** Start from a perfectly antipodal grasp (angle 0) and increase the closing-line tilt in small steps, re-running `antipodal_score` until it returns 0. The angle where it hits 0 is exactly `alpha`. This *is* the "how much can my pose be off" number from Lecture 1 §6.

**Estimated time.** 40 minutes.

---

## Problem 2 — Box vs. cylinder candidate counts

**Problem statement.** Run your Exercise-2 sampler on a cylinder cloud and a box cloud (extend the synthetic generator for a box). Compare the *number* and *distribution* of feasible antipodal candidates. Explain the difference geometrically.

**Acceptance criteria.**

- `notes/box-vs-cylinder.md` records the candidate count and a description of where the candidates cluster, for both objects.
- You explain why the cylinder has a *continuum* of antipodal grasps (any diameter pass) while the box has a small number of *discrete* good grasp regions (opposing face pairs).
- A visualization (image) of the top grasps on each.
- Committed.

**Hint.** On a cylinder, every diameter is antipodal, so candidates are everywhere at the right width. On a box, antipodal pairs live on opposing parallel faces — three pairs of faces, three width regimes — so the candidates cluster into discrete bands. The shape of the object shapes the candidate set.

**Estimated time.** 45 minutes.

---

## Problem 3 — The gripper-frame convention against your URDF

**Problem statement.** Take your Week-23 arm's URDF and identify the gripper's tool frame and its convention (which axis approaches, which closes). Then adjust `grasp_orientation` from Exercise 3 so the grasp pose it builds matches *your* gripper's convention. Verify by planning to a grasp pose in MoveIt2 and confirming the gripper approaches correctly (not 90° wrong).

**Acceptance criteria.**

- `notes/gripper-convention.md` names your gripper's tool frame and states which axis is approach and which is closing.
- Your `grasp_orientation` column assignment matches the URDF convention, with a comment explaining the mapping.
- A screenshot or recording shows MoveIt2 planning to a grasp pose with the gripper oriented correctly (fingers straddling the closing line, approaching along the approach axis).
- Committed.

**Hint.** This is the silent failure from Lecture 2 §1.1. The URDF is the ground truth, not REP 103 and not the exercise's default. If the gripper sweeps sideways through the object in MoveIt2, your column assignment is wrong — rotate the convention until the approach matches.

**Estimated time.** 60 minutes.

---

## Problem 4 — The grasp-failure postmortem (headline deliverable)

**Problem statement.** Engineer a grasp *failure* on purpose — pick a grasp from your planner, perturb its pose (shift it 5 mm, tilt it 10°) or pick a deliberately edge-of-cone grasp, execute it (in sim or with a careful real test), and watch it fail (the object spins out, a finger misses, the approach knocks it over). Then write a one-page postmortem classifying the failure.

**Acceptance criteria.**

- `notes/grasp-failure-postmortem.md` exists, fits roughly one page (350–550 words), and has these sections:
  1. **Summary** — one sentence: what grasp, what failed, what you observed.
  2. **Classification** — is this a **pose** failure, a **width** failure, an **approach/collision** failure, or a **perception** (bad cloud) failure? State which and why.
  3. **Root cause** — the specific geometry: which friction-cone margin was violated, or how far the pose was off, with the number.
  4. **Why the score didn't catch it** — if the planner scored this grasp highly, why? (Often: high antipodal score but tiny pose-error tolerance, or a missing collision check.)
  5. **Fix** — the geometric mitigation (margin, prefer centered grasps, add the collision gate, fix the cloud).
- The classification is *specific* — "pose failure: the grasp had 4 mm of pose tolerance and my pose was 5 mm off," not "the grasp was bad."
- Committed.

**Hint.** This is the "pose failure vs. policy failure vs. perception failure" distinction from Lecture 2 §3.4 made concrete. The most instructive failure is a *high-scoring* grasp that still fails — because it teaches that the score is a heuristic, and the term it didn't capture (pose-error tolerance, or a bad cloud) is the one that bit you.

**Estimated time.** 60 minutes.

---

## Problem 5 — Add the collision gate to your scorer

**Problem statement.** Your Exercise-2 sampler scores antipodal quality and width. Add the **collision-freedom** gate and the **approach-sanity** term from Lecture 2 §2.1 so a grasp that approaches up through the table, or whose gripper geometry hits the table, scores ~0. Re-rank and show that bad-approach grasps drop out of the top-10.

**Acceptance criteria.**

- Your scorer now includes the approach-sanity term (penalize approaching into the table normal) and a collision gate (a grasp whose gripper box intersects the table plane scores 0).
- `notes/scorer-upgrade.md` shows a before/after top-10 on the same cloud, demonstrating that a grasp which was high-ranked on antipodal quality alone but approaches through the table is now gated out.
- Committed.

**Hint.** A simple collision gate: model the gripper as a box at the grasp pose and test whether it intersects the table plane (z < table_height + clearance). The approach-sanity term is `0.5 - 0.5 * dot(approach, table_up)` clamped to `[0,1]` — it rewards coming down or sideways and punishes coming up from below.

**Estimated time.** 45 minutes.

---

## Problem 6 — Compare one grasp to an ACRONYM grasp

**Problem statement.** Pick an object that exists in ACRONYM (a mug, a bottle). Download a few ACRONYM grasps for it, and generate grasps for the same object with your heuristic. Compare: do the learned/simulated grasps land in the same regions as yours? Where do they differ?

**Acceptance criteria.**

- `notes/acronym-compare.md` records a handful of ACRONYM grasp poses and your heuristic's top grasps for the same object.
- A comparison: which regions both agree on, and at least one grasp the ACRONYM set has that your heuristic misses (or vice versa), with a geometric explanation.
- One sentence on what the simulated/learned grasp set captures that your single-object antipodal heuristic does not (e.g., a handle grasp, a grasp robust to the object's mass distribution).
- Committed.

**Hint.** ACRONYM grasps are *physically simulated and shaking-tested*, so they encode dynamic stability your static antipodal test ignores — a grasp that is geometrically antipodal but unstable under the object's mass distribution gets labeled a failure in ACRONYM. That is part of what the data buys (Lecture 2 §3.3).

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Friction-cone tolerance table | 40 min |
| 2 — Box vs. cylinder candidates | 45 min |
| 3 — Gripper-frame convention vs. URDF | 1 h 0 min |
| 4 — Grasp-failure postmortem (headline) | 1 h 0 min |
| 5 — Add the collision gate | 45 min |
| 6 — Compare to ACRONYM | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_grasp` [mini-project](./mini-project/README.md) is in the same workspace — Week 26 imports it to compare against Contact-GraspNet. Then take the [quiz](./quiz.md) with your notes closed.
