#!/usr/bin/env python3
# Exercise 2 -- The README scorer.
#
# Goal: check a portfolio README against the senior bar from Lecture 2 section 1 --
#       a what-and-why paragraph at the TOP, an architecture diagram, a runnable
#       quickstart, results WITH NUMBERS, and an honest limitations section. The
#       lesson: a reviewer reads your README in 90 seconds; this tool catches the
#       gaps before they do.
#
# Estimated time: 40 minutes. Runnable. Pure Python -- no dependencies.
#
# HOW TO USE THIS FILE
#   python3 exercise-02-readme-scorer.py                  # scores the built-in good/bad samples
#   python3 exercise-02-readme-scorer.py path/to/README.md  # score YOUR readme
#
#   Run it on all THREE flagship READMEs (perception cycle, policy stack, capstone).
#
# ACCEPTANCE CRITERIA
#   [ ] The scorer rewards: a what-and-why paragraph BEFORE the first install step,
#       an architecture diagram (Mermaid or image), a quickstart, NUMERIC results,
#       and a limitations section.
#   [ ] The "bad" sample (install-dump README) scores low; the "good" sample passes.
#   [ ] You run it on your own READMEs and record the scores.
#   [ ] `python3 exercise-02-readme-scorer.py` prints ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import re
import sys

PASS_THRESHOLD = 70  # out of 100


def score_readme(text: str) -> tuple[int, list[str]]:
    """Score a README against the senior bar. Returns (score, findings)."""
    findings: list[str] = []
    score = 0
    lines = [ln.rstrip() for ln in text.splitlines()]
    lower = text.lower()

    # 1. What-and-why paragraph BEFORE the first install/usage heading (25 pts).
    #    Find the first H1, then the first prose paragraph, then the first install heading.
    first_install_idx = _first_heading_index(
        lines, ("install", "installation", "setup", "getting started", "build", "quickstart")
    )
    intro_para = _first_prose_paragraph_after_title(lines)
    if intro_para and (first_install_idx is None or intro_para[0] < first_install_idx):
        # Reward a substantive paragraph (not a one-liner badge row).
        words = len(intro_para[1].split())
        if words >= 25:
            score += 25
        else:
            score += 10
            findings.append("What-and-why paragraph is short (<25 words) -- expand it.")
    else:
        findings.append("MISSING: a what-and-why paragraph before the first install/setup section.")

    # 2. Architecture diagram -- Mermaid fenced block or an image (20 pts).
    has_mermaid = "```mermaid" in lower or "flowchart" in lower
    has_image = bool(re.search(r"!\[[^\]]*\]\([^)]+\.(png|svg|jpg|jpeg)\)", lower))
    if has_mermaid or has_image:
        score += 20
    else:
        findings.append("MISSING: an architecture diagram (Mermaid block or image).")

    # 3. A quickstart / runnable commands (20 pts).
    has_quickstart_heading = _first_heading_index(
        lines, ("quickstart", "usage", "run", "getting started", "how to run")
    ) is not None
    has_code_block = "```" in text
    if has_quickstart_heading and has_code_block:
        score += 20
    elif has_code_block:
        score += 10
        findings.append("Has commands but no clear Quickstart/Usage heading -- add one.")
    else:
        findings.append("MISSING: a quickstart with runnable commands.")

    # 4. Results WITH NUMBERS (20 pts). Look for digits near a results section, or
    #    common metric tokens (ms, fps, mAP, %, m, p95).
    has_results_heading = _first_heading_index(lines, ("result", "results", "evaluation", "benchmarks")) is not None
    metric_tokens = re.findall(r"\b\d+(?:\.\d+)?\s?(ms|fps|map|%|m\b|p95|p99|hz)", lower)
    if has_results_heading and metric_tokens:
        score += 20
    elif metric_tokens:
        score += 12
        findings.append("Has numbers but no Results heading -- group them under one.")
    else:
        findings.append("MISSING: results WITH NUMBERS (a reviewer wants metrics, not 'works well').")

    # 5. Limitations section -- the senior tell (15 pts).
    has_limitations = _first_heading_index(
        lines, ("limitation", "limitations", "known issues", "what this doesn't do", "caveats")
    ) is not None
    if has_limitations:
        score += 15
    else:
        findings.append("MISSING: a limitations section -- its absence signals a junior README.")

    return score, findings


