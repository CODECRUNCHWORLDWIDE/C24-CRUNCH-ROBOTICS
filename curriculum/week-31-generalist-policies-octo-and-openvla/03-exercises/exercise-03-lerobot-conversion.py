#!/usr/bin/env python3
# Exercise 3 — Convert your Week 29 demos into a LeRobotDataset
#
# Goal: Turn your raw teleop trajectories into the LeRobot on-disk format that the
#       OpenVLA fine-tuner consumes, compute the per-dimension stats (the q01/q99 that
#       become OpenVLA's action tokenizer — Lecture 2 Part 1.2), and VALIDATE that the
#       schema is exactly what fine-tuning expects. The boring load-bearing step of
#       VLA work: garbage-in here is garbage-out everywhere downstream.
#
# Estimated time: 60 minutes. Runnable.
#
# WHAT THIS FILE DOES
#
#   1. Loads your Week 29 demos (a directory of .npz episodes — adapt the loader to
#      your collector's format; the EXPECTED schema is documented in load_demos()).
#   2. Converts each episode into LeRobot frames, ENSURING the action is the 7-D
#      EE-delta (dx,dy,dz,droll,dpitch,dyaw,grip). If your demos stored ABSOLUTE poses
#      or JOINT commands, the to_ee_delta() helper shows where you convert (you MUST).
#   3. Writes a LeRobotDataset, consolidates it (computes meta/stats.json), and
#      validates: feature shapes, action dimensionality, and that stats are non-degenerate.
#
# HOW TO USE THIS FILE
#
#       pip install lerobot
#       python3 exercise-03-lerobot-conversion.py \
#           --demos /path/to/week29_demos --out /data/lerobot --task "pick up the red cube"
#
#   If lerobot isn't installed OR --demos is omitted, the script runs in --self-test
#   mode: it SYNTHESIZES three tiny fake episodes, runs the same validation logic on
#   them WITHOUT writing a real dataset, and prints PASS — so you can verify the
#   conversion/validation logic before you have the real library and data.
#
# ACCEPTANCE CRITERIA
#
#   [ ] With real demos + lerobot: a LeRobotDataset is written under --out, with
#       observation.images.*, observation.state, and a 7-D action feature.
#   [ ] meta/stats.json exists and the action q01/q99 are NON-degenerate on the moving
#       dimensions (a dimension that never moves is flagged, not silently zero-width).
#   [ ] validate_schema() prints "SCHEMA OK" and the script exits 0.
#   [ ] You can state why the action MUST be an EE-delta and not a joint command.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import numpy as np

ACTION_DIM = 7
ACTION_LABELS = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "grip"]
IMG_HW = (256, 256)


@dataclass
class Episode:
    """One demonstration. images: [T,H,W,3] uint8; state: [T,7]; action: [T,7] EE-delta."""
    images: np.ndarray
    state: np.ndarray
    action: np.ndarray
    instruction: str


def to_ee_delta(raw_action: np.ndarray, action_kind: str) -> np.ndarray:
    """Convert your collector's action to the 7-D EE-delta OpenVLA expects.

    This is the conversion the whole week hinges on (Lecture 1 Part 1.2, Lecture 2
    Part 1.3). OpenVLA's action space is a 6-DOF END-EFFECTOR POSE DELTA plus a 1-DOF
    gripper command. If you collected something else, convert it HERE.

    action_kind:
      "ee_delta"  -> already correct, pass through.
      "ee_abs"    -> absolute EE poses; difference consecutive poses to get deltas.
                     (For full rigor, difference orientations via the SE(3) log-map;
                     small-angle euler differencing is acceptable for tabletop deltas.)
      "joint"     -> joint commands; you CANNOT feed these to OpenVLA. Run forward
                     kinematics (Week 23) to EE poses, then difference. This is real work.
    """
    if action_kind == "ee_delta":
        return np.asarray(raw_action, dtype=np.float32)
    if action_kind == "ee_abs":
        # Deltas between consecutive absolute poses. For rotations a proper SE(3)
        # log-map is correct; linear differencing of small-angle euler is acceptable
        # for tabletop deltas. Prepend a zero delta for the first frame.
        a = np.asarray(raw_action, dtype=np.float32)
        deltas = np.zeros_like(a)
        deltas[1:] = a[1:] - a[:-1]
        return deltas
    if action_kind == "joint":
        raise ValueError(
            "Joint-command demos cannot feed OpenVLA directly. Run FK (Week 23) to "
            "end-effector poses, then convert to deltas. OpenVLA's action space is "
            "EE-delta, not joint space — see Lecture 1 Part 1.2."
        )
    raise ValueError(f"unknown action_kind={action_kind!r}")


