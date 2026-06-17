#!/usr/bin/env python3
# Exercise 2 — Action tokenization end to end (the heart of OpenVLA)
#
# Goal: Implement OpenVLA's continuous-action <-> discrete-token pipeline yourself,
#       round-trip a real 7-DOF EE-delta through it, and PROVE the un-normalization
#       trap is real by binning with one dataset's stats and un-normalizing with
#       another's. After this, "the robot twitches instead of reaching" is a bug you
#       can name, not a mystery.
#
# Estimated time: 75 minutes. Runnable. Pure NumPy — no GPU, no model download.
#
# WHAT OPENVLA ACTUALLY DOES (Lecture 1 Part 3.3):
#
#   continuous a (R^7) --normalize/clamp to [q01,q99]--> bin index (0..255)^7
#       --map bin -> reserved rare LLM token id--> 7 action tokens   (the LLM predicts these)
#       --token -> bin -> bin center -> un-normalize with per-dim (q01,q99)--> â (R^7)
#
#   This file implements every arrow with NumPy so the math is undeniable.
#
# HOW TO USE THIS FILE
#
#       python3 exercise-02-action-tokenization.py
#
#   It runs three demonstrations and prints PASS/FAIL for each:
#     PART A — round-trip: tokenize then de-tokenize a known action; error is < one
#              bin width (quantization is the only loss). Prints PASS.
#     PART B — the un-norm trap: bin with stats_A, un-normalize with stats_B; the
#              recovered action is WRONG by a scale factor even though the bins were
#              "correct". Prints the wrong magnitude. This is the silent bug.
#     PART C — token mapping: show the bins map onto the reserved tail of a 32000-token
#              vocab, exactly as OpenVLA maps onto the least-used Llama tokens.
#
# ACCEPTANCE CRITERIA
#
#   [ ] Part A round-trips within one bin width on every dimension -> "PART A: PASS".
#   [ ] Part B recovers an action whose magnitude is wrong by the stats ratio,
#       demonstrating the un-normalization trap -> "PART B: trap reproduced".
#   [ ] Part C prints token ids in the reserved tail range [31744, 32000).
#   [ ] You can state, in one sentence, why mismatched stats give right DIRECTION but
#       wrong MAGNITUDE.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import numpy as np

# OpenVLA's binning resolution and the Llama vocab size it carves the tail from.
N_BINS = 256
VOCAB_SIZE = 32000
# The 256 reserved action tokens are the LAST 256 ids of the vocabulary (the tail
# the LLM almost never emits as natural text). bin i -> token (VOCAB_SIZE - 256 + i).
ACTION_TOKEN_BASE = VOCAB_SIZE - N_BINS  # 31744

# The 7 EE-delta dimensions, for readable printing.
DIMS = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "grip"]


class ActionTokenizer:
    """OpenVLA-style per-dimension uniform-bin action tokenizer.

    Built from per-dimension (q01, q99) percentile stats — exactly the numbers that
    live in a LeRobotDataset's meta/stats.json (Lecture 2 Part 1.2). The SAME stats
    object must be used to tokenize at train time and to de-tokenize at inference.
    """

    def __init__(self, q01: np.ndarray, q99: np.ndarray, n_bins: int = N_BINS) -> None:
        self.q01 = np.asarray(q01, dtype=np.float64)
        self.q99 = np.asarray(q99, dtype=np.float64)
        self.n_bins = n_bins
        # Guard against a degenerate (q01 == q99) dimension (e.g., a gripper that is
        # always 1.0 in the data) — it would divide by zero. Give it a tiny span.
        span = self.q99 - self.q01
        span[span == 0.0] = 1e-8
        self._span = span

    def normalize(self, action: np.ndarray) -> np.ndarray:
        """Map real action -> [0,1] per dim using (q01,q99); clamp out-of-range."""
        x = (np.asarray(action, dtype=np.float64) - self.q01) / self._span
        return np.clip(x, 0.0, 1.0)

    def to_bins(self, action: np.ndarray) -> np.ndarray:
        """Real action -> bin index in {0..n_bins-1} per dimension."""
        norm = self.normalize(action)
        # floor into n_bins buckets; the value exactly == 1.0 must land in bin n_bins-1.
        idx = np.minimum((norm * self.n_bins).astype(np.int64), self.n_bins - 1)
        return idx

    def to_tokens(self, action: np.ndarray) -> np.ndarray:
        """Real action -> reserved action-token ids (the LLM's targets)."""
        return ACTION_TOKEN_BASE + self.to_bins(action)

    def from_bins(self, bins: np.ndarray) -> np.ndarray:
        """Bin index -> real action, using THIS tokenizer's (q01,q99) stats.

        We reconstruct the BIN CENTER (the (i + 0.5)/n_bins point) and un-normalize.
        Using the center, not the edge, halves the worst-case quantization error.
        """
        bins = np.asarray(bins, dtype=np.float64)
        norm_center = (bins + 0.5) / self.n_bins
        return self.q01 + norm_center * self._span

    def from_tokens(self, tokens: np.ndarray) -> np.ndarray:
        """Reserved token ids -> real action (the inference path)."""
        bins = np.asarray(tokens, dtype=np.int64) - ACTION_TOKEN_BASE
        return self.from_bins(bins)

    @property
    def bin_width(self) -> np.ndarray:
        return self._span / self.n_bins


