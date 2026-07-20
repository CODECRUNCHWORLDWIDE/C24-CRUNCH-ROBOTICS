# Week 41 — Resources

The safety-standards world is not as free as the software-docs world. The ISO standards themselves are paywalled — that is the reality of the field, and a robotics engineer learns to live with it. Where we can, we point you at the freely readable scope/abstract pages, the regulatory texts that *are* free (EU Machinery Regulation, OSHA), and the open-source tooling and academic material that teaches the same methods without the paywall. Read the abstracts of the paid standards; buy the one or two that matter for your path if your employer will reimburse them; learn the method from the free material.

## The standards (the framing for your case)

- **ISO 13482:2014 — Robots and robotic devices — Safety requirements for personal care robots.** The framing standard for a service / personal-care robot operating near people. Scope and preview at the ISO catalogue:
  <https://www.iso.org/standard/53820.html>
  *(Note: a revision has been in development; check the catalogue for the current edition before you cite a clause number.)*
- **ISO 10218-1:2025 — Robotics — Safety requirements — Part 1: Industrial robots.** The robot-arm safety standard (the manipulator itself):
  <https://www.iso.org/standard/73933.html>
- **ISO 10218-2:2025 — Part 2: Robot systems, robot applications and robot cells.** The *integration* standard — your robot plus its workspace, the part most capstones actually fall under:
  <https://www.iso.org/standard/73934.html>
- **ISO/TS 15066:2016 — Robots and robotic devices — Collaborative robots.** The power-and-force-limited (PFL) annex: the body-region table of pain/injury thresholds you check a collaborative arm against:
  <https://www.iso.org/standard/62996.html>
- **ISO 12100:2010 — Safety of machinery — General principles for design — Risk assessment and risk reduction.** The meta-standard. Every robot safety standard inherits its risk-assessment method from here. If you buy one standard, buy this one — it teaches the method:
  <https://www.iso.org/standard/51528.html>
- **ISO 13849-1:2023 — Safety of machinery — Safety-related parts of control systems.** Where "Category 3 / Performance Level d" comes from — the standard for the E-stop and safety-relay architecture:
  <https://www.iso.org/standard/73481.html>

## The free regulatory texts (these you can actually read in full)

- **EU Machinery Regulation (EU) 2023/1230** — replaces the old Machinery Directive 2006/42/EC; applies from 20 January 2027; the first machinery law to explicitly address AI and autonomy. Full text, free:
  <https://eur-lex.europa.eu/eli/reg/2023/1230/oj>
- **OSHA Technical Manual, robotics sections** (US workplace-safety perspective, free):
  <https://www.osha.gov/robotics>
- **NIST — robot safety and performance** (free measurement-science material, useful for validation-plan metrics):
  <https://www.nist.gov/el/intelligent-systems-division-73500/cognition-and-collaboration-systems/robotic-systems-safety>

## FMEA and hazard analysis (learn the method, free)

- **NASA Systems Engineering Handbook (SP-2016-6105 Rev 2)** — the FMEA/FMECA and hazard-analysis chapters are the clearest free treatment anywhere:
  <https://www.nasa.gov/reference/systems-engineering-handbook/>
- **MIL-STD-1629A** — the original FMECA procedure; old but still the canonical reference for criticality analysis (free PDF, public domain):
  <https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=36391>
- **FAA System Safety Handbook** — fault trees, hazard severity/probability matrices, residual risk; entirely free:
  <https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/risk_management/ss_handbook>
- **STPA Handbook (Leveson & Thomas, MIT, free PDF)** — System-Theoretic Process Analysis. A modern alternative to FMEA for software-heavy autonomous systems; read this even if you use FMEA for the case, because it will change how you think about your perception and planning hazards:
  <http://psas.scripts.mit.edu/home/get_file.php?name=STPA_handbook.pdf>

## Functional safety, oriented to robots

- **"Engineering a Safer World" — Nancy Leveson (MIT Press, free PDF from the author).** The book behind STPA. The first three chapters reframe why component-failure analysis (classical FMEA) is necessary but not sufficient for software-controlled systems:
  <https://direct.mit.edu/books/oa-monograph/2908/Engineering-a-Safer-World>
- **ROS 2 Safety Working Group** — the community group documenting safety patterns for ROS2; design docs and meeting notes:
  <https://github.com/ros-safety>
- **Open Robotics — "Quality, safety, and security in ROS 2"** (REP and design docs on the topic):
  <https://docs.ros.org/en/jazzy/The-ROS2-Project/Contributing/Quality-Guide.html>

## The mitigation layers (real docs for the code you'll write)

- **ROS 2 Jazzy documentation** (the platform for every node this week):
  <https://docs.ros.org/en/jazzy/index.html>
- **Nav2 — collision monitor and speed-limit / safety zones** (the production way to do a velocity gate around the base):
  <https://docs.nav2.org/configuration/packages/collision-monitor/configuration.html>
- **BehaviorTree.CPP (BT.CPP) v4 documentation** (the safety condition node and the watchdog hook in the tree):
  <https://www.behaviortree.dev/>
- **`diagnostic_updater` / `diagnostic_aggregator`** — the standard ROS2 way to publish liveness and let an aggregator trip on a stale heartbeat:
  <https://docs.ros.org/en/jazzy/p/diagnostic_updater/>
