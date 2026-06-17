# Week 44 — Capstone Build Sprint 3 + Language-Conditioned Task Tuning

Welcome to **C24 · Crunch Robotics**, Week 44. You are four weeks from the defense. The robot drives (week 42), it streams telemetry to an operator dashboard with a one-click teleop takeover (week 43), and it has a signed safety case (week 41). What it does *not* yet do reliably is the thing the whole capstone is named after: take a natural-language instruction — *"bring me the red cup from the left bench"* — and carry it out, again and again, across the variety of phrasings and scene layouts a real user will throw at it. This week is where that number goes up.

The capstone is graded at week 48 against a hard, written acceptance bar: **at least 15 of 20 instructions succeed** on a held-out evaluation suite. Right now you probably do not know your number, because you have never run a clean, repeatable, twenty-instruction evaluation. By Friday you will. You will curate the suite, freeze it, run your baseline VLA against it and record an honest per-instruction success table, fine-tune the policy on 50 capstone-specific demonstrations, re-run the *same frozen suite*, and produce a baseline-vs-fine-tuned diff that says, for every instruction, whether it got better, worse, or stayed the same — and why.

This is not a "train a bigger model" week. It is an **evaluation discipline** week that happens to involve fine-tuning. The senior move in policy work is not "I improved the loss." It is "I drove instruction 14 from 1/5 to 4/5, I know exactly why the remaining failure happens, and here is the next data change that would close it." We will spend as much care on the eval harness — deterministic seeds, fixed scene resets, an honest scoring rubric a stranger could replicate — as on the training loop. A policy improvement you cannot measure repeatably did not happen.

The first thing to internalize is that **the eval suite is a contract you write down before you touch the training code, and you do not edit it afterward.** The moment you tune the suite to flatter the model — drop the instruction it always fails, reword the one it finds confusing — your number stops meaning anything. We freeze the twenty instructions, the twenty scene resets, and the scoring rubric into a versioned YAML file under Git, and every run cites the commit hash of that file. If you change the suite, the old numbers are void and you say so.

The second thing to internalize is that **fifty good demonstrations beat five hundred sloppy ones.** Your fine-tuning budget this week is fifty capstone-specific demos — teleoperated or scripted-and-verified trajectories on *your* robot, in *your* scene, for the *families of instructions in your suite*. The OpenVLA / RT-2-class base model already knows how to grasp a cup; what it does not know is your bench heights, your camera extrinsics, your gripper's quirks, and the specific noun phrases your eval uses. Fine-tuning is teaching it those, cheaply, with LoRA adapters so a single Orin or a single workstation GPU can do the job in an afternoon.

## Learning objectives

By the end of this week, you will be able to:

- **Curate** a frozen twenty-instruction evaluation suite for your capstone — instructions, scene resets, success rubric — versioned in Git and replicable by a stranger.
- **Stratify** the suite across the axes that actually break VLA policies: object reference, spatial grounding, distractor density, instruction phrasing, and recovery, so a score reveals *where* you fail, not just *that* you fail.
- **Run** a baseline VLA against the full suite with deterministic seeds and fixed resets, recording per-instruction success out of N trials in a machine-readable report.
- **Distinguish** the four failure modes that dominate language-conditioned manipulation — grounding, grasp, placement, and language-binding errors — and tag every failed trial with one.
- **Collect** fifty capstone-specific demonstrations via teleop or verified scripting, in the LeRobot/RLDS episode format the trainer expects, with the same observation and action spaces as deployment.
- **Fine-tune** an OpenVLA-class policy with LoRA on those demos, tracking train and held-out metrics, and checkpoint-select on the eval suite rather than on training loss.
- **Re-run** the frozen suite on the fine-tuned checkpoint and produce a baseline-vs-fine-tuned per-instruction diff with a regression call-out for any instruction that got worse.
- **Diagnose** every still-failing instruction to a specific failure mode and write the next concrete data or scaffolding change that would fix it.
- **Defend** an honest number: report the success rate with its trial count and confidence interval, never a single lucky run.

## Prerequisites

