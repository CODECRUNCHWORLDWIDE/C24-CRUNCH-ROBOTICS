# Exercise 1 — Build Two Randomization Recipes

**Goal:** Practice the judgment that precedes any randomization code: deciding **what to randomize and how wide** for a given task, and justifying each choice against the family-to-exposure rule (Lecture 1 §2.4). You will build two complete recipes — one for a manipulation (grasp) policy, one for a navigation policy — and discover that they are *not* the same list. Randomizing the wrong family is the most common way to waste a week of GPU time; this exercise inoculates you.

**Estimated time:** 45 minutes. Guided. No code — paper and judgment.

---

## Setup

Write your answers in `notes/week-34/randomization-recipes.md`. You'll reference the two recipes from Lecture 2 §3 (manipulation vs. navigation) but you must *justify* each line, not copy it. For each parameter you randomize, state: the **family** (visual / dynamics / sensor / latency), the **nominal value** (a plausible center), a **range** (low–high), and a one-line **why** (what real-world variation it brackets).

---

## Part A — A grasp policy (manipulation)

A vision-conditioned policy that picks a cube off a table (your Week 25–31 task family). The camera is on the wrist; the policy reads the wrist image + proprioception and outputs an EE-delta.

Fill in a table like this — at least **six** parameters across **at least three** families:

| Parameter | Family | Nominal | Range | Why (what real variation it brackets) |
|---|---|---|---|---|
| object x,y position | dynamics(scene) | (0.4, 0.0) | ±0.05 m | the real cube is never exactly where sim placed it |
| object friction | dynamics | 0.8 | 0.5–1.1 | grasp stability varies with surface/wear |
| object mass | dynamics | 0.15 kg | 0.05–0.25 | real mass differs from CAD estimate |
| table/object texture | visual | wood | {wood, tile, ...} | the real object/table looks different (Tobin) |
| light intensity | visual | 800 | 400–1400 | real lighting is uncontrolled |
| camera yaw | visual | 0° | ±8° | real mounting is imperfect |
| wrist-cam noise | sensor | 0 | σ small | real images are noisy |

(Replace the example rows with your own values and reasoning; add latency if your controller is delay-sensitive.)

**Then answer:** which **family dominates** for *this* policy, and why? (Hint: it reads images — so the visual gap is a primary exposure — but a grasp also lives or dies on contact physics, so dynamics matters too. A pure state-based reach would shift the balance.)

---

## Part B — A navigation policy (navigation)

A policy that drives the robot to a goal while avoiding obstacles (your Nav-adjacent task family). It reads odometry + a LiDAR/scan and outputs `/cmd_vel`.

Fill in the same kind of table — at least **six** parameters across **at least three** families:

| Parameter | Family | Nominal | Range | Why |
|---|---|---|---|---|
| floor friction | dynamics | 0.8 | 0.4–1.2 | carpet vs tile vs polished concrete |
| obstacle layout/count | dynamics(scene) | fixed | randomized | the real clutter isn't your sim's |
| odometry/wheel-slip noise | sensor | 0 | small | real wheel odometry drifts (Week 6) |
| robot payload mass | dynamics | base | +0–3 kg | a loaded robot drives differently |
| lighting | visual | 800 | 400–1400 | for any vision input |
| control latency | latency | 0 ms | 0–50 ms | real actuator/comms delay affects stability |

**Then answer:** how does this recipe *differ* from Part A's, and what would happen if you applied the *grasp* recipe (heavy object-pose/object-friction randomization) to this *nav* policy? (It would waste capacity randomizing things the nav policy never touches while under-randomizing floor friction and odometry — the exposures that actually matter for driving.)

---

## Part C — The exposure argument

In two or three sentences, state the rule you used to build both recipes (the family-to-exposure rule from Lecture 1 §2.4) and explain why "randomize everything maximally" is *not* the answer (over-randomization, Lecture 2 §2.3 — too-wide ranges make the policy conservative and it solves nothing).

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `notes/week-34/randomization-recipes.md` has both tables (grasp and nav), each with ≥ 6 parameters spanning ≥ 3 families, with nominal, range, and a why per row.
- [ ] You named the dominant family for each task and justified it by what the policy's inputs/physics are exposed to.
- [ ] You explained, concretely, what goes wrong if you apply the grasp recipe to the nav policy (wrong exposures randomized).
- [ ] You stated the exposure rule and why maximal randomization is wrong (over-randomization).

---

## Stretch

- For one parameter in each recipe, argue whether you'd use a **uniform**, **normal**, or **log-uniform** distribution and why (friction → uniform around nominal; a multiplicative gain → log-uniform; sensor noise → normal). The distribution shape is part of the recipe, not just the range.
- Add a **"do NOT randomize"** list for each task: parameters that should stay fixed because randomizing them would change the *task itself* (e.g., the goal location for nav, the gripper width semantics for grasp). Knowing what *not* to randomize is as senior as knowing what to.

---

When both recipes feel justified, move to [Exercise 2 — Implement the config + sampler](exercise-02-domain-randomization-config.py).