def load_demos(demos_dir: str, action_kind: str, instruction: str) -> list[Episode]:
    """Load .npz episodes. Adapt to YOUR collector's keys.

    Expected per-episode .npz keys (rename to match your Week 29 collector):
        images : uint8  [T, H, W, 3]
        state  : float  [T, 7]   (proprioception: EE pose + gripper, your choice)
        action : float  [T, A]   (A=7 if ee_delta; otherwise converted by to_ee_delta)
    """
    import glob
    import os

    episodes: list[Episode] = []
    paths = sorted(glob.glob(os.path.join(demos_dir, "*.npz")))
    if not paths:
        raise FileNotFoundError(f"no .npz episodes in {demos_dir}")
    for p in paths:
        z = np.load(p)
        images = z["images"].astype(np.uint8)
        state = z["state"].astype(np.float32)
        action = to_ee_delta(z["action"], action_kind)
        if action.shape[1] != ACTION_DIM:
            raise ValueError(f"{p}: action dim {action.shape[1]} != {ACTION_DIM}")
        episodes.append(Episode(images, state, action, instruction))
    return episodes


def synth_demos(n: int = 3, length: int = 20) -> list[Episode]:
    """Self-test data: tiny fake episodes with realistic EE-delta ranges."""
    rng = np.random.default_rng(7)
    eps: list[Episode] = []
    for _ in range(n):
        images = rng.integers(0, 255, (length, *IMG_HW, 3), dtype=np.uint8)
        state = rng.normal(0, 0.05, (length, 7)).astype(np.float32)
        # Realistic small EE-deltas; gripper closes over the episode.
        action = rng.normal(0, 0.01, (length, 7)).astype(np.float32)
        action[:, 6] = np.linspace(0.0, 1.0, length)  # gripper open->close
        eps.append(Episode(images, state, action, "pick up the red cube"))
    return eps


def compute_stats(episodes: list[Episode]) -> dict:
    """Per-dimension action stats — the q01/q99 that become OpenVLA's bins.

    LeRobot's consolidate() computes the real thing into meta/stats.json; this mirrors
    the action part so we can validate it without the library in self-test mode.
    """
    all_actions = np.concatenate([e.action for e in episodes], axis=0)
    q01 = np.percentile(all_actions, 1, axis=0)
    q99 = np.percentile(all_actions, 99, axis=0)
    return {
        "mean": all_actions.mean(0),
        "std": all_actions.std(0),
        "q01": q01,
        "q99": q99,
        "n_frames": all_actions.shape[0],
    }


def validate_schema(episodes: list[Episode], stats: dict) -> bool:
    """Validate the conversion is fine-tune-ready. Returns True if OK."""
    print("-" * 64)
    print("VALIDATION")
    print("-" * 64)
    ok = True

    # 1. Action dimensionality.
    if all(e.action.shape[1] == ACTION_DIM for e in episodes):
        print(f"  [ok]  every episode action is {ACTION_DIM}-D (EE-delta)")
    else:
        print("  [FAIL] some episode action is not 7-D — OpenVLA needs the EE-delta")
        ok = False

    # 2. Image dtype/shape.
    if all(e.images.dtype == np.uint8 and e.images.shape[1:3] == IMG_HW for e in episodes):
        print(f"  [ok]  images are uint8 {IMG_HW}")
    else:
        print("  [FAIL] image dtype/shape wrong — expected uint8 HxWx3")
        ok = False

    # 3. Non-degenerate stats on moving dimensions (the un-norm-trap guard).
    span = stats["q99"] - stats["q01"]
    for i, label in enumerate(ACTION_LABELS):
        if span[i] < 1e-6:
            print(f"  [warn] dim '{label}' never moves in the data (q01==q99). "
                  f"OpenVLA will assign it ~0 range — fine for a constant gripper, "
                  f"a bug if you expected motion there.")
    moving = span[:6]  # the 6 pose dims should move in a real pick
    if np.any(moving > 1e-4):
        print(f"  [ok]  pose dimensions have non-degenerate q01/q99 ranges")
    else:
        print("  [FAIL] no pose dimension moves — did you feed all-zero actions?")
        ok = False

    print()
    print("  action stats (these become OpenVLA's 256-bin edges):")
    for i, label in enumerate(ACTION_LABELS):
        print(f"    {label:7s} q01={stats['q01'][i]:+.4f}  q99={stats['q99'][i]:+.4f}  "
              f"bin_width={(span[i]/256):.6f}")
    print(f"  total frames: {stats['n_frames']}  episodes: {len(episodes)}")
    print()
    print(f"  SCHEMA {'OK' if ok else 'FAILED'}")
    return ok


