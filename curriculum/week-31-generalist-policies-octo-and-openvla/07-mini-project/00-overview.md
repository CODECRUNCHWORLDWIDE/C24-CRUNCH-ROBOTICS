# Mini-Project — `crunchbot_vla_eval`: A Reproducible Zero-Shot-vs-Fine-Tuned Evaluator

> Build a small, reusable harness that loads any OpenVLA checkpoint (zero-shot or your fine-tuned LoRA adapter), runs a **fixed, held-out eval protocol** against a task, and emits the honest-number table plus a **perception/grounding/control failure breakdown** — reproducibly, from a config file, with a non-zero exit on regression.

This is the artifact that turns "I fine-tuned a VLA and it seemed better" into "here is the A/B, here is the held-out denominator, here is why it failed nine times." It is the *evaluation* spine you defend at the Week 32 midterm, and it is the same harness you will re-point at the capstone's 20-instruction eval suite in Week 44. Build it once, well, and you never hand-tally a VLA eval again.

**Estimated time:** ~12.5 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This harness becomes your standing policy-evaluation tool. **Week 37** wires the fine-tuned OpenVLA into the mobile manipulator and re-runs this eval on three instructions; **Week 44** runs it on the capstone's twenty-instruction suite for per-instruction success rates. The config-driven, exit-coded design means it drops straight into a CI/regression gate.

---

## What you will build

A small Python package `crunchbot_vla_eval` with three deliverables:

1. **`crunchbot_vla_eval/policy.py`** — a thin, uniform `VLAPolicy` wrapper around an OpenVLA checkpoint that exposes a single `predict(image, instruction) -> action_7d` method, hides the `unnorm_key` plumbing, and supports loading **either** the base model (zero-shot) **or** a LoRA adapter on top. The whole point is that the evaluator never sees the difference — it just calls `predict`.
2. **`crunchbot_vla_eval/evaluator.py`** — the harness. Reads a YAML protocol (conditions, `n`, instructions, the success predicate), runs each trial in your sim env (Gz Sim or Isaac, whatever your Week 29 task lives in), records success/failure, and on each failure prompts you (or an auto-classifier, see below) for a **perception/grounding/control** label. Emits the honest-number table and the failure breakdown; exits non-zero if a named checkpoint underperforms a configured threshold.
3. **A config + report** (`protocols/pick_red_cube.yaml` + a generated `reports/<checkpoint>.md`) so a run is fully described by a file and produces a committed artifact.

By the end you have a repo of ~300–400 lines that runs `vla-eval --protocol pick_red_cube.yaml --checkpoint <path>` and produces a portfolio-grade evaluation report.

---

## Why a harness and not a notebook

You *could* eval in a Jupyter notebook. Don't — not as the source of truth. A harness gives you:

- **Reproducibility.** The protocol is a committed YAML, not cells you re-ran in some order you can't reconstruct. "n=40 from these seeds, this success predicate" is in the file.
- **A fair A/B.** The *same* evaluator runs zero-shot and fine-tuned through the *same* `VLAPolicy` interface, so the only thing that differs is the checkpoint. No accidental "I used a different success threshold for the fine-tuned run."
- **A regression gate.** A non-zero exit on under-threshold means this drops into CI: a fine-tune that makes things *worse* fails the build instead of getting quietly committed.

This is the same "decision in one place, verifiable on a real run" discipline as Week 5's `crunchbot_qos` auditor, applied to policy evaluation.

---

## Package layout

```
crunchbot_vla_eval/
├── pyproject.toml
├── crunchbot_vla_eval/
│   ├── __init__.py
│   ├── policy.py            # VLAPolicy: load base or LoRA, predict(image, instr) -> 7d
│   ├── evaluator.py         # run protocol, tally, classify failures, exit code
│   ├── failure_taxonomy.py  # the 3-class enum + a rule-based auto-classifier helper
│   └── cli.py               # `vla-eval` entry point
├── protocols/
│   └── pick_red_cube.yaml   # conditions, n, instructions, success predicate, thresholds
├── reports/                 # generated, committed eval reports
└── tests/
    ├── test_policy_iface.py  # VLAPolicy.predict returns a 7-vector; unnorm_key honored
    └── test_tally.py         # the success/failure tally + threshold-gate logic
```

