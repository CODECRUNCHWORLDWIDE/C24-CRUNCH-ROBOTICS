#!/usr/bin/env python3
# Exercise 3 — Hazard log + FMEA generator (YAML -> Markdown)
#
# Goal: Make your hazard log and FMEA a VERSIONED, REGENERATED artifact instead
#       of a stale spreadsheet. This tool loads hazard-log and FMEA rows from a
#       YAML file, computes:
#         * hazard risk rating  = Severity x Probability x Exposure  (banded)
#         * FMEA RPN            = Severity x Occurrence x Detection
#       applies a criticality cutoff (high RPN OR catastrophic severity),
#       sorts by criticality, and emits a Markdown section you paste straight
#       into your safety case. Commit the YAML; regenerate the Markdown on
#       every commit. That is the senior-engineer outcome of the week.
#
# Estimated time: 50 minutes.
#
# HOW TO USE THIS FILE
#   1. Fill in the TODOs (risk math, banding, criticality, sorting).
#   2. Run the self-test (uses an embedded sample, no external file needed):
#
#         python3 exercise-03-hazard-log-fmea.py --selftest
#
#      Correct implementation prints:  SELFTEST PASSED
#   3. Write your own rows in YAML and generate your safety-case tables:
#
#         python3 exercise-03-hazard-log-fmea.py --write-sample safety.yaml
#         python3 exercise-03-hazard-log-fmea.py safety.yaml > safety-tables.md
#
# ACCEPTANCE CRITERIA
#   [ ] All TODOs implemented; `--selftest` prints SELFTEST PASSED.
#   [ ] A hazard with S/P/E all maxed bands as INTOLERABLE.
#   [ ] An FMEA row with severity 10 is flagged CRITICAL even at low RPN.
#   [ ] Output Markdown has hazards sorted by risk desc, FMEA by RPN desc.
#
# Hints at the bottom. Don't peek for 15 minutes.

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import yaml


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hazard:
    hid: str
    hazard: str
    event: str
    energy: str
    harm: str
    severity: int        # 1..4  (1 negligible .. 4 catastrophic)
    probability: int     # 1..4  (1 remote .. 4 frequent)
    exposure: int        # 1..3  (1 rare .. 3 continuous)
    mitigations: str
    residual: str

    @property
    def risk(self) -> int:
        """Risk = Severity x Probability x Exposure. Range 1..48."""
        # TODO: return the product of the three factors.
        raise NotImplementedError

    @property
    def band(self) -> str:
        """Band the risk score into Low / Medium / High / Intolerable.

        Cutoffs (inclusive lower bound):
            >= 25 -> INTOLERABLE
            >= 12 -> HIGH
            >= 5  -> MEDIUM
            else  -> LOW
        """
        # TODO: implement the banding with the cutoffs above.
        raise NotImplementedError


@dataclass(frozen=True)
class FmeaRow:
    item: str
    failure_mode: str
    effect: str
    cause: str
    controls: str
    severity: int        # 1..10
    occurrence: int      # 1..10
    detection: int       # 1..10 (10 = undetectable)

    @property
    def rpn(self) -> int:
        """RPN = S x O x D. Range 1..1000."""
        # TODO: return the product.
        raise NotImplementedError

    def is_critical(self, rpn_cut: int = 100, sev_cut: int = 9) -> bool:
        """Critical if RPN >= rpn_cut OR severity >= sev_cut.

        The severity gate is the important one: a failure that can kill is
        critical even at a low (optimistic) occurrence guess. You do not get
        to multiply your way out of a fatality.
        """
        # TODO: return True if either condition holds.
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load(path: str) -> tuple[list[Hazard], list[FmeaRow]]:
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return _parse(doc)


