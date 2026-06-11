# Week 41 — Capstone Integration Sprint + Safety Case

Welcome to the capstone phase. For forty weeks you built the layers of an autonomy stack — math, ROS2, perception, fusion, SLAM, planning, control, manipulation, learned policies, sim-to-real. Weeks 41 through 48 fuse those layers into a single robot you defend in front of a panel. This is the first week of that arc, and it opens not with code but with the **safety case**: the document that says, in writing, *why a person can stand next to this robot while it runs*.

If that sounds like paperwork, recalibrate. The safety case is the single most senior artifact you will produce in this track. A line engineer can tune a controller. A staff engineer can architect a perception graph. But the person who signs the safety case is the person who owns the consequences of the robot moving. In a real robotics company, no robot leaves the lab — let alone touches a customer site — until a safety case exists, has been reviewed, and has a name on the residual-risk-acceptance line. This week you learn to author that document the way it is actually authored: against ISO 13482 (personal-care robots) and ISO 10218 (industrial manipulators), with a hazard log, an FMEA, a mitigations design, a residual-risk statement, and a validation plan.

You are on one of two paths from here. **Path A** brings the capstone up on real hardware (a mobile manipulator: a wheeled base plus a small arm). **Path B** hardens a sim-production-grade deployment (Gz Sim or Isaac Sim, treated as the deployment target). The safety case differs in detail between the two — the hazards of a 30 kg base with a real gripper are not the hazards of a simulated one — but the *method* is identical. We teach the method. You instantiate it for your path.

A blunt warning that we will repeat all week: **a safety case is not a compliance theater exercise.** A hazard log with twelve rows that all say "mitigated by E-stop" is worthless and a reviewer will fail it on sight. The point of this artifact is to make you find the failure modes *before* the robot finds them for you, on a person. We grade it as the Week 41 milestone (5% of the track), and it becomes the safety appendix of your capstone portfolio. Reviewers in your eventual robotics-startup interview will read it. Write it like that is true, because it is.

## Learning objectives

By the end of this week, you will be able to:

- **Frame** a robot's safety argument against the correct standard — ISO 13482 for a personal-care / service robot operating near people, ISO 10218-1/-2 (and the ISO/TS 15066 collaborative annex) for an industrial manipulator — and explain *why* that framing was chosen.
- **Write** the intended-use and reasonably-foreseeable-misuse sections that bound every later argument in the case, distinguishing what the robot is *for* from what people will *actually do* with it.
- **Build** a hazard log that enumerates real, specific hazards (not "the robot could fail") with severity, probability, and exposure, and assign each a risk rating you can defend.
- **Run** an FMEA across the integrated autonomy stack — perception, localization, planning, control, the learned policy, the safety filter, the compute and power subsystems — scoring Severity × Occurrence × Detection into a Risk Priority Number (RPN).
- **Design** a defense-in-depth mitigation stack: hardware E-stop, software E-stop, a software watchdog, and perception confidence gates — and explain the independence and the failure mode of each layer.
- **Distinguish** a software E-stop from a hardware E-stop and articulate why a safety case that relies on a software E-stop alone is not credible.
- **State** a residual-risk position honestly — what risk remains after mitigation, who accepts it, and on what basis — without hand-waving the remainder to zero.
- **Author** a validation plan that ties each top hazard to a concrete, runnable test with a pass/fail criterion, so "we believe it is safe" becomes "here is the evidence."
- **Complete** the path-appropriate pre-flight checklist — the hardware bring-up checklist (Path A) or the sim-production-grade checklist (Path B) — as the entry gate to the build sprint.

## Prerequisites

This week assumes you have completed **C24 weeks 1–40** and have a working (if rough) integrated stack to write a safety case *about*. Specifically:

- You have a ROS2 Jazzy workspace on Ubuntu 24.04 that brings up your capstone robot — base + arm — in sim, and (Path A) you have the hardware on a bench.
- You have a navigation stack (Nav2), a manipulation stack (MoveIt2), at least one learned policy with a classical fallback (from the Week 32 milestone), and a perception pipeline that produces detections with confidence scores.
- You understand behavior trees well enough to read and edit a BT.CPP tree (weeks 24–25), because the safety filter and the watchdog hook into the tree.
- You can read C++ and Python ROS2 nodes fluently and write both. The exercises this week include a runnable `rclpy` watchdog and a runnable BT.CPP safety condition node.
- You have `colcon`, `ros2`, and a working DDS (the Jazzy default is rmw_fastrtps; some of you switched to rmw_cyclonedds — either is fine).

You do **not** need any formal functional-safety background (no prior IEC 61508, no Cat-3/PLd certification experience). We teach the framing from first principles, calibrated to a robotics startup, not to an automotive Tier-1.

## Topics covered

- Why a safety case exists, who owns it, and what "the robot is safe" actually means as a falsifiable claim.
- The standards landscape in 2026: ISO 13482, ISO 10218-1:2025 and -2:2025, ISO/TS 15066 (power-and-force-limited collaborative operation), ISO 12100 (the risk-assessment meta-standard everything inherits from), and where ANSI/RIA R15.06 and the EU Machinery Regulation 2023/1230 fit.
- Intended use and the operational design domain (ODD) — borrowing the autonomous-vehicle term because it is the right tool.
- Reasonably-foreseeable misuse — the section juniors skip and reviewers fail you on.
- The hazard log: hazard identification, the energy-source method, severity / probability / exposure, and risk rating.
- FMEA mechanics: failure mode, effect, cause, current controls, Severity × Occurrence × Detection = RPN, and the criticality cutoff.
- The four-layer mitigation stack: hardware E-stop (the contactor that opens the motor power), software E-stop (a latched stop state in the stack), the software watchdog (a deadline monitor that trips when a node goes silent), and perception confidence gates (refuse to act on low-confidence perception).
- Independence, common-cause failure, and why two software mitigations are not "two layers."
- Residual risk: what it is, the ALARP principle ("as low as reasonably practicable"), and the acceptance signature.
- The validation plan: turning each hazard into a test with a measured pass criterion.
- Path A: the hardware bring-up pre-flight checklist (power, E-stop continuity, motor-power contactor, encoder sanity, IMU bias, network, watchdog liveness).
- Path B: the sim-production-grade pre-flight checklist (deterministic launch graph, clean cold boot, telemetry up, fault injection wired, no orphaned nodes).

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a clock to punch.

| Day       | Focus                                                        | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Why safety cases; ISO 13482/10218 framing; intended use     |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Hazard log; energy-source method; risk rating               |    1.5h  |    2h     |     1h     |    0.5h   |   0.5h   |     0h       |    0.5h    |     6h      |
| Wednesday | FMEA on the integrated stack; RPN; criticality cutoff       |    1.5h  |    1.5h   |     1h     |    0.5h   |   0.5h   |     0.5h     |    0.5h    |     6h      |
| Thursday  | Mitigations: HW/SW E-stop, watchdog, confidence gates       |    1h    |    1.5h   |     0h     |    0.5h   |   0.5h   |     2h       |    0.5h    |     6h      |
| Friday    | Pre-flight checklist (Path A or B); residual risk; validation |  0h    |    1h     |     0h     |    0.5h   |   0.5h   |     3h       |    0.5h    |     5.5h    |
| Saturday  | Mini-project deep work — author the full safety case        |    0h    |    0h     |     0h     |    0h     |   0.5h   |     3h       |    0h      |     3.5h    |
| Sunday    | Quiz, peer review, polish                                   |    0h    |    0h     |     0h     |    1h     |   0h     |     1.5h     |    0h      |     2.5h    |
| **Total** |                                                             | **7.5h** | **7.5h**  | **3h**     | **4h**    | **4h**   | **10h**      | **3h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The standards, the FMEA references, the functional-safety reading, and the ROS2-safety tooling |
| [lecture-notes/01-the-safety-case-as-an-artifact.md](./lecture-notes/01-the-safety-case-as-an-artifact.md) | What a safety case is; ISO 13482 / ISO 10218 framing; intended use & misuse; the hazard log; the FMEA |
| [lecture-notes/02-preflight-checklists-and-mitigations.md](./lecture-notes/02-preflight-checklists-and-mitigations.md) | Hardware bring-up vs sim-production-grade pre-flight; the four-layer mitigation stack; residual risk; validation |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-intended-use-and-misuse.md](./exercises/exercise-01-intended-use-and-misuse.md) | Draft the intended-use and foreseeable-misuse sections for your capstone robot |
| [exercises/exercise-02-watchdog-and-confidence-gate.py](./exercises/exercise-02-watchdog-and-confidence-gate.py) | A runnable `rclpy` software watchdog + perception-confidence gate that latches a software E-stop |
| [exercises/exercise-03-hazard-log-fmea.py](./exercises/exercise-03-hazard-log-fmea.py) | A runnable hazard-log + FMEA tool: load rows from YAML, compute risk ratings and RPN, sort by criticality, emit Markdown |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-fmea-highest-severity-mitigation.md](./challenges/challenge-01-fmea-highest-severity-mitigation.md) | Find the single highest-severity failure mode in your stack and demonstrably reduce its risk rating, before/after |
| [quiz.md](./quiz.md) | 14 questions with an answer key |
| [homework.md](./homework.md) | Six concrete homework deliverables with a rubric |
| [mini-project/README.md](./mini-project/README.md) | The graded Week 41 artifact: the portfolio-quality capstone safety case |

