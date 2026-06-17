# Week 34 — Domain Randomization and Sim-to-Real Strategy

Welcome to the week that answers the question hanging over everything you've trained: **your policy works in sim — will it work on a real robot, and how would you even know?** By Friday you will be able to take the PPO policy from Week 28, train it over a *distribution* of randomized worlds instead of one fixed world, evaluate it on a held-out "real-style" world it never saw, and report — with a single number — how much of the sim-to-real gap your randomization closed.

You arrive here having spent last week proving that simulators differ — that the same robot behaves measurably differently under DART vs. Bullet vs. PhysX. That observation was not academic. It was the sim-to-real gap *in miniature*: if your policy is brittle to the difference between two simulators, it will shatter against the difference between any simulator and reality. This week is the strategy for surviving that gap, and it has a name that sounds like magic but is actually a curriculum: **domain randomization.**

The one sentence to carry through the week:

> **Sim-to-real transfer is not achieved by making one simulator perfectly realistic. It is achieved by training over a *distribution* of imperfect simulators so wide that the real world looks like just another sample from it.**

This is the Tobin et al. insight (the original 2017 domain-randomization paper) and the Sadeghi-Levine "CAD2RL" insight before it, and it remains the workhorse strategy in 2026: rather than chase fidelity — an expensive, never-finished arms race against reality — you **deliberately corrupt** the simulator along every axis the real world might differ (textures, lighting, camera pose, friction, mass, sensor noise, latency) and train a policy robust to *all* of them at once. A policy that has seen a thousand frictions cannot be surprised by the one real friction. A vision policy that has seen ten thousand random textures treats the real tabletop as texture number ten-thousand-and-one. The randomization *is* the robustness.

This week you do it for real: visual and dynamics randomization on the Week 28 PPO task, an honest held-out evaluation, and the gap-closure metric.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** why domain randomization works — the "reality as one more sample from a wide training distribution" argument — and trace it to its sources (Sadeghi & Levine CAD2RL, Tobin et al. 2017, the OpenAI Dactyl dynamics-randomization result).
- **Distinguish** the three families of randomization — **visual** (textures, lighting, colors, camera pose), **dynamics** (mass, friction, damping, motor gains, latency), and **sensor-noise** (Gaussian noise, dropout, bias, quantization) — and know which family matters for which task (visual for vision policies, dynamics for control policies).
- **Implement** a randomization configuration: a parameterized distribution over world parameters, sampled fresh per episode (or per parallel environment), wired into a Gz Sim or Isaac Lab training loop.
- **Apply** the canonical recipes — uniform-range randomization, the "randomize everything you're unsure about" default, and **structured/automatic domain randomization (ADR)** that widens ranges as the policy improves — and explain the over-randomization failure mode (a policy so conservative it solves nothing).
- **Author** a held-out "real-style" evaluation world with *mismatched* textures, lighting, and friction the policy never trained on — the proxy for reality on Path B.
- **Measure** the **gap-closure metric**: the difference in held-out success rate between a policy trained on one nominal world and a policy trained with randomization, and present it as the evidence sim-to-real worked.
- **Decide**, as a senior engineer, what to randomize and how wide, and own the honest limits — domain randomization narrows the gap, it does not erase it, and some gaps (a genuinely novel object, a contact regime never sampled) it cannot close.

## Prerequisites

This week assumes you have completed **C24 weeks 1–33**, including the Phase 4 learning weeks and last week's multi-sim comparison. Specifically:

- You have the **Week 28 PPO policy** — a reach (or navigate) task trained with parallel environments in Isaac Lab (Path A) or Gymnasium + Gz Sim (Path B), reaching ~90% success on the nominal world. *This week's lab augments that exact training run with randomization.* If it's gone, re-run Week 28's training first.
- You have **last week's `crunchbot_sim_compare` harness** (or the metric-capture skills from it). This week extends the same idea — hold the robot fixed, vary the world, measure — into a randomization-and-gap harness.
- You can train and evaluate an RL policy, read a reward curve in TensorBoard, and reason about success rate on a held-out set (Weeks 28, 31).
- You understand the **throughput vs. fidelity** trade-off from Week 33 — domain randomization *needs* throughput, because randomizing over a thousand worlds is only affordable when you can step many cheap worlds in parallel (the Isaac Lab story).
- For the parallel-randomization lab (Path A or GPU Path B): an **NVIDIA GPU** + Isaac Lab. **Path B without an NVIDIA GPU:** randomize across Gz Sim episodes (slower, fewer samples) and treat the parallel-env scale as read-and-reason — documented in the lab.

You do **not** need prior sim-to-real experience. Lecture 1 starts at "why fidelity-chasing fails" and builds the randomization recipe from first principles.

## Topics covered