def _parse(doc: dict) -> tuple[list[Hazard], list[FmeaRow]]:
    hazards = [Hazard(**row) for row in doc.get("hazards", [])]
    fmea = [FmeaRow(**row) for row in doc.get("fmea", [])]
    return hazards, fmea


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(hazards: list[Hazard], fmea: list[FmeaRow]) -> str:
    out: list[str] = []

    out.append("## Hazard log\n")
    out.append("| ID | Hazard | Energy | Worst harm | S | P | E | Risk | Band | Mitigations | Residual |")
    out.append("|----|--------|--------|------------|---|---|---|-----:|------|-------------|----------|")
    # TODO: sort hazards by risk DESCENDING, then emit one table row each.
    #       Use the format string below for each row `h`:
    #   f"| {h.hid} | {h.hazard} | {h.energy} | {h.harm} | {h.severity} | "
    #   f"{h.probability} | {h.exposure} | {h.risk} | {h.band} | "
    #   f"{h.mitigations} | {h.residual} |"
    for h in []:  # TODO: replace [] with the sorted hazards
        out.append("")  # TODO: replace with the formatted row

    out.append("\n## FMEA\n")
    out.append("| Item | Failure mode | Effect | Cause | Controls | S | O | D | RPN | Critical |")
    out.append("|------|--------------|--------|-------|----------|---|---|---|----:|:--------:|")
    # TODO: sort fmea by RPN DESCENDING, then emit one row each.
    #       Critical column is "YES" if r.is_critical() else "".
    for r in []:  # TODO: replace [] with the sorted fmea rows
        out.append("")  # TODO: replace with the formatted row

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# A realistic embedded sample (also written by --write-sample)
# ---------------------------------------------------------------------------