## The "no unsigned residual" promise

C24 uses a recurring marker for any safety artifact that is actually complete:

```
Residual risk: ACCEPTED by <name> on <date>  ·  basis: validation plan §4, all top-RPN hazards tested  ·  ALARP: yes
```

If your safety case ends without that line — a named human accepting a *stated* residual risk on a *stated* basis — it is not done. "It's safe" is not a residual-risk statement. "After the four mitigations below, the worst credible outcome is a low-speed contact at ≤ 0.25 m/s producing ≤ 25 N of force, which is below the ISO/TS 15066 pain threshold for the forearm, accepted by Jane Roe on 2026-06-12" is a residual-risk statement. The whole week builds toward being able to write that second sentence and mean it.

## A note on honesty

The fastest way to fail this week is to write a safety case that lies. A hazard log that omits the obvious hazard (your arm can pinch a finger; your base can run over a foot) because including it is inconvenient is worse than no safety case at all — it manufactures false confidence. We would rather read a case that says "we identified this hazard, we could not fully mitigate it, here is the residual risk and here is who accepted it" than one that pretends the hazard does not exist. Reviewers — and regulators, and juries — are very good at finding the hazard you hid. Don't hide it.

## Stretch goals

If you finish early and want to push further:

- Read ISO 10218-2:2025 §5 (the system-integration requirements) and map three of its clauses onto your capstone. Note where your robot is non-compliant and why.
- Add a second, *independent* hardware safety channel: a safety-rated scanning LiDAR (or its sim model) that opens the motor contactor through a safety relay, entirely outside your ROS2 graph. Document the architecture as a Cat-3 / PLd argument per ISO 13849-1.
- Compute the ISO/TS 15066 power-and-force limit for your arm's worst-case contact (mass, speed, contact area) and check it against the body-region table. If you exceed it, redesign the speed gate until you don't.
- Write the FMEA as code (extend exercise 3) so your hazard log and RPN table regenerate from a single YAML source on every commit — a living document, not a stale PDF.

## Up next

Continue to **Week 42 — Capstone Build Sprint 1** once your safety case has a signed residual-risk line and your pre-flight checklist is green. Week 42 is the first integration day: Path A brings the robot up on hardware and drives a 20-meter trajectory; Path B hardens the launch graph for a clean sub-60-second cold boot. You do not start Week 42 until Week 41's milestone is signed. That is the rule, and it is the same rule a real robotics company runs on.

---

*If you find errors in this material, please open an issue or send a PR. Future learners — and the people who stand next to their robots — will thank you.*