---

## Deliverable 1 — `policy.py` (the uniform interface)

`VLAPolicy` must:

- Load `openvla/openvla-7b` as the base, **optionally** apply a LoRA adapter from a path (so the same class serves zero-shot and fine-tuned).
- Take the **`unnorm_key` in the constructor** and use it on every `predict` — making the Lecture-2 un-normalization trap impossible to hit by construction (the evaluator can't forget it).
- Expose exactly one method: `predict(image: np.ndarray, instruction: str) -> np.ndarray` returning a 7-D EE-delta.

Spine to start from:

```python
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForVision2Seq, AutoProcessor


class VLAPolicy:
    def __init__(self, base="openvla/openvla-7b", adapter=None, unnorm_key=None,
                 device="cuda"):
        self.device = device
        self.unnorm_key = unnorm_key            # MUST match what fine-tuning used
        self.processor = AutoProcessor.from_pretrained(base, trust_remote_code=True)
        model = AutoModelForVision2Seq.from_pretrained(
            base, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        if adapter is not None:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, adapter)   # load your LoRA on top
        self.model = model.to(device)

    @torch.no_grad()
    def predict(self, image: np.ndarray, instruction: str) -> np.ndarray:
        prompt = f"In: What action should the robot take to {instruction}?\nOut:"
        inputs = self.processor(prompt, Image.fromarray(image)).to(
            self.device, dtype=torch.bfloat16)
        action = self.model.predict_action(
            **inputs, unnorm_key=self.unnorm_key, do_sample=False)
        return np.asarray(action).reshape(7)
```

> **The rule this enforces:** `unnorm_key` is set *once*, at construction, from the checkpoint's own stats. No call site can pass the wrong key, so the silent magnitude bug from Lecture 2 cannot occur in your eval. That is the whole reason the wrapper exists.

---

## Deliverable 2 — `evaluator.py` (the harness)

The evaluator must:

1. Load a **protocol YAML** declaring `conditions` (each with `name`, `n`, `instruction`, and start-state seeds), the `success_predicate`, and per-checkpoint `min_success` thresholds.
2. For each condition, run `n` trials: reset the sim to a seeded start state, loop `predict → step the env → check the success predicate`, record success/failure. (Use whatever sim env your Week 29 task lives in; abstract it behind a tiny `Env` protocol so the harness is sim-agnostic.)
3. On each failure, attach a **failure label** — manual (you watch and tag) or via the rule-based helper in `failure_taxonomy.py` (e.g., "EE never came within R of any object" → perception; "reached the wrong object" → grounding; "reached the target, grasp metric failed" → control).
4. Print the honest-number table and the per-class failure breakdown.
5. **Exit non-zero** if any checkpoint's success rate is below its `min_success` threshold.

The verdict logic core (this is what `test_tally.py` tests):

```python
def gate(results: dict, thresholds: dict) -> int:
    """Return 0 if every checkpoint meets its threshold, else 1."""
    failed = [
        name for name, r in results.items()
        if r.success_rate < thresholds.get(name, 0.0)
    ]
    return 1 if failed else 0
```

Expected shape of output:

```
=== VLA EVAL: pick_red_cube ===
checkpoint            Cond A (n=40)    Cond B (n=20)
zero-shot             11/40 (27.5%)    3/20 (15.0%)
finetuned-lora        33/40 (82.5%)    13/20 (65.0%)

failure breakdown (finetuned-lora):  perception 2 | grounding 4 | control 1
gate: finetuned-lora >= 0.70 (Cond A) -> PASS ;  zero-shot is baseline (no gate)
exit 0
```

---

## Deliverable 3 — the protocol config + a committed report

`protocols/pick_red_cube.yaml`:

```yaml
task: pick_red_cube
success_predicate:
  type: grasped_and_lifted
  lift_z: 0.05
  hold_s: 1.0
conditions:
  - name: positions
    instruction: "pick up the red cube"
    n: 40
    seeds: [0, 1, 2, ...]        # 40 seeds for reproducible start states
  - name: phrasing
    instruction: "grab the red block"
    n: 20
    seeds: [100, 101, ...]
thresholds:
  finetuned-lora:
    positions: 0.70             # gate: fine-tuned must clear 70% on held-out positions
```

A run writes `reports/<checkpoint>.md` with the table, the breakdown, and the exact protocol used — a committed, portfolio-grade artifact.

---

## Rules

- **You may** read the OpenVLA repo, the PEFT docs, the LeRobot docs, and your own exercise solutions.
- **You must not** let any call site pass `unnorm_key` per-`predict`. It is set once in `VLAPolicy.__init__`. If `grep -rn "unnorm_key" --include=*.py | grep -v "def __init__"` shows it passed anywhere else, you've reopened the trap.
- **You must not** evaluate on training demos. The eval start states must be held out from fine-tuning. State how you guaranteed this.
- The harness must be **sim-agnostic**: the same evaluator works whether the env is Gz Sim or Isaac, behind a small `Env` protocol.
- The gate must exit non-zero on under-threshold so it can run in CI.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-31-crunchbot-vla-eval-<yourhandle>`.
- [ ] `VLAPolicy` loads both the base (zero-shot) and a LoRA adapter through one interface; `unnorm_key` is constructor-only.
- [ ] `vla-eval --protocol pick_red_cube.yaml --checkpoint zero-shot` and `... --checkpoint finetuned-lora` both run and produce a `reports/*.md`.
- [ ] The report contains the honest-number table (≥ 2 conditions, explicit `n`) and a failure breakdown whose counts sum to the failures.
- [ ] The gate exits **non-zero** when a checkpoint is below threshold (demonstrate by lowering a threshold above the fine-tuned rate, or vice-versa).
- [ ] `tests/` pass: `test_policy_iface.py` (predict returns a 7-vector; unnorm_key honored) and `test_tally.py` (success-rate + gate logic, including the threshold boundary).
- [ ] A `README.md` with the run commands, the protocol schema, and a paragraph on why `unnorm_key` is constructor-only.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Uniform policy interface** | 20 | `VLAPolicy` serves zero-shot and LoRA identically; `unnorm_key` set once; trap closed by construction. |
| **Honest eval discipline** | 25 | Held-out start states (proven); fixed `n`; identical protocol across checkpoints; a defensible success predicate. |
| **Failure taxonomy** | 20 | Every failure classified perception/grounding/control; counts sum; the auto-classifier rules are sane. |
| **Reproducibility & gate** | 20 | Protocol is a committed YAML; non-zero exit on under-threshold; the report is regenerable from the config. |
| **Tests** | 10 | Interface and tally/gate logic tested; green. |
| **Docs & hygiene** | 5 | Clear README; no checkpoints/big blobs committed; sensible commits. |

**90+** is portfolio-grade and ready for the Week 32 midterm and the Week 44 capstone eval suite. **70–89** works but has a soft predicate or a leaky train/eval split. **Below 70** means the A/B isn't honest — fix the held-out split first.

---

## Stretch goals

- **Per-instruction breakdown.** Generalize the protocol to N instructions and emit a per-instruction success table — exactly the Week 44 capstone deliverable, built 13 weeks early.
- **Auto-classifier.** Make `failure_taxonomy.py` classify failures from the trajectory automatically (distance-to-nearest-object for perception, which-object-reached for grounding, grasp-metric for control) so a 40-trial eval needs no manual tagging. Validate it agrees with your hand labels on a sample.
- **Bootstrap CIs.** Report a 95% confidence interval on each success rate (bootstrap over trials) so "82.5% (n=40)" comes with `[70%, 92%]` — a senior reviewer's first question about any rate is "what's the CI?"
- **Octo head-to-head.** Add an `OctoPolicy` behind the same `predict` interface and run the identical protocol — a true generalist-vs-generalist A/B at matched eval, with the latency delta reported.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