SAMPLE = {
    "hazards": [
        {
            "hid": "HZ-01",
            "hazard": "Base in motion strikes/runs over a person",
            "event": "Pedestrian enters the base's planned path",
            "energy": "Kinetic energy of base",
            "harm": "Impact to shin / foot crush",
            "severity": 3, "probability": 3, "exposure": 3,
            "mitigations": "Speed gate 0.25 m/s near person; collision monitor; SW + HW E-stop",
            "residual": "Low-speed contact only; accepted (see residual risk)",
        },
        {
            "hid": "HZ-07",
            "hazard": "Arm strikes a bystander reaching into the workspace",
            "event": "Hand enters arm swept volume during a pick",
            "energy": "Kinetic energy of arm",
            "harm": "Blunt impact to hand/head",
            "severity": 3, "probability": 3, "exposure": 2,
            "mitigations": "TCP speed limit; ISO/TS 15066 force limit; confidence gate; SW + HW E-stop",
            "residual": "Contact below 15066 forearm threshold; accepted",
        },
        {
            "hid": "HZ-09",
            "hazard": "Policy grasps a sharp/dangerous object on a mis-grounded instruction",
            "event": "VLA grounds 'knife' and transports it toward a person",
            "energy": "Kinetic energy of arm + sharp object",
            "harm": "Laceration",
            "severity": 4, "probability": 2, "exposure": 2,
            "mitigations": "Object allowlist; confidence gate; classical fallback veto; operator confirm",
            "residual": "Sharp-object grasps blocked by allowlist; accepted",
        },
        {
            "hid": "HZ-14",
            "hazard": "Arm falls under gravity on motor power loss",
            "event": "Power brown-out while arm is extended",
            "energy": "Potential energy of arm",
            "harm": "Arm drops onto a person/surface below",
            "severity": 3, "probability": 2, "exposure": 1,
            "mitigations": "Brake-on-power-loss verified each pre-flight; arm holds without power",
            "residual": "Arm holds on power loss; accepted",
        },
    ],
    "fmea": [
        {
            "item": "Safety filter (classical fallback)",
            "failure_mode": "Fails to engage when the learned policy is unsafe",
            "effect": "Unsafe policy action reaches actuators; possible person contact",
            "cause": "Filter subscribed to a topic the policy bypasses under load",
            "controls": "BT reactive sequence pre-empts; HW E-stop independent",
            "severity": 10, "occurrence": 3, "detection": 7,
        },
        {
            "item": "3D LiDAR",
            "failure_mode": "Stops publishing (USB driver drop)",
            "effect": "Costmap goes stale; planner trusts old free space",
            "cause": "USB power dip under vibration",
            "controls": "Watchdog on /scan deadline; costmap clears on stale data",
            "severity": 8, "occurrence": 4, "detection": 3,
        },
        {
            "item": "EKF / robot_localization",
            "failure_mode": "Covariance diverges; confident-but-wrong pose",
            "effect": "Robot acts on a wrong belief about where it is",
            "cause": "IMU bias drift + covariance underflow",
            "controls": "Pose covariance threshold gate; AMCL cross-check",
            "severity": 7, "occurrence": 3, "detection": 6,
        },
        {
            "item": "Arm joint brake",
            "failure_mode": "Brake fails to engage on power loss",
            "effect": "Arm falls under gravity",
            "cause": "Brake solenoid wear",
            "controls": "Pre-flight brake-on-power-loss check",
            "severity": 9, "occurrence": 2, "detection": 2,
        },
    ],
}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _selftest() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    hazards, fmea = _parse(SAMPLE)

    # Risk math.
    hz01 = next(h for h in hazards if h.hid == "HZ-01")
    check(hz01.risk == 3 * 3 * 3, "HZ-01 risk should be 27")
    check(hz01.band == "INTOLERABLE", "HZ-01 (risk 27) should band INTOLERABLE")

    hz14 = next(h for h in hazards if h.hid == "HZ-14")
    check(hz14.risk == 3 * 2 * 1, "HZ-14 risk should be 6")
    check(hz14.band == "MEDIUM", "HZ-14 (risk 6) should band MEDIUM")

    hz07 = next(h for h in hazards if h.hid == "HZ-07")
    check(hz07.risk == 18 and hz07.band == "HIGH", "HZ-07 should be risk 18 / HIGH")

    # FMEA math + criticality.
    filt = next(r for r in fmea if r.item.startswith("Safety filter"))
    check(filt.rpn == 10 * 3 * 7, "safety-filter RPN should be 210")
    check(filt.is_critical(), "safety filter (RPN 210) is critical")

    brake = next(r for r in fmea if r.item == "Arm joint brake")
    check(brake.rpn == 9 * 2 * 2, "brake RPN should be 36")
    # RPN 36 is below the 100 cut, but severity 9 >= sev_cut -> still critical.
    check(brake.is_critical(), "severity-9 brake must be critical even at RPN 36")

    lidar = next(r for r in fmea if r.item == "3D LiDAR")
    check(lidar.rpn == 96, "lidar RPN should be 96")
    check(not lidar.is_critical(), "lidar (RPN 96, sev 8) is NOT critical")

    # Rendering: must be sorted desc and contain the right leaders.
    md = render(hazards, fmea)
    hz_section = md.split("## FMEA")[0]
    # HZ-01 (27) must appear before HZ-07 (18) in the hazard table.
    check(hz_section.index("HZ-01") < hz_section.index("HZ-07"),
          "hazard table must be sorted by risk descending (HZ-01 before HZ-07)")
    fmea_section = md.split("## FMEA")[1]
    check(fmea_section.index("Safety filter") < fmea_section.index("3D LiDAR"),
          "FMEA table must be sorted by RPN descending (safety filter before LiDAR)")
    check("YES" in fmea_section, "critical FMEA rows must be flagged YES")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SELFTEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml", nargs="?", help="path to a hazard/FMEA YAML file")
    parser.add_argument("--selftest", action="store_true", help="run embedded tests")
    parser.add_argument("--write-sample", metavar="PATH",
                        help="write the embedded sample YAML to PATH and exit")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()

    if args.write_sample:
        with open(args.write_sample, "w", encoding="utf-8") as fh:
            yaml.safe_dump(SAMPLE, fh, sort_keys=False, width=120)
        print(f"wrote sample to {args.write_sample}", file=sys.stderr)
        return 0

    if not args.yaml:
        parser.error("provide a YAML path, or use --selftest / --write-sample")

    hazards, fmea = load(args.yaml)
    sys.stdout.write(render(hazards, fmea))
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# HINTS (read only if stuck > 15 min)
# ---------------------------------------------------------------------------
#
# Hazard.risk:
#     return self.severity * self.probability * self.exposure
#
# Hazard.band:
#     r = self.risk
#     if r >= 25: return "INTOLERABLE"
#     if r >= 12: return "HIGH"
#     if r >= 5:  return "MEDIUM"
#     return "LOW"
#
# FmeaRow.rpn:
#     return self.severity * self.occurrence * self.detection
#
# FmeaRow.is_critical:
#     return self.rpn >= rpn_cut or self.severity >= sev_cut
#
# render (hazards loop):
#     for h in sorted(hazards, key=lambda x: x.risk, reverse=True):
#         out.append(
#             f"| {h.hid} | {h.hazard} | {h.energy} | {h.harm} | {h.severity} | "
#             f"{h.probability} | {h.exposure} | {h.risk} | {h.band} | "
#             f"{h.mitigations} | {h.residual} |")
#
# render (fmea loop):
#     for r in sorted(fmea, key=lambda x: x.rpn, reverse=True):
#         flag = "YES" if r.is_critical() else ""
#         out.append(
#             f"| {r.item} | {r.failure_mode} | {r.effect} | {r.cause} | "
#             f"{r.controls} | {r.severity} | {r.occurrence} | {r.detection} | "
#             f"{r.rpn} | {flag} |")
