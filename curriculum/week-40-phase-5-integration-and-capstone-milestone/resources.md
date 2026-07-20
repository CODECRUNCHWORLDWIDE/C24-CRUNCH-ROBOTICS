# Week 40 — Resources

Every resource on this page is **free** and current to 2026. The ROS2 Jazzy documentation, the Nav2 and MoveIt2 docs, the Open-RMF message repositories, and the Foxglove documentation are all openly accessible. The ISO standards themselves are paywalled (ISO sells them), so we link to the freely available *summaries and framings* of ISO 13482 and ISO 10218 rather than the standards' text, and we tell you exactly which clauses matter. No paid course or paywalled book is required for this week.

Week 40 introduces almost no new API. The references here are therefore weighted toward **systems integration, observability, and the safety/operations literature** — the topics that turn thirty-nine weeks of components into one defensible robot.

## Required reading (work it into your week)

- **The C24 capstone specification** — re-read it before anything else this week. It is the source of truth for Lecture 1: [`../../SYLLABUS.md`](../../SYLLABUS.md), the section titled "Capstone specification — Autonomous Mobile Manipulator with Language-Conditioned Pick-and-Place." Every acceptance number in the mini-project comes from there.
- **ROS2 Jazzy — Launch system, main tutorial** — the composition primitives you use to stand the whole stack up in one graph:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html>
- **ROS2 Jazzy — Managed (lifecycle) nodes concept** — the ordered bring-up that keeps a node from commanding hardware before its inputs are valid:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Nodes.html>
- **Nav2 — Lifecycle and bringup** — the canonical lifecycle-manager pattern your full-stack launch graph imitates:
  <https://docs.nav2.org/concepts/index.html>
- **Foxglove — Introduction and panels** — the dashboard you stream the telemetry spine to; the panels you need are 3D, Plot, Raw Messages, and State Transitions:
  <https://docs.foxglove.dev/docs>
- **Foxglove — Layouts** — check your milestone layout into the repo so the dashboard is reproducible:
  <https://docs.foxglove.dev/docs/visualization/layouts>
- **`tf2` — Time travel and the `transform_listener` lookup model** — the frame/timing mismatch in this week's integration-defect list is a `tf2` problem; this is the reference:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>

## The capstone-kickoff ritual — pre-flight, chaos, safety

- **NASA Software Safety Guidebook (NASA-GB-8719.13)** — the canonical, freely downloadable treatment of software safety, hazard analysis, and pre-flight verification. Read the hazard-analysis and the "fault detection, isolation, and recovery" sections; they are the intellectual ancestor of this week's chaos-drill and safety-case templates:
  <https://standards.nasa.gov/standard/NASA/NASA-GB-871913>
- **Google SRE Book — "Reliable Product Launches at Scale" (the Launch Coordination Engineering chapter)** — the pre-flight checklist as an engineering discipline, written by the people who run the largest launch checklists in the industry. The "launch checklist" idea maps directly onto your pre-flight check node:
  <https://sre.google/sre-book/reliable-product-launches/>
- **Google SRE Book — "Postmortem Culture: Learning from Failure"** — the postmortem structure your chaos-drill template ends with: timeline, root cause, contributing factors, what worked, what didn't, action items:
  <https://sre.google/sre-book/postmortem-culture/>
- **Principles of Chaos Engineering** — the short, canonical statement of what a chaos experiment *is* (a steady-state hypothesis, a real-world fault, a blast radius, a measured deviation). Your chaos-drill template is this, applied to a robot:
  <https://principlesofchaos.org/>
- **ISO 13482:2014 — Personal care robots (official summary page)** — the standard your safety case frames against for a shared-space mobile manipulator. ISO sells the text; this page tells you the scope and the hazard categories, which is what you need for the template:
  <https://www.iso.org/standard/53820.html>
- **ISO 10218-1:2025 — Industrial robots, safety (official summary page)** — the manipulator-safety framing; the 2025 revision is the current edition and the one to cite in 2026:
  <https://www.iso.org/standard/73101.html>
- **MIL-STD-1629A — Procedures for Performing a Failure Mode and Effects Analysis** — the classic FMEA procedure your safety-case template's FMEA table follows (severity × occurrence × detectability → RPN):
  search for "MIL-STD-1629A FMEA"; the document is in the public domain and widely mirrored.

## Systems integration and observability

- **REP 105 — Coordinate frames for mobile platforms** — `map`, `odom`, `base_link` and the transform chain every component in your stack must agree on. The frame-mismatch integration defect is a REP-105 violation:
  <https://www.ros.org/reps/rep-0105.html>