- **Weeks 31–34 of C24 complete:** learned policies (BC, DAgger, Diffusion Policy, ACT) and the VLA weeks. You have an OpenVLA-class policy already wrapped behind a `rclpy` action server and emitting end-effector deltas your controller consumes. This week tunes it; it does not introduce it.
- **Week 42 and 43 complete:** the robot (or the hardened sim) executes a full perception → planner → controller → policy task and streams telemetry. The eval harness this week drives that same stack.
- **A working `ros2 jazzy` workspace on Ubuntu 24.04**, with `rclpy`, `BehaviorTree.CPP` v4, PyTorch 2.x with CUDA, OpenCV, Open3D, and GTSAM already building. We do not re-install the stack this week.
- **A GPU you can fine-tune on.** A Jetson Orin (Path A) does LoRA fine-tuning of a 7B VLA overnight; a workstation RTX 4090 / 5090 or an A100 does it in an hour or two. Either is fine. Pure-CPU fine-tuning of a 7B model is not realistic — borrow a GPU box for one afternoon if you must.
- **Teleop working.** You will collect demos by driving the robot (Path A) or by scripting-and-verifying trajectories in sim (Path B). The week-43 teleop-takeover plumbing is the data-collection path; reuse it.

You do **not** need to invent a new policy architecture. You need to measure the one you have, improve it with a small, honest amount of data, and measure it again.

## Topics covered

- **The twenty-instruction evaluation suite as a contract.** Why you freeze it before training, version it in Git, and cite its commit hash on every run. The difference between a *dev* suite (you may iterate on) and a *frozen acceptance* suite (you may not).
- **Stratifying instructions across failure axes.** Object reference ("the red cup" vs "the cup" vs "the leftmost cup"), spatial grounding ("on the left bench", "behind the box"), distractor density (one cup vs five cups of different colors), phrasing variation (imperative, polite, terse), and recovery (object not where expected). A suite that is all easy instructions hides your real number.
- **Scene resets and determinism.** Fixed object spawn poses per instruction, seeded RNG, a documented reset procedure (sim: a world-reset service; real: a taped floor template and a photo). Why a non-deterministic suite produces un-citable numbers.
- **The success rubric.** Binary success per trial, defined operationally ("the named object ends within 5 cm of the named destination, no collision, within 90 s"), N trials per instruction (we use 5), success counted out of N. Partial credit is a trap; we score binary and report the count.
- **Running the baseline.** A `rclpy` eval-runner node that loads the suite, resets the scene, issues each instruction to the policy action server, scores the outcome from the state estimate, and writes a per-instruction JSON/CSV report plus a Markdown table.
- **The four failure modes.** *Grounding* (the policy attended to the wrong object), *grasp* (right object, failed pick), *placement* (right pick, wrong place), *language-binding* (it ignored or misread the instruction and did a generic behavior). Tagging every failure unlocks the right fix.
- **Capstone-specific demonstrations.** Why fifty in-domain demos beat the base model's generic priors for *your* scene. The observation/action space must match deployment exactly — same cameras, same proprioception, same action representation (here: 7-DoF end-effector delta + gripper).
- **The episode format.** LeRobot `v2` dataset / RLDS-style episodes: per-step observation dict, action vector, language instruction string, success flag. How to record them from a live `rclpy` session into a parquet-backed dataset.
- **LoRA fine-tuning of an OpenVLA-class policy.** Why LoRA (a few hundred MB of adapter weights, not 14 GB of full weights), the rank/alpha/target-module choices, the learning-rate and step-count that work for ~50 demos, and how to merge or hot-load the adapter into the action server.
- **Checkpoint selection on the eval suite, not the loss.** Why training loss lies about manipulation success, and why you evaluate candidate checkpoints on a held-out *dev* slice (never the frozen acceptance suite) to pick which one to ship.
- **Honest improvement tracking.** Reporting `k/N` with a Wilson confidence interval, calling out regressions explicitly, and never quoting a single best-of-three run. The baseline-vs-fine-tuned diff table is the week's headline artifact.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract. Reserve your GPU time early — the fine-tune run is the long pole, and you do not want it queued on Saturday night.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Eval-suite curation; the failure-axis stratification        |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Scene resets, determinism, the success rubric; baseline run |    1.5h  |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Wednesday | Demo collection; the episode format; the four failure modes |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | LoRA fine-tuning; checkpoint selection; re-run the suite     |    1h    |    1h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Baseline-vs-fine-tuned diff; failure diagnosis; mini-project |    0.5h  |    0h     |     1h     |    0.5h   |   1h     |     2.5h     |    0.5h    |     6h      |
| Saturday  | Mini-project deep work — drive the per-instruction number up |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, write the report                              |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0.5h    |     2.5h    |
| **Total** |                                                             | **6h**   | **6.5h**  | **3h**     | **3.5h**  | **5h**   | **8.5h**     | **3h**     | **35.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | OpenVLA / LeRobot / RLDS docs, LoRA and eval-methodology references, and the 2026 robot-learning eval papers worth reading |
| [lecture-notes/01-curating-the-twenty-instruction-eval-suite.md](./02-lecture-notes/01-curating-the-twenty-instruction-eval-suite.md) | The eval suite as a frozen contract: stratification across failure axes, scene resets, determinism, the binary success rubric, and the `rclpy` eval-runner |
| [lecture-notes/02-fine-tuning-the-vla-on-capstone-demos.md](./02-lecture-notes/02-fine-tuning-the-vla-on-capstone-demos.md) | Collecting fifty in-domain demos, the episode format, LoRA fine-tuning of an OpenVLA-class policy, checkpoint selection on eval not loss, and honest improvement tracking |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-curate-the-eval-suite.md](./03-exercises/exercise-01-curate-the-eval-suite.md) | Author and freeze the twenty-instruction suite YAML, with scene resets and rubric |
| [exercises/exercise-02-run-baseline-suite.py](./03-exercises/exercise-02-run-baseline-suite.py) | A runnable `rclpy` eval-runner that drives the baseline policy across the full suite and writes a per-instruction report |
| [exercises/exercise-03-finetune-and-rerun.py](./03-exercises/exercise-03-finetune-and-rerun.py) | A runnable LoRA fine-tune script over fifty demos plus a re-run-and-diff harness |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-drive-to-fifteen-of-twenty.md](./04-challenges/challenge-01-drive-to-fifteen-of-twenty.md) | Drive per-instruction success to ≥ 15/20 and document the failure mode + next fix for every remaining failure |
| [quiz.md](./05-quiz.md) | 13 questions on eval methodology, failure modes, and fine-tuning, with an answer key |
| [homework.md](./06-homework.md) | Concrete homework with deliverables and a grading rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the tuned capstone VLA policy + frozen suite + baseline-vs-fine-tuned report |