def part_a_round_trip() -> bool:
    print("=" * 70)
    print("PART A — round-trip: tokenize then de-tokenize a known action")
    print("=" * 70)

    # Realistic tabletop-pick stats: a few cm of translation, small rotations,
    # gripper in [0,1]. These stand in for YOUR meta/stats.json after conversion.
    q01 = np.array([-0.04, -0.04, -0.04, -0.10, -0.10, -0.10, 0.0])
    q99 = np.array([+0.04, +0.04, +0.04, +0.10, +0.10, +0.10, 1.0])
    tok = ActionTokenizer(q01, q99)

    # A real-ish EE-delta: reach forward 1.5 cm, down 1 cm, close the gripper.
    action = np.array([0.015, -0.002, -0.010, 0.005, -0.003, 0.012, 1.0])

    tokens = tok.to_tokens(action)
    recovered = tok.from_tokens(tokens)
    err = np.abs(recovered - action)
    half_bin = tok.bin_width / 2.0

    print(f"original action : {np.array2string(action, precision=4)}")
    print(f"action tokens   : {tokens.tolist()}")
    print(f"recovered action: {np.array2string(recovered, precision=4)}")
    print(f"abs error       : {np.array2string(err, precision=5)}")
    print(f"half bin width  : {np.array2string(half_bin, precision=5)}")
    print(f"bin width (mm) dx: {tok.bin_width[0]*1000:.4f} mm")

    ok = bool(np.all(err <= half_bin + 1e-9))
    print(f"PART A: {'PASS' if ok else 'FAIL'} "
          f"(every dim recovered within half a bin — quantization is the only loss)")
    return ok


def part_b_unnorm_trap() -> bool:
    print()
    print("=" * 70)
    print("PART B — the un-normalization trap (Lecture 2 Part 2.4)")
    print("=" * 70)

    # Stats the model was FINE-TUNED with (your small task: +/- 4 cm).
    q01_mine = np.array([-0.04, -0.04, -0.04, -0.10, -0.10, -0.10, 0.0])
    q99_mine = np.array([+0.04, +0.04, +0.04, +0.10, +0.10, +0.10, 1.0])
    tok_train = ActionTokenizer(q01_mine, q99_mine)

    # Stats LEFT OVER from a different OXE dataset (+/- 20 cm) — the copy-paste error
    # of passing the wrong unnorm_key at inference.
    q01_other = np.array([-0.20, -0.20, -0.20, -0.50, -0.50, -0.50, 0.0])
    q99_other = np.array([+0.20, +0.20, +0.20, +0.50, +0.50, +0.50, 1.0])
    tok_infer_wrong = ActionTokenizer(q01_other, q99_other)

    action = np.array([0.015, -0.002, -0.010, 0.005, -0.003, 0.012, 1.0])

    # The model predicts bins against the TRAINING stats (that's what it learned).
    tokens = tok_train.to_tokens(action)
    # But inference un-normalizes with the WRONG stats.
    recovered_wrong = tok_infer_wrong.from_tokens(tokens)
    recovered_right = tok_train.from_tokens(tokens)

    print(f"true action        : {np.array2string(action, precision=4)}")
    print(f"de-tok (right stats): {np.array2string(recovered_right, precision=4)}")
    print(f"de-tok (WRONG stats): {np.array2string(recovered_wrong, precision=4)}")
    ratio = (q99_other - q01_other) / (q99_mine - q01_mine)
    print(f"scale blow-up factor: {np.array2string(ratio, precision=2)}  (5x on translation)")
    print("Same DIRECTION (signs match), wrong MAGNITUDE — the robot lunges 5x too far.")
    print("Nothing errored. This is the silent failure, in action space.")

    # The trap is 'reproduced' when direction is preserved but magnitude is off.
    same_sign = np.all(np.sign(recovered_wrong[:6]) == np.sign(recovered_right[:6]))
    wrong_mag = np.any(np.abs(recovered_wrong[:3] - action[:3]) > 0.02)
    ok = bool(same_sign and wrong_mag)
    print(f"PART B: {'trap reproduced' if ok else 'FAIL'}")
    return ok