- **The sim-to-real gap, named:** the visual gap (rendered ≠ real images), the dynamics gap (sim physics ≠ real physics), the sensor gap (clean sim sensors ≠ noisy real ones), and the latency gap (instant sim control ≠ real actuator/comms delay).
- **Why fidelity-chasing loses:** the diminishing-returns arms race against reality, and the randomization alternative — train over a distribution wide enough to contain reality.
- **The canonical patterns:** Sadeghi & Levine **CAD2RL** (visual randomization for flight), **Tobin et al. 2017** (the textbook texture/lighting/camera recipe), OpenAI **Dactyl** (dynamics randomization + ADR for in-hand manipulation), and where each applies.
- **Visual domain randomization:** randomizing textures, materials, colors, lighting (number, position, intensity, color), camera pose and intrinsics, distractor objects, and backgrounds — for any policy that consumes images.
- **Dynamics randomization:** randomizing mass, inertia, friction (static/dynamic), restitution, joint damping, motor gains/torque limits, and control/observation latency — for any policy that produces actions.
- **Sensor-noise injection:** Gaussian noise, bias, dropout, quantization, and delay on the observations a policy reads, so it doesn't overfit to clean sim sensors.
- **Randomization for manipulation vs. navigation:** what to randomize for a grasp (object pose, friction, mass, visual appearance) vs. a nav policy (floor friction, lighting, obstacle layout, odometry noise) — they are not the same recipe.
- **Automatic Domain Randomization (ADR):** widening ranges as the policy succeeds, the over- and under-randomization failure modes, and the curriculum framing ("a curriculum of distributions").
- **Honest sim-to-real evaluation:** the held-out "real-style" world, the gap-closure metric, and the limits — randomization narrows but does not erase the gap, and you must say so.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The sim-to-real gap; why fidelity-chasing fails; the recipes |   2h    |    1h     |     0h     |    0.5h   |   1h     |     0h       |    1h      |     5.5h    |
| Tuesday   | Visual + dynamics + sensor randomization; the config         |   2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Wednesday | ADR; over-randomization; manipulation vs navigation recipes |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | Augment the Week 28 PPO with randomization; train             |   1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Held-out eval; the gap-closure metric; the write-up          |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work (the randomization + gap harness)     |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, gap-closure write-up polish                    |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                             | **6h**   | **6.5h**  | **4h**     | **4h**    | **5h**   | **11h**      | **2.5h**   | **36.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The DR papers (Tobin, CAD2RL, Dactyl/ADR), Isaac Lab randomization docs, and the talks worth your time |
| [lecture-notes/01-the-sim-to-real-gap-and-why-randomization-works.md](./02-lecture-notes/01-the-sim-to-real-gap-and-why-randomization-works.md) | The gap, why fidelity-chasing fails, the canonical recipes, and the three randomization families |
| [lecture-notes/02-randomization-config-adr-and-honest-evaluation.md](./02-lecture-notes/02-randomization-config-adr-and-honest-evaluation.md) | Implementing the config, ADR, manipulation-vs-nav recipes, the held-out world, and the gap-closure metric |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-randomization-recipe.md](./03-exercises/exercise-01-randomization-recipe.md) | Decide what to randomize and how wide for two tasks (a grasp and a nav), and justify each choice |
| [exercises/exercise-02-domain-randomization-config.py](./03-exercises/exercise-02-domain-randomization-config.py) | Implement a parameterized randomization config that samples per-episode world parameters and validate it |
| [exercises/exercise-03-gap-metric.py](./03-exercises/exercise-03-gap-metric.py) | Compute the sim-to-real gap-closure metric from nominal-vs-randomized held-out evals |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-close-the-gap.md](./04-challenges/challenge-01-close-the-gap.md) | Augment the Week 28 PPO with randomization, eval on a held-out world, report the gap closed |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the headline gap-closure write-up |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunchbot_domain_rand` harness: a config-driven randomization layer + gap-closure evaluator |

## The "gap closed" promise

C24 uses a recurring marker for this week: **the gap-closure number.** Not "randomization helped" — a held-out success rate for the nominal policy, a held-out success rate for the randomized policy, and the difference, on a world *neither* trained on.

```
=== SIM-TO-REAL GAP: reach task, held-out "real-style" world (n=100) ===
policy trained on nominal world only     held-out success:  31/100  (31%)
policy trained with domain randomization held-out success:  84/100  (84%)
gap closed: +53 pts
(sanity) both policies on their TRAINING world:  nominal 92% | randomized 88%
```

That last sanity line matters: the randomized policy is often *slightly worse* on the easy nominal world (it spent capacity on robustness) and *dramatically better* on the held-out world. If your randomized policy is better on *both*, double-check your held-out world is actually held out. If you cannot produce this table, you have not finished the week.

## Stretch goals

If you finish the regular work early and want to push further:

- **Implement ADR.** Start ranges narrow and widen each parameter automatically as the policy clears a success threshold on the current range. Plot range-width vs. training step and watch the curriculum emerge. Compare final held-out success against fixed-range randomization.
- **Find the over-randomization cliff.** Deliberately widen friction/mass ranges until the policy *can't learn the task at all* (it goes maximally conservative and solves nothing). Locate the cliff; it's the practical upper bound the lecture warns about.
- **Ablate the families.** Train with visual-only, dynamics-only, and both, then eval each on the held-out world. Which family carries the gap closure for *your* task? (Usually visual for vision-based, dynamics for state-based — confirm it.)
- **Latency randomization.** Add a randomized control/observation delay (0–50 ms) to the training loop and show it makes the policy robust to the real-actuator latency that ambushes a lot of sim-trained controllers on first hardware contact.

## Up next

Week 35 begins the **multi-robot** sub-phase (shared mapping and coordination). You leave the single-robot sim-to-real story here with a policy that survives a distribution of worlds and an honest gap number — exactly the kind of artifact the Phase 5 milestone (Week 40) and the capstone safety case (Week 41) expect you to defend. Push your randomization harness before you move on; the gap-closure discipline you built this week is what makes any sim-trained capstone result credible.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
