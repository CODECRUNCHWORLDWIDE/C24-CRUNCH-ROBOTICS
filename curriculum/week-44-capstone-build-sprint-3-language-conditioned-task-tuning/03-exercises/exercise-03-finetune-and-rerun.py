#!/usr/bin/env python3
# Exercise 3 — Fine-tune the policy on 50 capstone-specific demos and re-run the suite
#
# Goal: A runnable LoRA fine-tune over a LeRobot-format demo dataset, followed by a
#       re-run-and-diff harness that loads the exercise-2 baseline report and the
#       fine-tuned report and prints the baseline-vs-fine-tuned per-instruction table
#       with regressions flagged and a Wilson CI on the suite total.
#
# Estimated time: 90 minutes of authoring + GPU time (1-2 h on a workstation GPU,
#                 overnight on a Jetson Orin).
#
# HOW TO USE THIS FILE
#
#   It has two subcommands:
#
#     # (A) Fine-tune. Consumes the 50-demo LeRobot dataset you collected.
#     python exercise-03-finetune-and-rerun.py train \
#         --dataset capstone/demos-50 \
#         --out checkpoints/capstone-lora \
#         --steps 3000
#
#     # (B) Diff. After you re-run exercise 2 on the fine-tuned checkpoint
#     #     (producing reports/finetuned/report.json), compare it to the baseline.
#     python exercise-03-finetune-and-rerun.py diff \
#         --baseline reports/baseline/report.json \
#         --finetuned reports/finetuned/report.json \
#         --out reports/diff.md
#
#   The `train` path needs a GPU and the openvla/peft/transformers stack. The `diff`
#   path is pure Python and runs anywhere — author and test it first, it is the
#   week's headline artifact.
#
# This is REAL code. The diff harness runs as-is. The train harness runs against an
# openvla-7b checkpoint and a LeRobot v2 dataset with the schema from lecture 2.

from __future__ import annotations

import argparse
import json
from math import sqrt
from pathlib import Path


# ----------------------------------------------------------------------------
# (A) LoRA fine-tune of an OpenVLA-class policy
# ----------------------------------------------------------------------------

def train(args: argparse.Namespace) -> None:
    # Imports are local so the `diff` subcommand has no heavy deps.
    import torch
    from peft import LoraConfig, get_peft_model
    from torch.utils.data import DataLoader
    from transformers import AutoModelForVision2Seq, AutoProcessor
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        raise SystemExit("fine-tuning a 7B VLA needs a CUDA GPU; borrow one for an afternoon")

    # 1. Load the frozen base policy in bf16.
    processor = AutoProcessor.from_pretrained("openvla/openvla-7b", trust_remote_code=True)
    base = AutoModelForVision2Seq.from_pretrained(
        "openvla/openvla-7b",
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    ).to(device)

    # 2. Wrap with LoRA. r=32/alpha=64 is the OpenVLA fine-tune default; good for ~50 demos.
    lora_cfg = LoraConfig(
        r=32, lora_alpha=64, lora_dropout=0.05,
        target_modules="all-linear", init_lora_weights="gaussian",
    )
    policy = get_peft_model(base, lora_cfg)
    policy.print_trainable_parameters()      # expect ~1-2% trainable, rest frozen

    # 3. The 50-demo dataset. Schema must match deployment (see lecture 2 EpisodeRecorder).
    ds = LeRobotDataset(args.dataset)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True, num_workers=4)

    # 4. Optimizer over ONLY the LoRA params. LR 5e-4 because the base is frozen.
    opt = torch.optim.AdamW(
        (p for p in policy.parameters() if p.requires_grad), lr=5e-4)

    # 5. Train loop. OpenVLA's objective is next-action-token cross-entropy; the model's
    #    forward returns it when fed processed image+instruction+action labels.
    policy.train()
    step = 0
    Path(args.out).mkdir(parents=True, exist_ok=True)
    while step < args.steps:
        for batch in loader:
            inputs = processor(
                text=batch["task"],
                images=batch["observation.images.wrist"],
                return_tensors="pt",
            ).to(device, dtype=torch.bfloat16)
            # action labels are the discretized action tokens for the supervised target
            labels = processor.tokenize_action(batch["action"]).to(device)
            out = policy(**inputs, labels=labels)
            out.loss.backward()
            opt.step()
            opt.zero_grad()

            step += 1
            if step % 100 == 0:
                print(f"step {step}/{args.steps}  loss {out.loss.item():.4f}")
            if step % args.ckpt_every == 0:
                ckpt = Path(args.out) / f"step-{step}"
                policy.save_pretrained(ckpt)        # saves ONLY the LoRA adapter (~few hundred MB)
                print(f"  saved adapter -> {ckpt}")
            if step >= args.steps:
                break

    policy.save_pretrained(Path(args.out) / f"step-{args.steps}")
    print(f"done. select a checkpoint on DEV-SLICE eval success, not on loss (lecture 2 sec 6).")
    print(f"then merge it into the action server with PeftModel.merge_and_unload() and re-run "
          f"exercise 2 on the FROZEN suite to produce reports/finetuned/report.json.")


# ----------------------------------------------------------------------------
# (B) The baseline-vs-fine-tuned diff — the week's headline artifact
# ----------------------------------------------------------------------------