def write_lerobot(episodes: list[Episode], out_dir: str, repo_id: str, fps: int) -> None:
    """Write a real LeRobotDataset. Requires `pip install lerobot`."""
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset

    ds = LeRobotDataset.create(
        repo_id=repo_id,
        fps=fps,
        root=out_dir,
        features={
            "observation.images.wrist": {
                "dtype": "image", "shape": (*IMG_HW, 3),
                "names": ["height", "width", "channel"],
            },
            "observation.state": {"dtype": "float32", "shape": (7,), "names": ["state"]},
            "action": {"dtype": "float32", "shape": (7,), "names": ["action"]},
        },
    )
    for ep in episodes:
        for t in range(len(ep.action)):
            ds.add_frame({
                "observation.images.wrist": ep.images[t],
                "observation.state": ep.state[t],
                "action": ep.action[t],
                "task": ep.instruction,
            })
        ds.save_episode()
    # consolidate() computes meta/stats.json — the normalization stats. DO NOT SKIP.
    ds.consolidate()
    print(f"  wrote LeRobotDataset to {out_dir} (repo_id={repo_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Week 29 demos to LeRobot.")
    parser.add_argument("--demos", default=None, help="dir of .npz episodes")
    parser.add_argument("--out", default="/data/lerobot", help="output dataset dir")
    parser.add_argument("--repo-id", default="crunch/week29_pick_red_cube")
    parser.add_argument("--task", default="pick up the red cube")
    parser.add_argument("--action-kind", default="ee_delta",
                        choices=["ee_delta", "ee_abs", "joint"])
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--self-test", action="store_true",
                        help="run validation on synthetic data, no library/data needed")
    args = parser.parse_args()

    self_test = args.self_test or args.demos is None
    if self_test:
        print("[self-test] no --demos given; using synthetic episodes, no write.\n")
        episodes = synth_demos()
    else:
        episodes = load_demos(args.demos, args.action_kind, args.task)

    stats = compute_stats(episodes)
    ok = validate_schema(episodes, stats)

    if not self_test and ok:
        try:
            write_lerobot(episodes, args.out, args.repo_id, args.fps)
        except ImportError:
            print("\n  lerobot not installed — `pip install lerobot` to write the dataset.")
            print("  (Validation above still confirms your conversion is correct.)")

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--self-test / no --demos)
# -----------------------------------------------------------------------------
#
# [self-test] no --demos given; using synthetic episodes, no write.
#
# ----------------------------------------------------------------
# VALIDATION
# ----------------------------------------------------------------
#   [ok]  every episode action is 7-D (EE-delta)
#   [ok]  images are uint8 (256, 256)
#   [ok]  pose dimensions have non-degenerate q01/q99 ranges
#
#   action stats (these become OpenVLA's 256-bin edges):
#     dx      q01=-0.0xxx  q99=+0.0xxx  bin_width=0.0000xx
#     ...
#     grip    q01=+0.00xx  q99=+0.99xx  bin_width=0.00xxxx
#   total frames: 60  episodes: 3
#
#   SCHEMA OK
#
# With real --demos and lerobot installed, you ALSO get:
#   wrote LeRobotDataset to /data/lerobot (repo_id=crunch/week29_pick_red_cube)
# and meta/stats.json now holds the action q01/q99 that OpenVLA's fine-tuner reads.
# -----------------------------------------------------------------------------