def _first_heading_index(lines: list[str], keywords: tuple[str, ...]) -> int | None:
    for i, ln in enumerate(lines):
        if ln.startswith("#"):
            h = ln.lstrip("#").strip().lower()
            if any(k in h for k in keywords):
                return i
    return None


def _first_prose_paragraph_after_title(lines: list[str]) -> tuple[int, str] | None:
    """Return (line_index, paragraph_text) of the first non-heading, non-badge prose
    paragraph after the first H1."""
    started = False
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            started = True
            continue
        if not started:
            continue
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        # Skip badge rows / pure-link lines.
        if s.startswith("![") or s.startswith("[!") or s.startswith("|"):
            continue
        return (i, s)
    return None


GOOD = """# The 30-ms Perception Cycle

A fused, real-time perception node for a mobile manipulator: it takes IMU, 2D LiDAR,
and RGB-D, runs an EKF state estimate and a TensorRT-INT8 object detector, and
publishes detected objects in the map frame inside a 50 ms cycle on a Jetson Orin
Nano. Built for the C24 capstone, where the grasp policy needs fresh fused perception.

## Architecture

```mermaid
flowchart LR
    IMU & LIDAR & CAM --> EKF & DET --> FUSE --> OUT
```

## Quickstart

```bash
ros2 launch crunchbot_perception perception.launch.py
```

## Results

- End-to-end cycle: 44 ms p95 on Orin Nano (15 W).
- Detector: 11.6 ms, mAP@0.5 0.498 (INT8, -1.4 pts vs FP16).
- Drift: < 0.5 m over 20 m.

## Limitations

Camera-only degraded mode is validated to 0.3 m/s in a known map, not in unmapped
clutter. INT8 calibration is warehouse-domain; re-calibrate for other environments.
"""

BAD = """# perception_pkg

## Installation

```bash
pip install -r requirements.txt
colcon build
```

## Usage

Run the node. It does perception. Works well in our tests.
"""


def self_check() -> bool:
    ok = True
    good_score, good_findings = score_readme(GOOD)
    bad_score, bad_findings = score_readme(BAD)

    print(f"GOOD sample: {good_score}/100", "PASS" if good_score >= PASS_THRESHOLD else "FAIL")
    print(f"BAD  sample: {bad_score}/100", "PASS" if bad_score >= PASS_THRESHOLD else "FAIL")
    print(f"  bad README findings: {len(bad_findings)}")
    for f in bad_findings:
        print(f"    - {f}")

    if good_score < PASS_THRESHOLD:
        print("CHECK FAILED: the good sample should pass.")
        ok = False
    if bad_score >= PASS_THRESHOLD:
        print("CHECK FAILED: the install-dump README should NOT pass.")
        ok = False
    return ok


def main(argv: list[str]) -> int:
    if len(argv) >= 1:
        path = argv[0]
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            print(f"Could not read {path}: {e}")
            return 1
        score, findings = score_readme(text)
        print(f"{path}: {score}/100", "PASS" if score >= PASS_THRESHOLD else "FAIL")
        for f in findings:
            print(f"  - {f}")
        return 0 if score >= PASS_THRESHOLD else 1

    print("=" * 56)
    print("README scorer -- senior bar (Lecture 2 section 1)")
    print("=" * 56)
    if self_check():
        print("-" * 56)
        print("ALL CHECKS PASSED")
        print("Now run it on YOUR three READMEs:")
        print("  python3 exercise-02-readme-scorer.py path/to/README.md")
        return 0
    print("CHECKS FAILED -- see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT (no args):
#
#   ========================================================
#   README scorer -- senior bar (Lecture 2 section 1)
#   ========================================================
#   GOOD sample: 85/100 PASS   (exact value depends on metric-token matching)
#   BAD  sample: 20/100 FAIL
#     bad README findings: 4
#       - MISSING: a what-and-why paragraph before the first install/setup section.
#       - MISSING: an architecture diagram (Mermaid block or image).
#       - MISSING: results WITH NUMBERS (a reviewer wants metrics, not 'works well').
#       - MISSING: a limitations section -- its absence signals a junior README.
#   --------------------------------------------------------
#   ALL CHECKS PASSED
#   Now run it on YOUR three READMEs: ...
#
# The takeaway: the install-dump README fails because it opens with setup instead of
# what-and-why, has no diagram, no numbers, and no limitations. The senior README
# passes because it answers the reviewer's questions in the order they have them.
# ---------------------------------------------------------------------------
