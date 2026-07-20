# Week 46 — Resources

Every resource here is **free**. The chaos-engineering literature is open; the ROS2, Nav2, and `diagnostics` docs are public; the postmortem templates from Google's SRE book and the major incident-response sites are freely readable. No paywalled books are linked. ROS2 links are pinned to **Jazzy**; swap the distro if you are on a newer one.

## Required reading (work it into your week)

- **Principles of Chaos Engineering** — the canonical statement of the steady-state hypothesis, blast radius, and run-it-in-production-carefully discipline. Read it Monday; it is short:
  <https://principlesofchaos.org/>
- **Google SRE Book — Postmortem Culture: Learning from Failure** — the blameless postmortem, what a good one contains, and why blame destroys the learning:
  <https://sre.google/sre-book/postmortem-culture/>
- **Google SRE — Example Postmortem** — a worked postmortem with timeline, root cause, and action items; the shape your two should take:
  <https://sre.google/sre-book/example-postmortem/>
- **ROS2 QoS — Deadline and Liveliness** — the two policies that turn a silent sensor dropout into a fired event. The Week 5 material, now load-bearing:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
- **`diagnostics` / `diagnostic_aggregator`** — the standard ROS2 way to fuse per-component health into one robot-health signal:
  <https://github.com/ros/diagnostics>

## Chaos engineering and resilience (skim for the ideas)

- **Netflix — Chaos Monkey / the Simian Army** — where chaos engineering as a practice started; read for the philosophy, not the cloud specifics:
  <https://netflix.github.io/chaosmonkey/>
- **Rosenthal & Jones, "Chaos Engineering" (O'Reilly, free online edition)** — the steady-state-hypothesis method in depth:
  <https://www.oreilly.com/library/view/chaos-engineering/9781492043850/>
- **Nygard, "Release It!" — the Circuit Breaker and Timeout patterns** — the resilience patterns your recovery ladder implements (summaries are freely available):
  <https://pragprog.com/titles/mnee2/release-it-second-edition/>

## Nav2 recovery and behavior (read the code that does it right)

- **Nav2 — Recovery / behavior server and the navigation behavior tree** — how production mobile robots structure replan → spin → back-up → abort. Your deadlock recovery ladder is a custom version of this:
  <https://docs.nav2.org/configuration/packages/configuring-behavior-server.html>
- **Nav2 — Behavior Trees and the navigator BT XML** — where the recovery branches live and how a timeout decorator trips them:
  <https://docs.nav2.org/behavior_trees/index.html>
- **`bond` / lifecycle and the lifecycle manager** — how Nav2 detects a crashed node and brings the stack down safely (the model for your watchdog):
  <https://docs.nav2.org/configuration/packages/configuring-lifecycle.html>

## Watchdogs, health, and E-stop

- **`ros2 lifecycle`** — managed nodes; the clean way to take a faulted subsystem to a safe state:
  <https://docs.ros.org/en/jazzy/Tutorials/Demos/Managed-Nodes.html>
- **`std_msgs` / `diagnostic_msgs/DiagnosticArray`** — the message types your health aggregator publishes:
  <https://github.com/ros/diagnostics/tree/ros2/diagnostic_msgs>
- **ISO 13482 (personal-care robots) and ISO 10218 (industrial manipulators)** — the safety framings behind "what is a safe state?" The standards themselves are paywalled, but the freely available summaries explain the fail-safe categories your recovery must respect:
  <https://en.wikipedia.org/wiki/ISO_13482>

## On-call and incident response (the mindset)

- **PagerDuty — Incident Response documentation (free)** — severity levels, the incident commander role, and the discipline of triage that maps directly onto a robot fleet:
  <https://response.pagerduty.com/>
- **Atlassian — Incident postmortem template (free)** — a second, slightly different postmortem template to compare against the SRE one:
  <https://www.atlassian.com/incident-management/postmortem/templates>

## Tools you'll use this week

- **`ros2 lifecycle set <node> shutdown`** and a plain process `kill -9` — the two ways you inject a "node died" failure. The first is graceful; the second is the brutal real-world version.
- **`ros2 topic pub` / a fault-injection node** — to spawn the moved obstacle for the doorway deadlock.
- **`ros2 topic hz` / `ros2 topic delay`** — to confirm a sensor stopped (or slowed) and to measure detection latency.
- **Foxglove** — the operator dashboard; the panel where the fault and recovery must become visible inside 60 s.
- **`ros2 bag record`** — record the whole drill so the postmortem timeline comes from data, not memory. Always bag a gameday.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Chaos engineering** | Deliberately injecting failures into a system to find weaknesses before they find you. |
| **Steady-state hypothesis** | A measurable definition of "the system is healthy" that you assert holds, then test by breaking something. |
| **Blast radius** | How much of the system a given injection can affect; you keep it small and reversible. |
| **Graceful degradation** | Continuing with reduced capability (slower, fewer sensors, wider margins) instead of failing or pretending nothing happened. |
| **Watchdog** | A monitor that fires when an expected signal (a heartbeat, a sensor message) stops arriving in time. |
| **Deadline (QoS)** | The max expected gap between messages; missing it fires an event — your fastest dropout detector. |
| **Liveliness (QoS)** | How a publisher asserts it is alive; losing it tells a subscriber the writer is gone. |
| **Health aggregator** | A node that fuses per-component status into one robot-health signal the operator and the BT can act on. |
| **Recovery ladder** | The ordered escalation: replan → relax constraints → request operator assist → controlled stop. |
| **Safe state** | The state the robot goes to when it cannot continue safely — usually a controlled stop with brakes/clamps engaged. |
| **Operator-detectable** | The fault and recovery are visible to a human on the dashboard, not just in a log nobody reads. |
| **Blameless postmortem** | A write-up that explains *what and why* without assigning fault, so people tell the truth and the system gets fixed. |
| **MTTD / MTTR** | Mean Time To Detect / Mean Time To Recover — the two numbers a drill measures. |

---

*If a link 404s, please open an issue so we can replace it.*
