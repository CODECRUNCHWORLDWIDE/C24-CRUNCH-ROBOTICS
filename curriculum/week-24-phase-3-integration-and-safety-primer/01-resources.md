# Week 24 — Resources

Every resource on this page is **free** and current to 2026. The ROS2 Jazzy documentation, the Nav2 and MoveIt2 docs, the BehaviorTree.CPP docs, and the REPs are all openly accessible. The ISO standards themselves are paywalled (ISO sells the text), so we link to the freely available *summaries and framings* of ISO 10218 and ISO 13482 rather than the standards' text, and we tell you exactly which clauses matter. No paid course or paywalled book is required for this week.

Week 24 introduces almost no new API. The references here are therefore weighted toward **systems integration, lifecycle bring-up, and the functional-safety literature** — the topics that turn two correct codebases into one robot you can defend near a person.

## Required reading (work it into your week)

- **ROS2 Jazzy — Launch system, main tutorial** — the composition primitives you use to stand the base and the arm up in one graph:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html>
- **ROS2 Jazzy — Managed (lifecycle) nodes concept** — the ordered bring-up that keeps a node from commanding hardware before its inputs are valid:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Nodes.html>
- **Nav2 — Lifecycle and bringup** — the canonical lifecycle-manager pattern your composed launch graph imitates for the base half:
  <https://docs.nav2.org/concepts/index.html>
- **MoveIt2 — Concepts and the move_group node** — the arm half: the planning scene, the `move_group` action interface, and the controller manager you compose with Nav2:
  <https://moveit.picknik.ai/main/index.html>
- **REP 105 — Coordinate frames for mobile platforms** — `map`, `odom`, `base_link`; the transform chain the base and the arm must both agree on. The frame-mismatch integration defect is a REP-105 violation:
  <https://www.ros.org/reps/rep-0105.html>
- **`tf2` — Time travel and the transform_listener lookup model** — the frame/timing mismatch in this week's defect list is a `tf2` problem; this is the reference:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>

## Functional safety — the framings you cite

- **ISO 10218-1:2025 — Industrial robots, safety (official summary page)** — the manipulator-safety framing for the arm; the 2025 revision is the current edition and the one to cite in 2026. The hazard categories (collision, trapping, energy release) feed your hazard log:
  <https://www.iso.org/standard/73101.html>
- **ISO 13482:2014 — Personal care robots (official summary page)** — the framing for a mobile robot in shared space near people; scope and hazard categories for the base:
  <https://www.iso.org/standard/53820.html>
- **ISO 12100:2010 — Safety of machinery, risk assessment (official summary page)** — the parent standard for "risk = severity × probability" and the iterative risk-reduction process every robot safety case inherits:
  <https://www.iso.org/standard/51528.html>
- **IEC 60204-1 — Electrical equipment of machines, the E-stop function** — the standard that defines stop categories 0/1/2 and what an emergency-stop function must guarantee. Your software-vs-hardware E-stop distinction is grounded here:
  <https://webstore.iec.ch/publication/64761>
- **NASA Software Safety Guidebook (NASA-GB-8719.13)** — the freely downloadable treatment of software safety, hazard analysis, and fault detection/isolation/recovery; the intellectual ancestor of the hazard log and the pre-flight check:
  <https://standards.nasa.gov/standard/NASA/NASA-GB-871913>
- **MIL-STD-1629A — Procedures for Performing a Failure Mode and Effects Analysis** — the classic FMEA procedure (severity × occurrence × detectability → RPN) your hazard log grows into at Week 41:
  search for "MIL-STD-1629A FMEA"; the document is in the public domain and widely mirrored.

## The pre-flight ritual

- **Google SRE Book — "Reliable Product Launches at Scale"** — the pre-flight checklist as an engineering discipline; the "launch checklist" idea maps directly onto your pre-flight check node:
  <https://sre.google/sre-book/reliable-product-launches/>
