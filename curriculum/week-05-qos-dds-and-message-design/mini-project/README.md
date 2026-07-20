# Mini-Project — `crunchbot_qos`: One Place Where QoS Is Decided

> Build a reusable QoS-profile module for the crunchbot bring-up that assigns the *correct* profile to every topic class — sensors, latched map, parameters, commands, diagnostics — and an introspection script that audits the **live graph** against that module and tells you, topic by topic, whether reality matches policy.

This is the artifact that kills the week's anti-pattern: forty node files each hand-rolling a `QoSProfile(...)`, the numbers drifting, a fat-fingered depth in node #37, and a silent mismatch nobody finds until the demo. After this week, QoS is a decision made **once**, in one module, imported everywhere — and verifiable on a running robot with one command.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This module becomes part of your **Week 8 `crunchbot_bringup` package** (the Phase 1 integration milestone). The launch files you write in Week 8 will import `crunchbot_qos`, and the architecture-review rubric explicitly checks that your QoS lives in one place. Build it well now; you'll defend it in four weeks.

---

## What you will build

A small ament-python package `crunchbot_qos` with three deliverables:

1. **`crunchbot_qos/profiles.py`** — the single source of truth. A typed registry mapping every *topic class* and every *known topic name* to its correct `QoSProfile`, plus tiny factory functions so callers never construct a profile by hand.
2. **`crunchbot_qos/audit.py`** — a runnable node/script that walks the live graph, looks up each topic's expected profile in the registry, fetches each endpoint's actual QoS, and prints a pass/fail audit table. It exits non-zero if any topic on the policy list is mis-configured — so it works in CI and in a pre-launch healthcheck.
3. **A demo bring-up** (`launch/demo.launch.py` + two tiny nodes) that publishes one topic of *each* class using the module, so the auditor has something real to audit.

By the end you have a public repo of ~250–350 lines of Python (excluding tests) that any future crunchbot package can `from crunchbot_qos.profiles import sensor_qos` and never get QoS wrong again.

---

## Why a module and not a config file

You could put QoS in YAML and load it. Don't — not as the source of truth. A Python module gives you:

- **Type safety.** `ReliabilityPolicy.BEST_EFFORT` is checked by your editor; the string `"best_effort"` in YAML is checked by nothing until runtime.
- **Factory functions.** `sensor_qos()` can encode "BEST_EFFORT + KEEP_LAST(5)" once; a YAML row repeats the four fields and invites drift.
- **One import.** `from crunchbot_qos.profiles import map_qos` is greppable across the whole workspace; forty inline `QoSProfile(...)` calls are not.

YAML is fine for *operator overrides* layered on top (a field tech bumping a depth). The *defaults and the policy* live in code. That's the senior-shop convention in 2026.

---

## Package layout

```
crunchbot_qos/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunchbot_qos
├── crunchbot_qos/
│   ├── __init__.py
│   ├── profiles.py          # the registry + factories (source of truth)
│   ├── audit.py             # the live-graph auditor (a node)
│   └── demo_nodes.py        # one publisher per class, for the demo
├── launch/
│   └── demo.launch.py
└── test/
    ├── test_profiles.py     # unit tests: every class returns the right policy values
    └── test_audit_logic.py  # unit tests: the compare() verdict logic
```

---

## Deliverable 1 — `profiles.py` (the source of truth)

This is the heart of the project. It must:

- Define a factory per topic class: `sensor_qos()`, `map_qos()`, `command_qos()`, `parameters_qos()`, `diagnostics_qos()`. Each returns a fresh `QoSProfile` matching the Lecture 1 §5 taste-test table.
- Define an enum `TopicClass` and a `CLASS_FACTORIES` dict mapping each class to its factory.
- Define a `TOPIC_POLICY` registry: a dict from concrete topic name (`/scan`, `/imu/data`, `/map`, `/cmd_vel`, `/tf_static`, `/diagnostics`, ...) to its `TopicClass`. This is what the auditor checks the live graph against.
- Provide `expected_profile(topic_name) -> QoSProfile | None` that looks up a topic's class and returns its profile (or `None` if the topic isn't on the policy list — unknown topics are reported, not failed).

Here is the spine to start from; fill in the remaining factories and the registry yourself:

```python
"""crunchbot_qos.profiles — the single source of truth for QoS on the crunchbot.

Import these. Never hand-roll a QoSProfile in a node again.
"""
from __future__ import annotations

from enum import Enum

from rclpy.duration import Duration
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)


class TopicClass(str, Enum):
    SENSOR = "sensor"
    LATCHED = "latched"
    COMMAND = "command"
    PARAMETERS = "parameters"
    DIAGNOSTICS = "diagnostics"


def sensor_qos() -> QoSProfile:
    """High-rate, time-sensitive, 'the next one fixes a drop'. /scan, /imu, /points."""
    return QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=5,
    )


def map_qos() -> QoSProfile:
    """Latched state: /map, /robot_description. Late subscribers must catch up."""
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


def command_qos() -> QoSProfile:
    """/cmd_vel and friends: reliable, only-the-latest-matters, depth 1."""
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


# TODO: parameters_qos() and diagnostics_qos() — match the §5 table.
#   parameters: RELIABLE / VOLATILE / KEEP_LAST(1000)
#   diagnostics: RELIABLE / TRANSIENT_LOCAL / KEEP_LAST(1) (latest sticky for late dashboards)


CLASS_FACTORIES = {
    TopicClass.SENSOR: sensor_qos,
    TopicClass.LATCHED: map_qos,
    TopicClass.COMMAND: command_qos,
    # TODO: PARAMETERS, DIAGNOSTICS
}

# The policy list: every topic the bring-up owns, and its class.
TOPIC_POLICY = {
    "/scan": TopicClass.SENSOR,
    "/imu/data": TopicClass.SENSOR,
    "/map": TopicClass.LATCHED,
    "/robot_description": TopicClass.LATCHED,
    "/cmd_vel": TopicClass.COMMAND,
    "/diagnostics": TopicClass.DIAGNOSTICS,
    # TODO: add /tf_static (latched, but with a DEEP history — special-case it),
    #       /parameter_events (parameters), and any topic your week-3 robot owns.
}


def expected_profile(topic_name: str) -> QoSProfile | None:
    """Return the policy QoS for a topic, or None if the topic isn't on the list."""
    klass = TOPIC_POLICY.get(topic_name)
    if klass is None:
        return None
    return CLASS_FACTORIES[klass]()
```

> **Special case you must handle:** `/tf_static` is latched but uses a *deep* history (so a late joiner gets every static transform, not just the last). Either give it its own factory or a per-topic override. Document the choice.

---

## Deliverable 2 — `audit.py` (the live-graph auditor)

A node that, once spun, does the following for every topic in `TOPIC_POLICY`:

1. Looks up the **expected** profile via `expected_profile()`.
2. Fetches the **actual** QoS of each endpoint with `node.get_publishers_info_by_topic(topic)` and `node.get_subscriptions_info_by_topic(topic)` (these return `TopicEndpointInfo` objects whose `.qos_profile` you can read — the same data `ros2 topic info -v` prints, but programmatically).
3. Compares the **compatibility-relevant** policies (reliability, durability, deadline, liveliness) of each endpoint against the expected profile.
4. Prints a table: `topic | class | endpoint | actual | expected | verdict`.
5. Exits **non-zero** if any endpoint on a policy-listed topic disagrees on a compatibility-relevant policy.

It must distinguish three verdicts:

- **OK** — endpoint matches policy.
- **MISMATCH** — endpoint's QoS would break the request–offered rule against policy. This fails the audit.
- **UNLISTED** — a live topic that isn't in `TOPIC_POLICY`. Report it (so you notice new topics) but don't fail on it.

Compare *semantically*, not by string: a publisher offering `RELIABLE` is fine against a `BEST_EFFORT` policy (it over-satisfies), but a publisher offering `BEST_EFFORT` against a `RELIABLE` policy is a MISMATCH. Encode the request–offered direction from Lecture 1 §3 in your `compare()` function. (This is exactly the logic `test_audit_logic.py` will test.)

Skeleton of the comparison core:

```python
def reliability_ok(actual: ReliabilityPolicy, expected: ReliabilityPolicy) -> bool:
    """RELIABLE > BEST_EFFORT. An endpoint is OK if it is at least as strong as policy.
    (A RELIABLE offer satisfies a BEST_EFFORT policy; the reverse is a mismatch.)"""
    strength = {ReliabilityPolicy.BEST_EFFORT: 0, ReliabilityPolicy.RELIABLE: 1}
    return strength[actual] >= strength[expected]
```

Run it:

```bash
ros2 run crunchbot_qos audit
# or, since it walks the graph:  python3 crunchbot_qos/audit.py
```

Expected shape of output against a *correctly-configured* demo:

```
TOPIC               CLASS        ENDPOINT      ACTUAL        EXPECTED      VERDICT
/scan               sensor       PUBLISHER     BEST_EFFORT   BEST_EFFORT   OK
/scan               sensor       SUBSCRIPTION  BEST_EFFORT   BEST_EFFORT   OK
/map                latched      PUBLISHER     TRANSIENT_LOC TRANSIENT_LOC OK
/cmd_vel            command      SUBSCRIPTION  RELIABLE      RELIABLE      OK
/some_debug_topic   -            PUBLISHER     RELIABLE      -             UNLISTED
--------------------------------------------------------------------------------
audit: 6 OK, 0 MISMATCH, 1 UNLISTED  ->  PASS (exit 0)
```

And against a graph with a planted fault:

```
/scan               sensor       SUBSCRIPTION  RELIABLE      BEST_EFFORT   MISMATCH
--------------------------------------------------------------------------------
audit: 5 OK, 1 MISMATCH, 0 UNLISTED  ->  FAIL (exit 1)
```

---

## Deliverable 3 — the demo bring-up

