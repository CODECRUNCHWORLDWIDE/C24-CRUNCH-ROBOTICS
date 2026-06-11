#!/usr/bin/env python3
# Exercise 2 — Implement a domain-randomization config + sampler
#
# Goal: Build the simulator-independent core of domain randomization: a seedable
#       sampler that draws ONE fresh world per episode from a declarative config, and
#       validate that every sampled value stays inside its declared range. This is the
#       piece you wire into Isaac Lab's event manager (Path A) or Gymnasium reset
#       (Path B) — the policy never sees it, which is why it's portable.
#
# Estimated time: 60 minutes. Runnable. Pure NumPy — no GPU, no simulator.
#
# WHAT THIS FILE DOES
#
#   1. Defines a randomization CONFIG (the Lecture 2 Part 1.1 structure): named params,
#      each with a sampling distribution (uniform / normal / log_uniform / choice).
#   2. Implements DomainRandomizer.sample() -> one fresh set of world parameters.
#   3. VALIDATES the sampler over many draws:
#        * every numeric sample lies within its declared range (the silent-bug guard),
#        * reproducibility: same seed -> same draws,
#        * coverage: over many draws the samples actually SPAN the range (a sampler
#          stuck at the nominal isn't randomizing anything).
#
# HOW TO USE THIS FILE
#
#       python3 exercise-02-domain-randomization-config.py
#
#   It runs the validation suite and prints PASS/FAIL per check, then prints one
#   example sampled world so you can see what a single episode's randomization is.
#
# ACCEPTANCE CRITERIA
#
#   [ ] All numeric samples stay within their declared ranges over 10000 draws -> PASS.
#   [ ] Same seed reproduces the same sequence of draws -> PASS.
#   [ ] Samples span their ranges (min near low, max near high) -> PASS.
#   [ ] You can state why "sample fresh, per episode" matters vs. fixing the world.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import numpy as np

# A randomization config for a grasp task (Exercise 1 Part A). In real use this would
# be loaded from randomization.yaml; inline here so the file is standalone.
CONFIG = {
    "visual": {
        "table_texture":   {"dist": "choice", "options": ["wood", "metal", "tile", "marble", "noise"]},
        "light_intensity": {"dist": "uniform", "low": 400.0, "high": 1400.0},
        "camera_yaw_deg":  {"dist": "uniform", "low": -8.0, "high": 8.0},
    },
    "dynamics": {
        "object_x":       {"dist": "uniform", "low": 0.35, "high": 0.45},
        "floor_friction": {"dist": "uniform", "low": 0.4, "high": 1.2},     # nominal ~0.8
        "object_mass_kg": {"dist": "uniform", "low": 0.05, "high": 0.25},   # nominal ~0.15
        "joint_damping":  {"dist": "log_uniform", "low": 0.01, "high": 0.5},
        "motor_gain":     {"dist": "uniform", "low": 0.8, "high": 1.2},     # +/-20%
    },
    "sensor": {
        "imu_gyro_noise": {"dist": "normal", "mean": 0.0, "std": 0.01},
    },
    "latency": {
        "action_delay_ms": {"dist": "uniform", "low": 0.0, "high": 50.0},
    },
}


class DomainRandomizer:
    """Samples a fresh set of world parameters from the config, per episode/env.

    Seedable for reproducibility (you MUST be able to re-run a randomized training).
    The sampler is decoupled from any simulator — applying the sampled params to the
    world is the sim-specific step (Isaac event manager / Gz reset), done elsewhere.
    """

    def __init__(self, config: dict, seed: int = 0) -> None:
        self.config = config
        self.rng = np.random.default_rng(seed)

    def sample(self) -> dict:
        params = {}
        for family, entries in self.config.items():
            for name, spec in entries.items():
                params[f"{family}.{name}"] = self._draw(spec)
        return params

    def _draw(self, spec: dict):
        dist = spec["dist"]
        if dist == "uniform":
            return float(self.rng.uniform(spec["low"], spec["high"]))
        if dist == "normal":
            return float(self.rng.normal(spec["mean"], spec["std"]))
        if dist == "log_uniform":
            lo, hi = np.log(spec["low"]), np.log(spec["high"])
            return float(np.exp(self.rng.uniform(lo, hi)))
        if dist == "choice":
            return str(self.rng.choice(spec["options"]))
        raise ValueError(f"unknown dist {dist!r}")