- **`ros2 doctor` and `ros2 topic info -v`** — the introspection commands your pre-flight node automates; the CLI tools reference:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Command-Line-Tools.html>
- **ROS2 Jazzy — lifecycle service interfaces (`lifecycle_msgs`)** — `GetState`, `ChangeState`, and the state-machine labels the pre-flight check queries:
  <https://docs.ros.org/en/jazzy/p/lifecycle_msgs/>

## Nav2 + MoveIt2 composition (the codebases you are integrating)

- **Nav2 documentation** (the navigation behavior tree, costmaps, the `NavigateToPose` action, recovery): <https://docs.nav2.org/>
- **Nav2 — the navigation behavior tree** — how Nav2's own BT works, so you know where *your* top-level BT sits relative to it (yours is above, dispatching `NavigateToPose`, not buried inside Nav2's tree):
  <https://docs.nav2.org/behavior_trees/index.html>
- **MoveIt2 — controller configuration and `FollowJointTrajectory`** — the action the arm controller exposes and the one your safety node must cancel:
  <https://moveit.picknik.ai/main/doc/examples/controller_configuration/controller_configuration_tutorial.html>
- **BehaviorTree.CPP documentation** (the BT.CPP your top-level tree is written in) and **Groot 2**: <https://www.behaviortree.dev/>
- **`nav2_behavior_tree` action nodes** — the BT nodes that wrap Nav2's actions; the pattern your `MoveBaseToTable` leaf imitates:
  <https://docs.nav2.org/configuration/packages/configuring-bt-navigator.html>
- **`ros_gz` bridge** (the ROS2 ↔ Gz Sim bridge your composed stack runs on): <https://github.com/gazebosim/ros_gz>

## QoS for safety topics (the Week 5 callback)

- **About Quality of Service settings** — re-read the durability section; the E-stop is `RELIABLE`/`TRANSIENT_LOCAL` so a late subscriber still receives the latch:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
- **REP 2003 — default QoS profiles** — why a latched safety topic is `TRANSIENT_LOCAL`, as ratified policy:
  <https://www.ros.org/reps/rep-2003.html>

## Talks worth watching (all free, no account)

- **"Building a Production Robotics Stack with ROS2"** — search the **ROSCon 2024/2025** YouTube playlists for the systems-integration and lifecycle-management talks; the bring-up and composition talks are the most relevant to this week.
- **"MoveIt2 and Nav2 together"** — search the ROSCon and PickNik channels for mobile-manipulation integration talks; the namespace and controller-manager gotchas in those talks are exactly the defects in Lecture 1.
- **"Functional Safety for Robots"** — search for the **TÜV / Pilz robot-safety** introductory talks (free on YouTube); they ground the E-stop stop-categories and the hardware-vs-software distinction in the industrial-safety practice you are borrowing from.
- **"How to Write a Safety Case"** — search for the **Adelard / York University safety-case tutorial talks**; the Goal Structuring Notation framing is the academic backbone of the hazard log → safety case progression you start this week.

## How to use this resource list

The lectures cite specific URLs from this page at decision points. The links to read end-to-end *this week* are:

1. **Nav2 — Lifecycle and bringup** and **MoveIt2 — Concepts.** ~40 minutes together; the two codebases you compose on Monday.
2. **REP 105 and the `tf2` lookup model.** ~20 minutes; the reference for the frame/timing integration defect you will hit first.
3. **ISO 12100 (risk) and the ISO 10218 / ISO 13482 summaries.** ~30 minutes; the vocabulary for Lecture 2 and the hazard log.
4. **Google SRE — "Reliable Product Launches at Scale."** ~30 minutes; the frame for the pre-flight checklist in Lecture 1.

The IEC and NASA references are reference material — you frame against them in Lecture 2 and lean on them properly in Week 41 when the hazard log becomes a full safety case. Read the ISO summaries for scope and hazard categories; you do not need the paywalled text to write a first hazard log.

---

*Bookmarks decay. If a link rots, search the title — REPs, ROSCon talks, the SRE book chapters, and the ISO summary pages are all canonical and reappear on the same hosts.*