- **REP 103 — Standard units of measure and coordinate conventions** — the units and right-hand-rule conventions your composed stack must share. A silent unit mismatch (degrees vs radians, mm vs m) is the second-most-common integration defect after frames:
  <https://www.ros.org/reps/rep-0103.html>
- **`ros2 doctor` and `ros2 topic info -v`** — the introspection commands your pre-flight check node automates. The docs for the CLI introspection tools:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Command-Line-Tools.html>
- **`ros2 bag` (rosbag2) documentation** — record your milestone run so it is replayable, not just watchable:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html>
- **PlotJuggler** — the live time-series tool for watching drift, latency, and the safety-filter status during a run; complementary to Foxglove's 3D view:
  <https://github.com/facontidavide/PlotJuggler>
- **OpenTelemetry — Traces and metrics concepts** — the vocabulary (span, trace, metric) you will reach for in Phase 6 when the telemetry spine grows into a production operator dashboard:
  <https://opentelemetry.io/docs/concepts/>

## Fleet readiness and schemas

- **Open-RMF — `rmf_internal_msgs`** — the real fleet-state and robot-state message definitions to make your `/fleet/heartbeat` conformant to a documented schema instead of an ad-hoc one:
  <https://github.com/open-rmf/rmf_internal_msgs>
- **Open-RMF — `rmf_fleet_msgs`** — the `RobotState` / `FleetState` messages, the closest open standard to "what a robot reports about itself to a fleet manager":
  <https://github.com/open-rmf/rmf_internal_msgs/tree/main/rmf_fleet_msgs>
- **Open-RMF documentation** — the architecture context for why a heartbeat schema matters at fleet scale:
  <https://osrf.github.io/ros2multirobotbook/>

## The components you are integrating (re-reference)

These are the canonical docs for the subsystems you built earlier in C24 and are now composing. Bookmark them; you will re-open at least three of them this week when the parts disagree.

- **Nav2 documentation** (base navigation, the behavior tree, costmaps, recovery): <https://docs.nav2.org/>
- **MoveIt2 documentation** (arm planning, the `move_group` action interface, planning scene): <https://moveit.picknik.ai/main/index.html>
- **BehaviorTree.CPP documentation** (the BT.CPP your top-level tree is written in) and **Groot 2**: <https://www.behaviortree.dev/>
- **OpenVLA** (the open-weight VLA you fine-tuned and wire as a policy): <https://openvla.github.io/>
- **Open3D documentation** (the point-cloud and grasp-geometry library in your perception path): <https://www.open3d.org/docs/release/>
- **GTSAM documentation** (the factor-graph back-end behind your fused state estimate): <https://gtsam.org/>
- **`ros_gz` bridge** (the ROS2 ↔ Gz Sim bridge your sim stack runs on): <https://github.com/gazebosim/ros_gz>

## Talks worth watching (all free, no account)

- **"Building a Production Robotics Stack with ROS2"** — search the **ROSCon 2024/2025** YouTube playlists for the systems-integration and lifecycle-management talks. ROSCon talks are free and posted within weeks of the conference; the integration and bring-up talks are the most relevant to this week.
- **"Foxglove for ROS2 — building an operator dashboard"** — Foxglove's own tutorial talks on their YouTube channel; the "panels and layouts" walkthrough is the fastest way to build the milestone dashboard.
- **"Chaos Engineering at Scale"** (Nora Jones / Casey Rosenthal, on YouTube) — the canonical talk on the discipline your chaos-drill template borrows from. Not robotics-specific, but the steady-state-hypothesis framing transfers directly.
- **"How to Write a Safety Case"** — search for the **Adelard / York University safety-case tutorial talks**; the Goal Structuring Notation (GSN) framing is the academic backbone of the safety-case template.

## How to use this resource list

The lectures cite specific URLs from this page at decision points. The links you should read end-to-end *this week* are:

1. **The C24 capstone specification** (in `SYLLABUS.md`). Foundational; Lecture 1 is a clause-by-clause reading of it. Do not skip.
2. **Google SRE — "Reliable Product Launches at Scale."** ~30 minutes, the intellectual frame for the pre-flight checklist in Lecture 2.
3. **REP 105 and REP 103.** ~20 minutes together, and the reference for two of the four integration defects you will hit on Wednesday.
4. **Foxglove — panels and layouts.** ~30 minutes, the fastest path to a milestone dashboard that makes every layer observable.

The ISO and NASA references are reference material — you frame against them in Lecture 2 and lean on them properly in Week 41. The Open-RMF schemas are for the `/fleet/heartbeat` requirement; read them when you wire that topic, not before.

---

*Bookmarks decay. If a link rots, search the title — REPs, ROSCon talks, the SRE book chapters, and the ISO summary pages are all canonical and reappear on the same hosts.*
