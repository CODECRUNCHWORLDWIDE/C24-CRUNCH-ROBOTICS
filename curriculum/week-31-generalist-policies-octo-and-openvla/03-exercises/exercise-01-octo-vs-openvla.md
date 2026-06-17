# Exercise 1 — Octo vs. OpenVLA, and a Zero-Shot Forward Pass

**Goal:** Cement the two architectures from Lecture 1 by answering a precise comparison worksheet, then *see* a VLA produce an action: load `openvla-7b`, feed it an image and an instruction, and read the 7-D EE-delta it emits zero-shot. You leave this exercise able to draw both models and able to run one.

**Estimated time:** 60 minutes. Guided.

---

## Part A — The comparison worksheet (no GPU needed)

Answer each from Lecture 1. Write your answers in `notes/week-31/architecture-worksheet.md`. These are exactly the questions a Week 32 panelist asks.

1. **Action representation.** OpenVLA represents an action as *discrete tokens*; Octo represents an action as a *continuous chunk from a diffusion head*. For each: how many numbers is one action, and what are they (name the 7 dimensions of the OXE EE-delta)?
2. **The backbone.** Name OpenVLA's three backbone pieces (the LLM and the two visual encoders) and say, in one phrase each, what DINOv2 contributes versus what SigLIP contributes.
3. **Tokenization math.** OpenVLA uses 256 bins per dimension over the `[q01, q99]` range. If dimension `Δx` has `q01 = -0.04 m` and `q99 = +0.04 m`, how wide is one bin in millimeters? Is that fine enough for a tabletop pick? Show the arithmetic.
4. **The prompt.** Write OpenVLA's exact prompt template and explain what plays the role of the "task specification."
5. **Latency.** Why is OpenVLA inference much slower than Octo's? Give two distinct reasons (size *and* decoding strategy).
6. **The choice.** Your task is one fixed "pick the red cube" with 200 demos and a 50 ms latency budget on an Orin. Argue, in three sentences, whether you'd ship OpenVLA, Octo, or last week's ACT — and why.

**Acceptance for Part A:** all six answered; the bin-width arithmetic in (3) is correct (it's `0.08 m / 256 ≈ 0.3125 mm`); the choice in (6) names a specific model with a latency-or-data justification.

---

## Part B — A zero-shot forward pass (needs the 7B checkpoint)

Now run one. This is *not* a fine-tune — it's a single forward pass on the pretrained model, so you see the output shape and feel the latency before Thursday's lab. Save as `zero_shot_probe.py`.

```python
#!/usr/bin/env python3
"""Load openvla-7b and run ONE zero-shot action prediction.

Confirms your environment, the checkpoint download, and the output shape before
you rent a GPU for fine-tuning. ~16 GB download, ~16 GB VRAM in bf16.
"""
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForVision2Seq, AutoProcessor

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if DEVICE == "cuda" else torch.float32


def main() -> None:
    print(f"device={DEVICE} dtype={DTYPE}")

    # The processor builds the prompt + tokenizes; the model is the Prismatic-7B VLA.
    processor = AutoProcessor.from_pretrained("openvla/openvla-7b", trust_remote_code=True)
    model = AutoModelForVision2Seq.from_pretrained(
        "openvla/openvla-7b",
        torch_dtype=DTYPE,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    ).to(DEVICE)

    # A stand-in observation: a real wrist/scene image is HxWx3 uint8. Here, noise,
    # so you see the SHAPE of the output. Swap in a real frame from your Week 29 data
    # to see a meaningful (if zero-shot) action.
    rng = np.random.default_rng(0)
    image = Image.fromarray(rng.integers(0, 255, (256, 256, 3), dtype=np.uint8))
    instruction = "pick up the red cube"

    # OpenVLA's prompt template. The processor wraps the instruction in it.
    prompt = f"In: What action should the robot take to {instruction}?\nOut:"
    inputs = processor(prompt, image).to(DEVICE, dtype=DTYPE)

    # predict_action de-tokenizes the 7 action tokens and un-normalizes with the
    # stats keyed by unnorm_key. For the PRETRAINED model use a known OXE key.
    # After YOU fine-tune, you pass YOUR dataset's key here (Lecture 2 Part 2.4).
    with torch.no_grad():
        action = model.predict_action(**inputs, unnorm_key="bridge_orig", do_sample=False)

    action = np.asarray(action).reshape(-1)
    labels = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "grip"]
    print("zero-shot action (EE-delta, un-normalized to bridge_orig units):")
    for name, val in zip(labels, action):
        print(f"  {name:7s} = {val:+.5f}")
    assert action.shape == (7,), f"expected 7-D action, got {action.shape}"
    print("\nOK: VLA emitted a 7-D EE-delta. This is one (dx,dy,dz,droll,dpitch,dyaw,grip).")
    print("It is GARBAGE on a noise image + wrong unnorm_key — that's the point of zero-shot.")


if __name__ == "__main__":
    main()
```

Run it:

```bash
python3 zero_shot_probe.py
```

---

## What you should observe

```
device=cuda dtype=torch.bfloat16
zero-shot action (EE-delta, un-normalized to bridge_orig units):
  dx      = +0.01234
  dy      = -0.00821
  dz      = +0.00310
  droll   = -0.00104
  dpitch  = +0.00077
  dyaw    = +0.00219
  grip    = +0.99600
OK: VLA emitted a 7-D EE-delta. This is one (dx,dy,dz,droll,dpitch,dyaw,grip).
```

The **numbers are meaningless** (noise image, mismatched `unnorm_key`) — that's expected and it's the lesson. What matters: the model loaded, ran, and emitted a 7-vector in the EE-delta convention. Note the wall-clock time of that one forward pass; on an Orin it would be far worse, which is the latency story Week 37/39 confronts.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `notes/week-31/architecture-worksheet.md` answers all six Part-A questions; the bin-width arithmetic gives ≈ 0.3125 mm.
- [ ] `zero_shot_probe.py` runs, loads `openvla-7b`, and prints a **7-element** action vector without shape errors.
- [ ] You can state, in one sentence, why the printed action is garbage (noise image and/or wrong `unnorm_key`) — proving you understand that zero-shot on a mismatched setup is expected to be bad.
- [ ] You recorded the single-forward-pass latency and can compare it to last week's ACT latency.

---

## Stretch

- Swap the noise image for a **real frame from your Week 29 data** and a real instruction. The action is still zero-shot (likely poor) but now plausibly *directional* — does `grip` open/close sensibly? This is your zero-shot baseline intuition before Thursday.
- Load **Octo-Small** (JAX) and run its inference on the same frame. Compare the wall-clock latency to OpenVLA's. The ~270× parameter gap shows up directly in the timing.
- Set `do_sample=True` and run the same input several times. Observe how much the action varies — a window into the model's uncertainty at this state.

---

When the architectures feel concrete, move to [Exercise 2 — Action tokenization](./exercise-02-action-tokenization.py).