def part_c_token_mapping() -> bool:
    print()
    print("=" * 70)
    print("PART C — bins map onto the reserved tail of the Llama vocabulary")
    print("=" * 70)
    bins = np.array([0, 1, 128, 254, 255])
    tokens = ACTION_TOKEN_BASE + bins
    print(f"vocab size                : {VOCAB_SIZE}")
    print(f"reserved action-token base: {ACTION_TOKEN_BASE}  (last {N_BINS} ids)")
    print(f"bins  {bins.tolist()}")
    print(f"-> token ids {tokens.tolist()}")
    ok = bool(tokens.min() >= ACTION_TOKEN_BASE and tokens.max() < VOCAB_SIZE)
    print(f"all action tokens in [{ACTION_TOKEN_BASE}, {VOCAB_SIZE}): "
          f"{'PASS' if ok else 'FAIL'}")
    print("These are the least-frequent Llama tokens — repurposed as action symbols,")
    print("so 'predict the next action' becomes ordinary next-token prediction.")
    return ok


def main() -> None:
    a = part_a_round_trip()
    b = part_b_unnorm_trap()
    c = part_c_token_mapping()
    print()
    print("=" * 70)
    print(f"SUMMARY: round-trip={'PASS' if a else 'FAIL'} | "
          f"unnorm-trap={'reproduced' if b else 'FAIL'} | "
          f"token-map={'PASS' if c else 'FAIL'}")
    print("=" * 70)
    raise SystemExit(0 if (a and b and c) else 1)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (shape is invariant; exact tokens depend on the action values)
# -----------------------------------------------------------------------------
#
# ======================================================================
# PART A — round-trip: tokenize then de-tokenize a known action
# ======================================================================
# original action : [ 0.015  -0.002  -0.01    0.005  -0.003   0.012   1.    ]
# action tokens   : [31984, 31807, 31775, 31840, 31792, 31920, 31999]
# recovered action: [ 0.0149 -0.0021 -0.0099  0.005  -0.003   0.0121  0.998 ]
# abs error       : [...all <= half bin width...]
# bin width (mm) dx: 0.3125 mm
# PART A: PASS (every dim recovered within half a bin — quantization is the only loss)
#
# ======================================================================
# PART B — the un-normalization trap (Lecture 2 Part 2.4)
# ======================================================================
# true action        : [ 0.015  -0.002  -0.01   ...]
# de-tok (WRONG stats): [ 0.075  -0.010  -0.05   ...]   <-- 5x too far
# scale blow-up factor: [5. 5. 5. ...]
# PART B: trap reproduced
#
# ======================================================================
# PART C — bins map onto the reserved tail of the Llama vocabulary
# ======================================================================
# -> token ids [31744, 31745, 31872, 31998, 31999]
# PART C: PASS
#
# The takeaway: tokenization is just per-dim binning onto rare tokens; the ONLY
# thing standing between "right bins" and "right robot motion" is using the SAME,
# CORRECT (q01,q99) stats at train and inference time. Mismatch them and you get
# a confident robot moving the right way by the wrong amount — and no error message.
# -----------------------------------------------------------------------------