def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def diff(args: argparse.Namespace) -> None:
    base = json.loads(Path(args.baseline).read_text())
    tuned = json.loads(Path(args.finetuned).read_text())

    if base["suite_commit"] != tuned["suite_commit"]:
        raise SystemExit(
            f"REFUSING TO DIFF: suites differ "
            f"(baseline {base['suite_commit']} vs fine-tuned {tuned['suite_commit']}). "
            f"You must run both against the SAME frozen suite. See lecture 1.")

    base_by_id = {r["id"]: r for r in base["rows"]}
    tuned_by_id = {r["id"]: r for r in tuned["rows"]}

    lines = [
        f"suite: {base['suite_version']}  commit: {base['suite_commit']}  "
        f"seed: {base['master_seed']}",
        f"baseline: {base['policy']}        fine-tuned: {tuned['policy']}",
        "",
        "| id | instruction | axis | base | tuned | Δ |",
        "|---:|-------------|------|-----:|------:|---|",
    ]
    regressions = []
    for i in sorted(base_by_id):
        b, t = base_by_id[i], tuned_by_id[i]
        delta = t["k"] - b["k"]
        if delta < 0:
            tag = "⚠ REGRESSION"
            regressions.append((i, b["text"], b["k"], t["k"]))
        elif t["k"] >= 3 and b["k"] < 3:
            tag = "✓ fix"
        elif t["k"] >= 3:
            tag = "✓"
        else:
            tag = "✗ still failing"
        lines.append(
            f"| {i} | {b['text']} | {b['axis']} | {b['k']}/{b['n']} | "
            f"{t['k']}/{t['n']} | {delta:+d} {tag} |")

    base_passed = sum(r["passed"] for r in base["rows"])
    tuned_passed = sum(r["passed"] for r in tuned["rows"])
    tk = sum(r["k"] for r in tuned["rows"])
    tn = sum(r["n"] for r in tuned["rows"])
    lo, hi = wilson_interval(tk, tn)
    lines.append(
        f"| -- | **INSTRUCTIONS PASSED** | | **{base_passed}/20** | "
        f"**{tuned_passed}/20** | **{tuned_passed - base_passed:+d}** |")
    lines.append("")
    lines.append(f"fine-tuned trial-success {tk}/{tn} = {tk / tn:.2f}, "
                 f"95% Wilson CI [{lo:.2f}, {hi:.2f}]")
    lines.append("")
    bar = "OVER" if tuned_passed >= 15 else "UNDER"
    lines.append(f"**Acceptance bar (>= 15/20): {tuned_passed}/20 — {bar} the bar.**")
    if regressions:
        lines.append("")
        lines.append("### Regressions (must be explained in the failure-diagnosis section)")
        for i, text, bk, tk_ in regressions:
            lines.append(f"- id {i} \"{text}\": {bk}/5 -> {tk_}/5 — fine-tuning hurt this one.")

    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {args.out}")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="LoRA fine-tune + baseline-vs-fine-tuned diff")
    sub = p.add_subparsers(dest="cmd", required=True)

    pt = sub.add_parser("train", help="LoRA fine-tune on the 50-demo dataset")
    pt.add_argument("--dataset", required=True, help="LeRobot v2 repo_id or local path")
    pt.add_argument("--out", required=True, help="adapter output dir")
    pt.add_argument("--steps", type=int, default=3000)
    pt.add_argument("--batch-size", type=int, default=8)
    pt.add_argument("--ckpt-every", type=int, default=500)
    pt.set_defaults(func=train)

    pd = sub.add_parser("diff", help="diff two exercise-2 reports")
    pd.add_argument("--baseline", required=True)
    pd.add_argument("--finetuned", required=True)
    pd.add_argument("--out", default="reports/diff.md")
    pd.set_defaults(func=diff)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------------
# EXPECTED OUTPUT (reports/diff.md), numbers will be yours:
#
#   suite: 1.0.0  commit: 4f2a9c1  seed: 20260609
#   baseline: openvla-7b baseline        fine-tuned: openvla-7b + capstone-lora step-2000
#
#   | id | instruction                              | axis        | base | tuned | Δ        |
#   |---:|------------------------------------------|-------------|-----:|------:|----------|
#   |  1 | bring me the red cup from the left bench | object_...  | 3/5  | 5/5   | +2 ✓     |
#   |  2 | put the blue block on the right shelf    | spatial_... | 1/5  | 4/5   | +3 ✓ fix |
#   |  7 | grab the cup next to the toolbox         | object_...  | 2/5  | 1/5   | -1 ⚠ REGRESSION |
#   | ...                                                                                  |
#   | -- | INSTRUCTIONS PASSED                      |             | 9/20 | 16/20 | +7       |
#
#   fine-tuned trial-success 80/100 = 0.80, 95% Wilson CI [0.71, 0.87]
#   Acceptance bar (>= 15/20): 16/20 — OVER the bar.
#
# ACCEPTANCE CRITERIA
#   [ ] `train` runs to completion on a GPU and saves periodic LoRA adapters.
#   [ ] You selected the checkpoint on a DEV slice, not on lowest loss.
#   [ ] You re-ran exercise 2 on the merged fine-tuned policy against the SAME frozen
#       suite (the diff refuses to run if commit hashes differ).
#   [ ] `diff` prints the per-instruction table, flags every regression, and reports a
#       Wilson CI plus the OVER/UNDER acceptance call.
# ----------------------------------------------------------------------------
