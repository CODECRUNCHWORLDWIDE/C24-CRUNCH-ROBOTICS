# Challenge 1 — The Latency Shootout

**Time estimate:** ~90 minutes.

## Problem statement

You have two action-chunking imitation policies trained on the *same* demonstrations: your **Diffusion Policy** (Week 29) and your **ACT** (this week, mini-project). A robotics startup has to pick one to ship on a Jetson Orin running a 30 Hz control loop. You are the engineer who decides — and you must defend the decision with a *fair* benchmark and a five-axis comparison table, not "ACT is faster, everyone knows that."

This challenge is half about ACT and Diffusion Policy and half about **benchmarking integrity**. The single most common way this comparison goes wrong is an unfair measurement: a cold cache, a missing GPU sync, the wrong batch size, mismatched precision. Each of those can swing the number by an order of magnitude and reverse the conclusion. You'll do it right.

## Your task

### Part 1 — Profile both policies fairly

Benchmark inference latency for ACT (single forward pass) and Diffusion Policy ($N$-step DDIM) on the *same* device, following the five rules from Lecture 2 §2.1:

1. **Warm up** — discard the first ~20 passes (kernel compilation, autotuning).
2. **Synchronize** — `torch.cuda.synchronize()` before reading the clock (CUDA is async).
3. **Batch of one** — deployment runs one observation at a time.
4. **Deploy precision** — benchmark the precision you'd ship (FP16 if that's the plan).
5. **Distribution, not a point** — 100+ timed runs; report **median and p99**.

For Diffusion Policy, the inference cost scales with the DDIM step count — benchmark it at the step count you'd actually deploy (from your Week-29 step sweep), and report that the cost is roughly $N\times$ a single U-Net pass.

### Part 2 — Measure success and smoothness

On your fixed eval protocol (the Week-29 one), measure for both policies:

- **Success rate** (the same N episodes, same seeds, same criterion).
- **Jerk** ($\sum\|\Delta^2 a\|$ over a rollout) — ACT with temporal ensembling, Diffusion Policy with receding-horizon.

### Part 3 — The five-axis table and the recommendation

Fill the comparison table (Lecture 2 §3) with your measured numbers:

| Axis | ACT | Diffusion Policy |
|---|---|---|
| Success rate (N=___) | | |
| Inference latency (median / p99 ms) | | |
| Deploy-time multimodality | | |
| Jerk (smoothness) | | |
| Training cost (wall-clock) | | |

Then write the **recommendation**: which ships at a 30 Hz (33 ms) budget, and *why*, derived from your table. The recommendation must reference the *budget* — e.g. "ACT's p99 of 7 ms leaves 26 ms of headroom for perception and control; Diffusion Policy's 16-step p99 of 35 ms exceeds the per-tick budget, so it must use the action-queue to decouple inference from control, which adds staleness."

## Acceptance criteria

- [ ] A file `challenge-01-shootout.md` with the benchmark methodology, the measured latency distributions (median + p99) for both, the success and jerk numbers, the five-axis table, and the budget-referenced recommendation.
- [ ] The benchmark follows all five rules; you state explicitly that you warmed up and synchronized (an unsynced GPU benchmark is the disqualifier here).
- [ ] ACT's single-pass latency is clearly lower than $N$-step Diffusion Policy's — and if it *isn't*, you've found a benchmark bug and you fix it before concluding.
- [ ] The recommendation is derived from *your* numbers and references the 30 Hz budget. "ACT is generally faster" without your measurements does not pass.
- [ ] You correctly note at least one axis where the choice could flip (e.g., "if success on a more ambiguous task favored Diffusion Policy's deploy-time multimodality, that would override latency").
- [ ] Committed to your Week 30 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The disqualifying mistake is an **unsynchronized GPU benchmark**: you wrap `time.perf_counter()` around the forward pass, forget `torch.cuda.synchronize()`, and measure only the *kernel launch* (microseconds) instead of the *compute* (milliseconds). Your "latency" comes out absurdly low and roughly equal for both policies — which would make ACT's whole reason for existing vanish. If your two numbers are suspiciously close and suspiciously small, you forgot the sync. The second trap is benchmarking the **cold first call** (no warm-up), which inflates both numbers and adds huge variance. The third is comparing **different precisions** (ACT at FP16 vs Diffusion at FP32, or vice versa) — match them.

A subtler integrity point: report the *p99*, not just the median. A control loop misses its deadline on the *worst* tick, not the average one. A policy with a great median and a terrible p99 (a long tail from occasional GC or memory traffic) can still blow the budget — and that's exactly the kind of thing a real deployment review catches.

## Stretch

- **Quantize and re-benchmark.** Convert both to FP16 (and ACT to INT8 if you can) and re-run. Reason about which policy benefits more from quantization — the setup for Week 39. (Hint: a single big transformer pass vs many small U-Net passes quantize differently.)
- **Jetson vs dev GPU.** If you have an Orin, benchmark on both and show the *absolute* numbers change but the *ordering* (ACT < multi-step Diffusion) holds. If not, benchmark dev-GPU vs CPU and make the same point.
- **The crossover.** Find the DDIM step count at which Diffusion Policy's latency *equals* ACT's, and report the success rate at that step count. If Diffusion Policy needs, say, 4 steps to match ACT's latency, does it still hit the success bar at 4 steps? This is the cleanest statement of the latency/quality frontier.

## Why this matters

In Week 32 and in every real robotics design review, "which policy did you ship and why?" is the question, and "the paper said it's better" is the answer that gets you a follow-up you can't answer. The defensible answer is a fair benchmark and a table. This challenge builds the two habits that make your numbers trustworthy: rigorous benchmarking methodology (warm-up, sync, batch-of-one, precision, p99) and a decision framework that references the *constraint* (the control budget), not just the headline metric. Engineers who measure honestly get to make the call; engineers who guess get overruled by the ones who measured.