A `launch/demo.launch.py` that starts `demo_nodes.py`, which publishes one topic of each class using the `crunchbot_qos` factories (a fake `/scan`, a latched `/map`, a `/cmd_vel` consumer, a `/diagnostics` publisher). The point is to give `audit.py` a real, correctly-configured graph to pass on — and a one-line edit to make it fail on. The demo nodes must import from `crunchbot_qos.profiles`; they must not construct any `QoSProfile` inline. That's the rule the whole project enforces.

---

## Rules

- **You may** read the ROS2 docs, the lecture notes, `rclpy` source, and Nav2/slam_toolbox QoS code.
- **You must not** construct a `QoSProfile(...)` anywhere except inside `profiles.py`. Every node and the demo import from the module. If `grep -rn "QoSProfile(" --include=*.py | grep -v profiles.py` returns anything, you've broken the project's reason to exist.
- **You must not** depend on any package outside the ROS2 Jazzy desktop install plus `pytest` (the ament test default). No third-party QoS libraries.
- Python 3.12 (Ubuntu 24.04 default), `rclpy` on Jazzy.
- The audit must exit non-zero on any MISMATCH so it can gate a launch or a CI job.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-05-crunchbot-qos-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_qos` succeeds with no warnings.
- [ ] `profiles.py` defines all five class factories with values matching the Lecture 1 §5 table, plus the `/tf_static` deep-history special case.
- [ ] `grep -rn "QoSProfile(" --include=*.py` finds matches **only** in `profiles.py`.
- [ ] `colcon test --packages-select crunchbot_qos` passes, with at least:
  - `test_profiles.py`: one test per class asserting the exact reliability/durability/history/depth values.
  - `test_audit_logic.py`: tests for `reliability_ok` and `durability_ok` covering the over-satisfies-OK and under-satisfies-MISMATCH cases, including the asymmetry (BEST_EFFORT offer vs RELIABLE policy = MISMATCH; RELIABLE offer vs BEST_EFFORT policy = OK).
- [ ] `ros2 run crunchbot_qos audit` against `demo.launch.py` prints a table and exits **0**.
- [ ] Editing one demo node to mis-set its QoS makes the auditor print a MISMATCH row and exit **1**.
- [ ] A `README.md` in the repo root with the policy table, the run commands, and a paragraph on why QoS lives in code, not YAML.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Profile correctness** | 25 | All five class factories match the taste-test table exactly; `/tf_static` deep-history handled; no off-by-one on depth. |
| **Single-source-of-truth discipline** | 20 | The `grep` check is clean; demo and any nodes import from the module; YAML (if any) is override-only. |
| **Auditor semantics** | 25 | `compare()` encodes the request–offered direction correctly, including the reliability/durability asymmetry; verdicts (OK/MISMATCH/UNLISTED) are right; non-zero exit on MISMATCH. |
| **Tests** | 15 | Unit tests cover every class and both directions of the compatibility asymmetry; `colcon test` green. |
| **Live-graph audit** | 10 | Auditor passes the correct demo and fails a planted-fault demo, demonstrated in the README with the actual output. |
| **Docs & hygiene** | 5 | Clear README, no inline profiles, sensible commits, no `bin/`/`build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to drop into Week 8's `crunchbot_bringup`. **70–89** works but has drift or a soft auditor. **Below 70** means the module isn't actually the single source of truth — fix that first.

---

## Stretch goals

- **Pre-launch gate.** Wire `audit.py` into `demo.launch.py` as a node that runs once at startup and `OnProcessExit`-shuts-down the launch if the audit fails. Now a mis-configured bring-up *refuses to start* instead of silently half-working.
- **`/tf` vs `/tf_static`.** Add both to the policy and prove the auditor distinguishes them: `/tf` is `RELIABLE`/`VOLATILE`, `/tf_static` is `RELIABLE`/`TRANSIENT_LOCAL` with deep history. Getting this pair right is a classic interview tell.
- **Vendor sweep.** Run the auditor under both `rmw_fastrtps_cpp` and `rmw_cyclonedds_cpp` and confirm identical verdicts — proving your QoS is portable and your auditor reads it correctly regardless of vendor.
- **CI job.** Add a GitHub Actions workflow that builds the package, runs `colcon test`, and runs the auditor against the demo in a headless container. Green check on every push.

---

## How this connects to the rest of C24

- **Week 6 (odometry)** publishes `/odom`; you'll add it to `TOPIC_POLICY` as a sensor-ish class and the auditor will catch you if `robot_localization` expects a different profile.
- **Week 7 (slam_toolbox)** publishes a latched `/map` — your `map_qos()` is *exactly* what it needs, and the auditor will confirm slam_toolbox and your localization agree.
- **Week 8 (integration)** folds `crunchbot_qos` into the `crunchbot_bringup` package, and the architecture review grades whether QoS is centralized. This mini-project is that centralization, built four weeks early. Push it, keep the repo, import it in Week 8.

When you've finished, push the repo and take the [quiz](../quiz.md).
