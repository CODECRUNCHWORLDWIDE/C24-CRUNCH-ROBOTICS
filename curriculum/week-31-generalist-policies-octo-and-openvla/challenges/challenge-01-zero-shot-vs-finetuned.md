# Challenge 1 — Zero-Shot vs. Fine-Tuned OpenVLA, With a Failure Analysis

**Time estimate:** ~3–4 hours (including one cloud-GPU fine-tune of ~30–90 min).

## Problem statement

You are the ML engineer at a robotics startup. Your lead hands you `openvla-7b` and says: *"We have 150 teleop demos of the cube-pick. Tell me, with numbers, whether fine-tuning is worth the GPU bill, and if it fails, tell me whether it's the eyes, the ears, or the hands."* That is this challenge. You will:

1. Fine-tune OpenVLA on your Week 29 demos (LeRobot format from Exercise 3) with LoRA, one epoch.
2. Evaluate **both** the zero-shot model and your fine-tuned checkpoint on a **held-out** eval protocol.
3. Report the honest number and the gap closed.
4. Classify every failure into **perception / grounding / control** and prescribe a fix for the dominant class.

This is the syllabus lab for Week 31 ("fine-tune an open-weight OpenVLA on the week-29 demos for one epoch on a cloud GPU; compare zero-shot vs. fine-tuned success rate; document the failure modes"), done to publishable standard.

## Setup

- Your Week 29 demos converted to a `LeRobotDataset` with **valid `meta/stats.json`** (Exercise 3). Split off an eval set *before* training — do not evaluate on training demos.
- A cloud GPU with ≥ 24 GB VRAM. The whole run (download + fine-tune + eval) should fit comfortably in a few GPU-hours, well under the $25/month budget if you stop the instance when done.
- The OpenVLA repo's `finetune.py` (LoRA mode) and your environment from the exercises.

## Part 1 — Fine-tune

Launch the LoRA fine-tune (flags track the OpenVLA repo; see Lecture 2 Part 2.5):

```bash
torchrun --standalone --nproc-per-node 1 vla-scripts/finetune.py \
  --vla_path openvla/openvla-7b \
  --data_root_dir /data/lerobot \
  --dataset_name crunch_week29_pick_red_cube \
  --use_lora True --lora_rank 32 \
  --batch_size 8 --grad_accumulation_steps 4 \
  --learning_rate 5e-4 --image_aug True \
  --max_steps 2000 --save_steps 500
```

Register **your** dataset's normalization stats under a named `unnorm_key` and confirm the fine-tuner used it (Lecture 2 Part 2.4 — this is the make-or-break step). Watch the **action-token accuracy** climb; stop when it plateaus.

## Part 2 — The held-out eval protocol

Define, *before* you run, a fixed protocol. At minimum:

- **Condition A — held-out positions:** same object, same instruction "pick up the red cube", `n = 40` trials from start positions not in the training demos.
- **Condition B — held-out phrasing:** `n = 20` trials with a re-worded instruction ("grab the red block"). This probes the 7B language prior.
- (Optional **Condition C — distractor:** add a blue cube; `n = 20`. Probes grounding.)

A trial **succeeds** if the cube ends up grasped and lifted (define the exact success predicate — e.g., gripper closed on the cube and EE z > threshold for 1 s). Run the **same** protocol against zero-shot `openvla-7b` (no adapter) and against your fine-tuned checkpoint.

## Part 3 — The numbers

Produce the honest-number table:

```
=== VLA EVAL: pick_red_cube ===
                          Cond A (positions, n=40)   Cond B (phrasing, n=20)
zero-shot openvla-7b      __ / 40  (__%)             __ / 20  (__%)
fine-tuned (LoRA, 1 ep)   __ / 40  (__%)             __ / 20  (__%)
gap closed (A):  +__ pts        gap closed (B):  +__ pts
```

## Part 4 — The failure analysis (the deliverable)

For **every** failed trial across both checkpoints, classify it:

| Class | Test you apply | Count (zero-shot) | Count (fine-tuned) |
|---|---|---|---|
| **Perception** | EE went to empty space / wrong location; object out of frame or unlit | | |
| **Grounding** | Saw and reached an object, but the *wrong* one / ignored the instruction | | |
| **Control** | Right target, bad trajectory: missed grasp by cm, collided, dropped | | |

Then write 300–500 words: which class dominates each checkpoint, the *most likely root cause* of the dominant class (and explicitly check whether "control" failures are actually the **un-normalization** or EE-delta→IK mapping from Lecture 2 — they usually are), and the one fix you would try next.

## Acceptance criteria

- [ ] A fine-tuned LoRA checkpoint exists, trained on your LeRobot dataset, with **your** `unnorm_key` registered and used (state how you verified this).
- [ ] `challenges/challenge-01/eval-results.md` contains the honest-number table for at least Conditions A and B, with explicit `n` and the success predicate defined.
- [ ] A failure-classification table with counts that **sum to the number of failures** in each column (no unclassified failures).
- [ ] A 300–500-word analysis naming the dominant failure class per checkpoint and a concrete next fix.
- [ ] You explicitly checked and reported whether any "control" failures were actually un-normalization / IK-mapping bugs rather than policy errors.
- [ ] Committed under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The most common self-own this week: your fine-tuned model gets a *low* success rate and you conclude "fine-tuning didn't help / the model is bad." Before you write that, check three things in order: (1) **un-normalization** — did inference use the same stats you fine-tuned with? Run a known action through your Exercise-2 round-trip with the *deployed* stats and confirm it recovers correct real units. (2) **EE-delta→controller mapping** — is the 7-vector actually reaching the arm as an EE-delta in the right frame, or is something interpreting it as joints/absolute? (3) **camera framing** — does your eval camera match the framing in your demos? A huge fraction of "the VLA can't grasp" turns out to be one of these three, none of which is the policy's fault. Diagnose the pipeline before you blame the model. That habit *is* the senior skill.

## Stretch

- Add **Condition C (distractor)** and show that fine-tuning improves grounding (picks red, not blue) more than it improves raw position accuracy — evidence the language prior is doing work.
- Run the eval at **two LoRA ranks** (`r=16` vs `r=32`) and report whether the extra capacity helped on your ~150 demos or just overfit.
- Compare the fine-tuned OpenVLA against your **Week 30 ACT** on Condition A at a fixed latency budget. If ACT wins on this single fixed task, say so — that honesty is exactly the senior judgment the README asks for.

## Why this matters

In Week 32 you stand in front of a panel and defend a learned policy. They will not ask you to recite the OpenVLA architecture — they will point at your success-rate table and ask "why did it fail those nine times, and what would you do about it?" This challenge *is* that conversation, rehearsed, with the un-normalization trap already disarmed. The engineer who can say "six of nine were grounding failures, here's my fine-tune-data fix, and I ruled out un-normalization by round-tripping a known action" is the one who gets the offer.
