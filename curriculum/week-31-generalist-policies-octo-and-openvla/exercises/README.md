# Week 31 — Exercises

Three drills that build from "understand the architectures" to "your data is in the format OpenVLA can fine-tune on." Do them in order — Exercise 2's tokenizer and Exercise 3's dataset are both prerequisites for the mini-project and the challenge. Run them against your **Week 29 demonstrations**; if those are gone, re-collect a small set first (the VLA work is meaningless without your own task data).

## Index

1. **[Exercise 1 — Octo vs. OpenVLA, and a zero-shot forward pass](exercise-01-octo-vs-openvla.md)** — answer a precise architecture-comparison worksheet from the lecture, then load `openvla-7b` and run one zero-shot `predict_action` to see the shape of a VLA output. (~60 min, guided)
2. **[Exercise 2 — Action tokenization end to end](exercise-02-action-tokenization.py)** — implement OpenVLA's 256-bin action tokenizer and de-tokenizer, round-trip a real EE-delta, and prove the un-normalization trap is real by mismatching stats on purpose. (~75 min, runnable)
3. **[Exercise 3 — Convert your demos to LeRobot](exercise-03-lerobot-conversion.py)** — turn your Week 29 trajectories into a `LeRobotDataset`, compute the stats, and validate the schema is exactly what the OpenVLA fine-tuner expects. (~60 min, runnable)

## How to work the exercises

- **Set up the environment once.** A `conda`/`venv` with `torch>=2.2`+CUDA, `transformers>=4.40`, `peft`, `lerobot`, and the `openvla` repo cloned. Exercise 1 confirms it works before you rent a GPU.
- **Exercise 2 needs no GPU and no big download** — it's pure NumPy and the tokenization math. Do it first if your GPU box isn't ready; understanding tokenization is the conceptual core of the week.
- **Exercise 1's zero-shot forward pass needs the 7B checkpoint** (~16 GB download, ~16 GB VRAM in fp16/bf16). Run it on the cloud GPU you'll use Thursday, or on a local card with ≥16 GB. CPU works but is painfully slow — fine for a single forward pass to see the output shape.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match the *shape*, you're not done. (Exact numbers depend on your data; the shape is invariant.)

## Running the Python exercises

The two `.py` files are standalone. Exercise 2 needs only NumPy:

```bash
python3 exercise-02-action-tokenization.py
```

Exercise 3 needs `lerobot` and your Week 29 demos on disk:

```bash
pip install lerobot
python3 exercise-03-lerobot-conversion.py --demos /path/to/week29_demos --out /data/lerobot
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-31` to compare.
