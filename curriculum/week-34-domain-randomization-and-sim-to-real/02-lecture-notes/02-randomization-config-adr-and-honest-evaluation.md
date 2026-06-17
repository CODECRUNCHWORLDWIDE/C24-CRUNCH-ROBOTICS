# Lecture 2 — Randomization Config, ADR, and Honest Sim-to-Real Evaluation

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can implement a parameterized randomization config sampled per-episode/per-env, wire it into the Week 28 training loop, apply ADR as a curriculum, pick the right recipe for manipulation vs. navigation, author a held-out "real-style" world, and compute the gap-closure metric.

Lecture 1 gave you the *why* and the recipes. This lecture is the engineering: turning "randomize the friction" into a config, a sampler, a training loop, and — the part you'll be graded on — an honest evaluation that produces a defensible gap-closure number. Four parts: (1) the config and sampler, (2) wiring it into training + ADR, (3) manipulation vs. navigation recipes, (4) honest evaluation.

---

## Part 1 — The randomization config: a distribution over world parameters

### 1.1 The structure

A randomization config is, at heart, **a named set of parameters, each with a sampling distribution.** Per episode (Gz Sim, Path B) or per parallel environment on reset (Isaac Lab, Path A), you draw one sample from each distribution and apply it to the world before the policy acts. The clean way to express it is data, not code:

```yaml
# randomization.yaml — a distribution over world parameters, sampled per episode.
visual:
  table_texture:   {dist: choice, options: [wood, metal, tile, marble, noise]}
  light_intensity: {dist: uniform, low: 300.0, high: 1200.0}
  light_position:  {dist: uniform, low: [-2, -2, 2], high: [2, 2, 4]}
  camera_yaw_deg:  {dist: uniform, low: -10.0, high: 10.0}
dynamics:
  floor_friction:  {dist: uniform, low: 0.4, high: 1.2}     # nominal ~0.8
  object_mass_kg:  {dist: uniform, low: 0.05, high: 0.25}   # nominal ~0.15
  joint_damping:   {dist: log_uniform, low: 0.01, high: 0.5}
  motor_gain:      {dist: uniform, low: 0.8, high: 1.2}     # +/-20% of nominal
sensor:
  imu_gyro_noise:  {dist: normal, mean: 0.0, std: 0.01}
  scan_dropout_p:  {dist: uniform, low: 0.0, high: 0.05}
latency:
  action_delay_ms: {dist: uniform, low: 0.0, high: 50.0}
```

Two design rules that separate a good config from a fragile one:

- **Center on a realistic nominal, then spread to bracket reality.** `floor_friction` nominal is ~0.8 (your sim's value, ideally measured via light system ID); the range `[0.4, 1.2]` *brackets* it generously. The goal is for the real friction to fall *inside* the sampled range — Lecture 1's "can't close a gap you never sampled."
- **Sample fresh, independently, per episode/env.** Each episode rolls a new world. If you fix the world for a whole training run and only vary across runs, you have *domains*, not *randomization* — the policy still overfits within the run.

### 1.2 The sampler

The sampler is small and seedable (reproducibility matters — you must be able to re-run a randomized training):

```python
import numpy as np

class DomainRandomizer:
    """Samples a fresh set of world parameters from the config, per episode/env."""

    def __init__(self, config: dict, seed: int = 0) -> None:
        self.config = config
        self.rng = np.random.default_rng(seed)

    def sample(self) -> dict:
        """One draw: returns concrete world parameters to apply this episode."""
        params = {}
        for family, entries in self.config.items():
            for name, spec in entries.items():
                params[f"{family}.{name}"] = self._draw(spec)
        return params

    def _draw(self, spec: dict):
        dist = spec["dist"]
        if dist == "uniform":
            return self.rng.uniform(spec["low"], spec["high"])
        if dist == "normal":
            return self.rng.normal(spec["mean"], spec["std"])
        if dist == "log_uniform":
            lo, hi = np.log(spec["low"]), np.log(spec["high"])
            return float(np.exp(self.rng.uniform(lo, hi)))
        if dist == "choice":
            return self.rng.choice(spec["options"])
        raise ValueError(f"unknown dist {dist!r}")
```

Exercise 2 makes you implement and validate exactly this — including the check that every sample stays inside its declared range (a randomizer that occasionally emits out-of-range values is the silent bug that poisons a training run).

Two properties the sampler must have, both tested in Exercise 2: **reproducibility** (same seed → same sequence of worlds, so you can re-run a training exactly) and **coverage** (over many draws, the samples actually span the declared range — a sampler stuck near the nominal isn't randomizing anything). A sampler that passes both, plus the in-range check, is the trustworthy foundation everything else builds on; a sampler that quietly clips, repeats, or fails to cover is a bug that silently weakens every downstream result.

### 1.3 Applying the sample to the world

*Where* the sampled parameters get applied is simulator-specific:

- **Isaac Lab (Path A):** the **event manager**. You register randomization *terms* — `randomize_rigid_body_mass`, `randomize_physics_material`, `randomize_visual_material`, a lighting/camera term — each running on the `reset` event, applied per parallel environment as a batched tensor operation. This is what makes randomizing thousands of envs cheap (Week 33's throughput payoff).
- **Gz Sim (Path B):** at episode reset in your Gymnasium `reset()`, you set the sampled friction/mass via the model's SDF parameters (or `gz` service calls), swap the texture/material, and reposition lights/camera before the episode runs. Slower (no parallel envs), fewer samples, but the *concept* is identical.

The policy code never changes — it just acts in whatever world the randomizer produced. That separation (sampler ⟂ policy ⟂ simulator) is what makes the config reusable and the harness portable.

In Isaac Lab, the event-manager registration looks roughly like this (the mini-project's `apply.py` wraps it):

```python
# An Isaac Lab env config registers randomization "events" that fire on reset.
@configclass
class EventCfg:
    # randomize each env's object friction on reset, drawn from a range
    object_friction = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="reset",
        params={"static_friction_range": (0.4, 1.2),
                "dynamic_friction_range": (0.4, 1.2),
                "num_buckets": 64},
    )
    # randomize object mass on reset
    object_mass = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="reset",
        params={"mass_distribution_params": (0.05, 0.25),
                "operation": "abs"},
    )
    # ... visual, lighting, observation-noise terms similarly ...
```

The key idea: each `EventTerm` with `mode="reset"` runs every time an environment resets, and because there are thousands of environments resetting continuously, the randomization is applied *constantly and in parallel* — the GPU draws thousands of different worlds per training batch. On Path B (Gz Sim), the same logic lives in your Gymnasium `reset()`: sample, apply, run the episode, repeat — just one world at a time. The *abstraction* is identical (sample on reset, apply to world); only the parallelism differs. That's why the mini-project's sampler is sim-independent and only the thin `apply()` adapter knows which simulator it's talking to.

---

## Part 2 — Wiring randomization into training, and ADR

### 2.1 Augmenting the Week 28 PPO

Your Week 28 PPO trained on one nominal world. Augmenting it is one change: **call `randomizer.sample()` and apply it on every environment reset.** With parallel envs (Isaac Lab), each of the N envs resets with its own sample, so a single training batch already spans N different worlds. The training loop, the PPO hyperparameters, the reward — all unchanged. You are not training a different algorithm; you are training the same algorithm on a *wider* environment.

This is worth emphasizing because it's reassuring: **domain randomization does not require a new training algorithm.** Your PPO, your reward, your network — all stay the same. The *only* change is that the environment the policy trains in now varies per episode. That minimalism is a feature: it means you can add DR to any sim-trained policy you already have, and it means a DR result is directly comparable to its nominal baseline (only the world distribution differed). The whole technique is "same training, wider environment."

Expect the reward curve to look different: **noisier and slower to rise** than nominal training, because the task is genuinely harder (the policy must succeed across all sampled worlds, not one). A randomized run that converges as fast and as high as nominal usually means your ranges are too narrow to matter. Slower-but-broader is the signal that randomization is doing work.

### 2.2 Fixed-range vs. Automatic Domain Randomization (ADR)

The simplest approach is **fixed-range**: set the ranges in the config by hand and train. It works and it's where you start. Its weakness: pick the ranges too wide and the policy can't learn (over-randomization); too narrow and the gap doesn't close. You're guessing the right width.

**ADR (Dactyl)** removes the guess by making the ranges a **curriculum**:

1. Start every range **narrow** (near the nominal — an easy world).
2. Train. When the policy clears a success threshold on the current ranges, **widen** the ranges a step.
3. Repeat. The ranges grow only as fast as the policy can handle, so the policy is always trained at the edge of its competence — never overwhelmed, never coasting.

```
range width
   ^
   |                         ________ widen when policy clears threshold
   |                ________/
   |       ________/
   |______/
   +-------------------------------------> training step
   (narrow/easy early; wide/hard once competent — a curriculum of distributions)
```

This is the syllabus's "curriculum of distributions" made literal. ADR's payoff: it finds wide ranges *the policy can actually handle*, automatically, instead of you binary-searching the over-randomization cliff by hand.

### 2.3 The over-randomization failure mode

Widen ranges too far (by hand or by ADR's ceiling) and you hit the **over-randomization cliff**: the worlds become so varied that no single policy can succeed across all of them, so the policy learns the only thing that doesn't get punished everywhere — **maximal conservatism.** It barely moves, refuses risk, and solves nothing. The reward flatlines low. The fix is to *narrow* the ranges (or let ADR back off): you want the widest distribution the policy can *still solve*, not the widest distribution period. The stretch goal has you deliberately find this cliff so you recognize it in the wild — a flatlined reward under very wide ranges is over-randomization, not a broken trainer.

How do you *recognize* over-randomization versus a genuinely broken setup? The signatures differ:

- **Over-randomization:** the reward rises a little then flatlines *low*; the policy does something trivially safe (barely moves); narrowing the ranges immediately recovers learning. The trainer is fine; the task distribution is too hard.
- **A broken reward:** the reward is flat or chaotic from the start regardless of range width; even the *nominal* (un-randomized) run doesn't learn. The problem is upstream of randomization.
- **Too-narrow randomization:** the reward rises to nominal levels and the curve looks *identical* to nominal training; the policy learns fine but the held-out gap doesn't close. The ranges aren't doing anything.

Three different curves, three different fixes. Reading the reward curve under randomization — and knowing which of these three it is — is a core skill of the week, and it's why Problem 2 of the homework asks you to capture and interpret it rather than just run training.

### 2.4 Practical knobs for getting randomized training to converge

A few field-tested tips for when randomized training is fighting you:

- **Start narrower than you think, widen gradually** (manual ADR). Jumping straight to wide ranges often hits the cliff; ramping in lets the policy build competence first.
- **Randomize the high-impact families first.** For a control policy, friction and mass move the needle most; add the long tail (restitution, fine damping) only if the gap persists.
- **Watch the *spread* of returns across the batch**, not just the mean. With parallel envs, a healthy randomized run shows *variance* across envs (some worlds are harder) but a rising *floor*. If the floor never rises, the hard worlds are too hard — narrow them.
- **Don't randomize the reward or the goal.** Randomize the *world*, never the *objective*. A randomized goal changes the task; a randomized world changes the conditions. Mixing them up is a classic bug that looks like over-randomization but is actually a moving target.

---

## Part 3 — Manipulation vs. navigation: different recipes

The randomization recipe is **task-dependent**, and conflating the two is a common mistake. Lecture 1 §2.4 gave the families; here is the concrete per-task checklist.

### 3.1 Manipulation (a grasp/pick policy)

What the gap is exposed to: the object's appearance, pose, and physics, and the gripper's contact.

| Randomize | Why |
|---|---|
| **Object pose** (position, orientation) | The real object is never exactly where sim placed it. |
| **Object friction & mass** | Grasp stability depends on both; real values vary per object/wear. |
| **Object visual appearance** (texture, color) | If vision-conditioned, the real object looks different. |
| **Gripper friction / contact** | The real gripper grips differently than the sim's idealized contact. |
| **Lighting & camera pose** | For any vision-based grasp (the Tobin checklist). |
| **Sensor noise** on the wrist camera / proprioception | Real observations are noisy. |

### 3.2 Navigation (a drive/avoid policy)

What the gap is exposed to: the floor, the obstacle layout, the lighting, and the odometry.

| Randomize | Why |
|---|---|
| **Floor friction** | Real floors vary (carpet vs. tile vs. polished concrete). |
| **Obstacle layout & count** | The real environment's clutter is not your sim's. |
| **Lighting** | For any vision-based nav (and for perception inputs). |
| **Odometry / wheel-slip noise** | Real wheel odometry drifts (Week 6's lesson) — randomize the drift. |
| **Robot mass / payload** | A loaded robot drives differently. |
| **Latency** | Control delay affects stability at speed. |

The takeaway: **don't randomize a manipulation recipe on a nav task or vice-versa.** Randomize what *that policy's* inputs and physics are exposed to. Exercise 1 makes you build both recipes and justify each line.

### 3.3 What to *not* randomize (the under-taught half)

Knowing what to hold fixed is as senior as knowing what to vary. Some things must *not* be randomized because randomizing them changes the *task itself* rather than the *conditions*:

- **The goal/objective.** Randomizing where "the goal" is for a nav policy doesn't build robustness — it makes the task ambiguous. The goal is part of the *task definition*, not the world's variation. (You *can* randomize the *start* position; that's a condition. You don't randomize the *goal* relative to the instruction.)
- **The success criterion.** If "success" means different things across episodes, the reward signal is incoherent and nothing learns.
- **The robot's own kinematics in ways that break the task.** Randomizing wheel radius slightly (calibration error) is dynamics DR; randomizing it to 3× is changing the robot into a different robot.
- **Semantics the instruction depends on.** For a language-conditioned task, "the red cup" must stay red; randomizing the target object's identity breaks the grounding the instruction relies on.

The rule: **randomize the *conditions* the policy operates under, never the *task* it's trying to do.** Conditions are friction, lighting, noise, layout — things that vary in reality while the task stays the same. The task — the goal, the objective, the semantics — is fixed. Confusing the two produces a policy trained on a moving target, which looks like over-randomization but is a deeper design error. Exercise 1's stretch asks you to write this "do NOT randomize" list for both tasks precisely because it's the half people forget.

### 3.4 The two recipes, why they differ

It's worth naming *why* the manipulation and navigation recipes diverge, beyond "different exposures." A grasp policy lives or dies on *contact* (the object's friction, mass, the gripper's grip) and on *seeing the object* (visual). A nav policy lives or dies on *the floor* (friction, slip) and on *not hitting things* (obstacle layout, odometry drift). They share lighting (if vision-based) and latency, but the *load-bearing* families differ: dynamics-of-contact for grasping, dynamics-of-driving plus odometry-noise for navigation. Applying the grasp recipe to nav would lavish randomization on object friction (irrelevant — the nav robot grasps nothing) while under-randomizing floor friction and wheel slip (the things that actually matter for driving). Matching the recipe to the task's *load-bearing physics* is the whole point of building two recipes in Exercise 1 rather than one generic one.

---

## Part 4 — Honest sim-to-real evaluation

This is the graded part, and the artifact the Phase 5 milestone expects. Randomization without an honest gap measurement is faith, not engineering. The honest-evaluation discipline rests on three pillars, each of which a reviewer will check:

- **A held-out world** the policy never trained on (Part 4.1) — without it, you're measuring memorization.
- **A defensible denominator** (a fixed, adequate `n` with confidence intervals) — without it, your number is a coincidence.
- **A sanity line** (both policies on the nominal world) — without it, you can't tell a real gain from a leaky eval.

Skip any one and the result is not trustworthy. The rest of this part builds all three.

### 4.1 The held-out "real-style" world

On Path B (and as the in-sim proxy on Path A), you cannot evaluate on a real robot, so you build the next best thing: a **held-out world with parameters the policy never trained on**, deliberately *mismatched* to stress transfer:

- **Textures and colors** not in the training texture set.
- **Lighting** at an intensity/position/color outside the training range.
- **Floor/object friction** set to a specific value (ideally one you'd expect in reality), *distinct* from any single training value.
- **Sensor noise** at a realistic level.

The rule: **the held-out world's parameters must not be a sample the policy could have trained on.** If you reuse a training texture or a training friction, your "held-out" eval is contaminated and the gap number is a lie. This is the same train/eval-leakage discipline as Week 31's VLA eval, applied to worlds instead of demos.

### 4.2 The gap-closure metric

Train **two** policies on the *same* task with the *same* PPO setup, differing only in randomization:

- **Nominal policy** — trained on one fixed nominal world (your Week 28 baseline).
- **Randomized policy** — trained with the domain-randomization config.

Evaluate *both* on the *same* held-out world, with a fixed `n` (e.g., 100 trials). The **gap-closure metric** is the difference:

```
gap_closed = success_rate(randomized, held_out) − success_rate(nominal, held_out)
```

Report it with the sanity line from the README:

```
=== SIM-TO-REAL GAP: reach task, held-out "real-style" world (n=100) ===
nominal-trained      held-out success:  31/100  (31%)
randomized-trained   held-out success:  84/100  (84%)
gap closed: +53 pts
(sanity) on the TRAINING/nominal world:  nominal 92% | randomized 88%
```

Two checks make this honest:

1. **The sanity line.** The randomized policy is usually *slightly worse* on the easy nominal world (it spent capacity on robustness — Lecture 1's trade) and *much better* on the held-out world. If the randomized policy is better on **both**, your held-out world isn't actually held out, or your nominal training underfit — investigate before you believe the number.
2. **The denominator.** `n=100` on a held-out world is a defensible measurement; `n=5` is a coincidence. A reviewer attacks the denominator first (the Week 31 lesson, again).

### 4.2.1 Reading a gap-closure result, line by line

Take the example table above and interpret it the way a reviewer will:

- **nominal-trained held-out 31%.** This is the *naive transfer* number — train on one world, deploy on a different one. The 31% (down from 92% nominal) *is* the sim-to-real gap, quantified. Without randomization, this is what you'd ship, and it's a failure.
- **randomized-trained held-out 84%.** The randomized policy, on the *same* unseen world, succeeds 84% of the time. It never saw this world either — but it saw a *distribution* that brackets it, so it generalizes.
- **gap closed +53 pts.** Randomization recovered 53 of the 61 lost points. Not all of them (84% < 92%) — randomization narrows, doesn't erase — but most. That single number is the evidence the technique worked.
- **sanity: nominal 92% vs randomized 88% on the training world.** The randomized policy is *slightly worse* on the easy nominal world. This is the *expected, healthy* pattern: it traded a little peak nominal performance for a lot of robustness. If this line showed randomized *beating* nominal on the easy world, you'd suspect a leaky held-out set.

A reviewer reads exactly these four things, in this order, and the most common failure they catch is a missing or wrong sanity line. Lead with the gap, but *always* show the sanity line — it's what proves the gap is real and not an artifact.

### 4.2.2 Statistical honesty: confidence intervals on the gap

A +53-point gap between two `n=100` evals is almost certainly real (the confidence intervals barely touch). But a +10-point gap between two `n=20` evals might be noise — the intervals would overlap heavily. Always pair the gap with a sense of its uncertainty: report each rate with a binomial (Wilson) confidence interval, and treat the gap as significant only if the intervals don't substantially overlap. The Exercise-3 gap-metric script computes these intervals for you, precisely so your conclusion ("randomization helped") rests on a gap that's larger than the noise, not on a lucky run. A small-`n` gap with overlapping intervals is "promising, needs more trials," not "it works."

### 4.3 The limits, restated for the writeup

Your gap-closure writeup must include the honesty section from Lecture 1 §2.5: randomization narrows the gap, the held-out world is a *proxy* for reality (not reality), you can only close gaps you sampled, and a transferred policy still needs the Week 32 safety wrapper. A gap-closure result that claims "sim-to-real solved" is wrong on its face; one that says "randomization closed 53 points of the held-out gap; here's what it can't address and why the safety filter still matters" is the senior artifact.

### 4.4 Family ablation: attributing the gap closure

A gap-closure number tells you randomization helped; an *ablation* tells you *which family* helped, which is far more actionable. The method: train with visual-only DR, dynamics-only DR, and both; evaluate each on the held-out world. The per-family deltas attribute the closure:

```
ablation on held-out (n=100):
nominal (no DR)        : 31%
visual DR only         : 68%   (+37)
dynamics DR only       : 44%   (+13)
visual + dynamics DR   : 84%   (+53)
```

This (illustrative) result says **visual DR carried most of the gap** for this vision-based task — which makes sense, and tells you where to invest next (more visual variety) and what you could cheaply drop (heavy dynamics DR added only 13 points). Ablation turns "randomization closed 53 points" into "*visual* randomization closed 37 of the 53; here's my evidence and my next move." That specificity is what separates a result from a number, and it's the challenge's stretch goal precisely because it's the senior version of the analysis.

---

## 5. Recap

You should now be able to:

- Express a randomization config as a named distribution over world parameters and implement a seedable sampler that draws one fresh world per episode/env.
- Wire randomization into the Week 28 PPO via the Isaac Lab event manager (Path A) or Gymnasium reset (Path B), and recognize the noisier/slower reward curve as a sign it's working.
- Apply ADR as a curriculum that widens ranges with competence, and recognize the over-randomization cliff (a flatlined low reward under very wide ranges).
- Build the correct randomization recipe for manipulation vs. navigation — randomize what *that* policy is exposed to.
- Author a held-out "real-style" world with un-trained parameters and compute the gap-closure metric with a sanity line and a defensible denominator.
- Distinguish over-randomization, a broken reward, and too-narrow randomization by their reward-curve signatures.
- Distinguish *conditions* (randomize) from *task* (hold fixed), and write the "do NOT randomize" list.
- Read a gap-closure table line by line, pair each rate with a confidence interval, and judge whether a gap is real or noise.
- Run a family ablation to attribute the gap closure ("visual DR carried 37 of 53 points").
- State the honest limits: randomization narrows, doesn't erase, the gap; the held-out world is a proxy; the safety case still applies.

The synthesis of both lectures: domain randomization is an eight-step discipline — enumerate exposures, map to families, center and widen ranges, sample per-episode, train, hold out an eval world, measure the gap, diagnose and iterate. The architecture (a config, a sampler, an event-manager hook) is simple; the *discipline* (honoring the conditions-vs-task distinction, holding out the eval world, reading the curve, attributing the closure) is the job. A gap-closure number with a sanity line and a confidence interval is the artifact that makes any sim-trained policy credible — to the Phase 5 milestone, to the capstone safety reviewer, and to a future employer who asks "you trained this in sim; why should I believe it?".

Next: the exercises build the recipes, the config, and the gap metric on your own task. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *Domain Randomization (the recipe)* — Tobin et al., 2017: <https://arxiv.org/abs/1703.06907>
- *Dexterous In-Hand Manipulation / ADR* — OpenAI, 2018: <https://arxiv.org/abs/1808.00177>
- *Solving Rubik's Cube (ADR curriculum)* — OpenAI, 2019: <https://arxiv.org/abs/1910.07113>
- *Isaac Lab randomization (event manager)*: <https://isaac-sim.github.io/IsaacLab/>
- *Sim-to-Real Survey (what DR can/can't close)* — Zhao et al., 2020: <https://arxiv.org/abs/2009.13303>