- **micro-ROS** (Path A: the MCU-side watchdog and the E-stop input that has to survive a Linux crash):
  <https://micro.ros.org/>
- **Universal Robots — safety configuration** (a real industrial-arm safety system you can read about for free; good reference for what "safety-rated" speed/force limits look like in practice):
  <https://www.universal-robots.com/articles/ur/safety/>

## Worked examples and templates worth reading

- **UK HSE — "Reducing risks, protecting people" (R2P2)** — the canonical free explanation of ALARP and the tolerability-of-risk triangle you will cite in your residual-risk section:
  <https://www.hse.gov.uk/managing/theory/alarpglance.htm>
- **MISRA / industry safety-case structuring (GSN — Goal Structuring Notation)** — the community standard for *structuring* a safety argument as goals/strategies/evidence. The free community standard:
  <https://scsc.uk/gsn>

## Tools you'll use this week

- **`ros2`, `colcon`** — your daily ROS2 Jazzy drivers.
- **Python 3.12 + `rclpy`, `PyYAML`** — for the watchdog and the FMEA tool. `PyYAML` ships in the ROS2 Jazzy environment; if not, `pip install pyyaml` in a venv.
- **`pytest`** — the exercises and homework are testable; `pytest` is already in your ROS2 dev image.
- **A spreadsheet or, better, the YAML-driven generator from exercise 3** — for the hazard log and FMEA tables. Senior engineers version-control the YAML, not the spreadsheet.
- **Graphviz / Mermaid** — for the mitigation-architecture diagram in the mini-project. Mermaid renders inline on GitHub.

## Videos and talks (free, no signup)

- **ROSCon talks on safety and deployment** — every ROSCon talk is posted free; search the playlist for "safety," "deployment," "production":
  <https://roscon.ros.org/>
- **"Functional Safety for Autonomous Systems"** — recorded conference talks abound; search the EU Robotics and IROS channels. (If a specific link rots, search the talk title on the official conference channel.)

## Open-source projects to read this week

You learn more about safety from one well-instrumented production stack than from three standards PDFs.

- **`ros-planning/navigation2` (Nav2)** — read the `nav2_collision_monitor` package source. This is production-grade defense-in-depth you can study line by line:
  <https://github.com/ros-navigation/navigation2>
- **`BehaviorTree/BehaviorTree.CPP`** — read how reactive sequences let a safety condition pre-empt a running action:
  <https://github.com/BehaviorTree/BehaviorTree.CPP>
- **`ros/diagnostics`** — the liveness/heartbeat plumbing your watchdog should integrate with rather than reinvent:
  <https://github.com/ros/diagnostics>

## Glossary cheat sheet

Keep this open in a tab. Half of writing a safety case is using the words precisely.

| Term | Plain English |
|------|---------------|
| **Hazard** | A potential source of harm. Not a failure — a *source of harm* (e.g. "the gripper can pinch a finger"). |
| **Harm** | Physical injury or damage to health (or, by extension, property/environment). |
| **Risk** | The combination of the probability of harm and its severity. |
| **Hazardous event** | The event that turns a hazard into harm (the finger is *in* the gripper when it closes). |
| **Severity (S)** | How bad the harm is if it happens. |
| **Occurrence / Probability (O)** | How likely the failure/hazardous event is. |
| **Detection (D)** | In FMEA, how likely the system/operator is to catch the failure before harm. Low D score = easy to detect. |
| **RPN** | Risk Priority Number = S × O × D. The FMEA's sort key. |
| **FMEA** | Failure Mode and Effects Analysis — bottom-up, component-by-component failure enumeration. |
| **STPA** | System-Theoretic Process Analysis — top-down, control-structure-based hazard analysis. Complements FMEA. |
| **Intended use** | What the manufacturer says the robot is for, under what conditions (the ODD). |
| **Reasonably foreseeable misuse** | Use the manufacturer did not intend but can reasonably predict (standing in the path, a child climbing on it). |
| **ODD** | Operational Design Domain — the conditions under which the system is designed to operate (borrowed from AV safety). |
| **Residual risk** | The risk that remains after all mitigations are applied. Never zero. |
| **ALARP** | As Low As Reasonably Practicable — the UK/EU principle for accepting residual risk. |
| **E-stop (hardware)** | A safety-rated circuit that physically removes motor power (opens a contactor), independent of software. |
| **E-stop (software)** | A latched stop *state* in the software that commands zero velocity / holds position. Not a substitute for hardware. |
| **Watchdog** | A monitor that trips a safe state when an expected heartbeat/deadline is missed. |
| **PFL** | Power-and-Force-Limited operation — the collaborative mode where the arm is allowed to touch people because contact force is bounded (ISO/TS 15066). |
| **PL / Category** | Performance Level (a–e) and Category (B,1,2,3,4) from ISO 13849-1 — how trustworthy a safety function is. |
| **Common-cause failure** | A single root cause that defeats multiple "independent" mitigations at once. |

---

*If a link 404s, please open an issue so we can replace it. ISO catalogue numbers occasionally shift when a standard is revised; verify the edition before you cite a clause.*