## The "honest number" promise

C24 has a recurring marker in every week that produces a measured result. This week it is the **honest number**:

```
instruction-14  "put the blue block on the right shelf"   baseline 1/5  ->  fine-tuned 4/5   (grounding fix)
SUITE TOTAL                                                baseline 9/20 ->  fine-tuned 16/20  (Wilson 95% CI on mean: [0.59, 0.91])
```

If your report quotes a single run instead of `k/N`, or hides a regression, or cites a suite you edited after training, it is not an honest number and it will not survive the week-48 panel. The phrase "it works now" never appears in a senior engineer's eval report; the phrase "16 of 20, up from 9, with these three instructions still failing for these three reasons" does.

## A note on what's not here

This week is narrow on purpose. It does **not** introduce:

- **A new policy architecture.** We tune the OpenVLA-class policy you already have from the VLA weeks. Diffusion Policy / ACT swaps are out of scope; if your base policy is one of those, the eval discipline is identical and the fine-tune loop is the analogous LoRA/adapter recipe for that architecture.
- **RLHF or online RL.** Fifty offline demos and LoRA. Online policy improvement is a different, riskier loop we deliberately keep out of the capstone.
- **Full-parameter fine-tuning.** LoRA only. Full fine-tunes of a 7B VLA need multi-GPU and produce 14 GB checkpoints that do not fit your deployment story.
- **Sim-to-real transfer.** That was week 35–36. This week, you collect demos and evaluate in the *same* domain you deploy in (real for Path A, hardened sim for Path B). No domain gap to cross here.
- **Reward modeling or LLM-as-judge scoring.** Success is scored geometrically from the state estimate against an operational rubric, not by a model. A model judge is a week-46 chaos-drill stretch idea, not an acceptance-grade scorer.

## Up next

Continue to **Week 45 — Capstone build sprint 4 + interview-prep ramp** once your tuned policy, frozen suite, and baseline-vs-fine-tuned report are pushed. Week 45 starts the interview ramp; the per-instruction report you build this week is *exactly* the kind of artifact a robotics-startup interviewer wants you to walk them through. "Here is how I measured my policy, here is what I fixed, here is what I'd fix next" is a senior answer, and this week is where you earn the right to give it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