def _numeric_specs(config: dict):
    """Yield (key, spec) for every numeric (range-bounded) parameter."""
    for family, entries in config.items():
        for name, spec in entries.items():
            if spec["dist"] in ("uniform", "log_uniform"):
                yield f"{family}.{name}", spec


def check_in_range(config: dict, n: int = 10000) -> bool:
    """Every numeric sample must lie within its declared [low, high]."""
    r = DomainRandomizer(config, seed=1)
    bounds = {k: (s["low"], s["high"]) for k, s in _numeric_specs(config)}
    ok = True
    for _ in range(n):
        params = r.sample()
        for k, (lo, hi) in bounds.items():
            v = params[k]
            if not (lo - 1e-9 <= v <= hi + 1e-9):
                print(f"  [FAIL] {k}={v} outside [{lo}, {hi}]")
                ok = False
                break
        if not ok:
            break
    print(f"  in-range over {n} draws: {'PASS' if ok else 'FAIL'}")
    return ok


def check_reproducible(config: dict) -> bool:
    """Same seed -> identical draw sequence."""
    a = DomainRandomizer(config, seed=42)
    b = DomainRandomizer(config, seed=42)
    seqs_match = all(a.sample() == b.sample() for _ in range(50))
    print(f"  reproducible (same seed): {'PASS' if seqs_match else 'FAIL'}")
    return seqs_match


def check_coverage(config: dict, n: int = 5000) -> bool:
    """Over many draws, uniform params should span most of their range.

    A sampler stuck near the nominal isn't randomizing — this catches that.
    """
    r = DomainRandomizer(config, seed=7)
    seen = {k: [] for k, _ in _numeric_specs(config) if _["dist"] == "uniform"}
    bounds = {k: (s["low"], s["high"]) for k, s in _numeric_specs(config)
              if s["dist"] == "uniform"}
    for _ in range(n):
        p = r.sample()
        for k in seen:
            seen[k].append(p[k])
    ok = True
    for k, (lo, hi) in bounds.items():
        span = hi - lo
        lo_seen, hi_seen = min(seen[k]), max(seen[k])
        # Expect to have sampled within 10% of each end given 5000 draws.
        covers = (lo_seen - lo) < 0.1 * span and (hi - hi_seen) < 0.1 * span
        if not covers:
            print(f"  [FAIL] {k} only spanned [{lo_seen:.3f}, {hi_seen:.3f}] "
                  f"of [{lo}, {hi}]")
            ok = False
    print(f"  coverage (samples span the range): {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> None:
    print("=" * 64)
    print("DOMAIN-RANDOMIZER VALIDATION")
    print("=" * 64)
    a = check_in_range(CONFIG)
    b = check_reproducible(CONFIG)
    c = check_coverage(CONFIG)

    print("\nexample sampled world (one episode's randomization):")
    r = DomainRandomizer(CONFIG, seed=123)
    for k, v in r.sample().items():
        vs = f"{v:.4f}" if isinstance(v, float) else v
        print(f"  {k:28s} = {vs}")

    print()
    print("=" * 64)
    ok = a and b and c
    print(f"VALIDATION: {'ALL PASS' if ok else 'FAILED'}")
    print("=" * 64)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (shape is invariant; the example world depends on the seed)
# -----------------------------------------------------------------------------
#
# ================================================================
# DOMAIN-RANDOMIZER VALIDATION
# ================================================================
#   in-range over 10000 draws: PASS
#   reproducible (same seed): PASS
#   coverage (samples span the range): PASS
#
# example sampled world (one episode's randomization):
#   visual.table_texture         = tile
#   visual.light_intensity       = 9xx.xxxx
#   visual.camera_yaw_deg        = -x.xxxx
#   dynamics.object_x            = 0.4xxx
#   dynamics.floor_friction      = 0.xxxx
#   dynamics.object_mass_kg      = 0.1xxx
#   dynamics.joint_damping       = 0.0xxx
#   dynamics.motor_gain          = 1.0xxx
#   sensor.imu_gyro_noise        = 0.00xx
#   latency.action_delay_ms      = 2x.xxxx
#
# ================================================================
# VALIDATION: ALL PASS
# ================================================================
#
# The point: this sampler is the SIMULATOR-INDEPENDENT core of domain randomization.
# Per episode you draw one of these dicts and apply it to the world; the policy never
# sees the sampler. "Sample fresh, per episode" is what stops the policy overfitting
# to any single world — fix the world and you have domains, not randomization.
# -----------------------------------------------------------------------------
