# Week 43 — Resources

Every resource on this page is **free** and current to 2026. ROS2 Jazzy docs, Foxglove docs, Prometheus and OpenTelemetry docs, and Open-RMF are all open. No paywalled material is linked.

## Required reading (work it into your week)

- **Foxglove documentation — the operator's tool** — panels, layouts, the ROS bridge, MCAP:
  <https://docs.foxglove.dev/docs>
- **`foxglove_bridge` (ROS2 WebSocket bridge)** — the node that streams your live topics to Foxglove:
  <https://github.com/foxglove/ros-foxglove-bridge>
- **Prometheus — instrumenting an application** — the pull model, metric types, exposition format:
  <https://prometheus.io/docs/practices/instrumentation/>
- **`prometheus-client` for Python** — counters, gauges, histograms, the `start_http_server` `/metrics` endpoint:
  <https://prometheus.github.io/client_python/>
- **OpenTelemetry Python — getting started** — `TracerProvider`, spans, the OTLP exporter:
  <https://opentelemetry.io/docs/languages/python/getting-started/>
- **ROS2 Jazzy — managed (lifecycle) nodes** — the state machine the control-authority arbiter rides on:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Node-Lifecycle.html>

## ROS2 + the telemetry plumbing

- **ROS2 Jazzy documentation root** — the version every example here targets:
  <https://docs.ros.org/en/jazzy/index.html>
- **`twist_mux` — the canonical `/cmd_vel` multiplexer** — read it before you write your own arbiter; you are extending this idea with lifecycle + a latched authority state:
  <https://github.com/ros-teleoperation/twist_mux>
- **`teleop_twist_keyboard` / `teleop_twist_joy`** — the teleop sources you mux against:
  <https://github.com/ros2/teleop_twist_keyboard>
- **`diagnostic_msgs/DiagnosticArray`** — the message type the CPU/GPU panel publishes:
  <https://docs.ros2.org/latest/api/diagnostic_msgs/msg/DiagnosticArray.html>
- **`diagnostic_updater` / `diagnostic_aggregator`** — the standard ROS2 way to roll up diagnostics for a dashboard:
  <https://github.com/ros/diagnostics>

## Foxglove specifics

- **Foxglove panels reference** — 3D, Plot, Indicator, Gauge, Raw Messages, Image:
  <https://docs.foxglove.dev/docs/visualization/panels/introduction>
- **MCAP — the recording format** — the container your week-48 dashboard recording uses:
  <https://mcap.dev/>
- **Foxglove layouts** — exporting and version-controlling the dashboard JSON:
  <https://docs.foxglove.dev/docs/visualization/layouts>
- **Foxglove SDK (server-side, for custom panels / publishing)** — if you outgrow the bridge:
  <https://docs.foxglove.dev/docs/sdk>

## Prometheus + OpenTelemetry deeper

- **Prometheus metric types** — counter vs gauge vs histogram vs summary, and when each is correct:
  <https://prometheus.io/docs/concepts/metric_types/>
- **Prometheus naming + label conventions** — keep label cardinality low on an embedded box:
  <https://prometheus.io/docs/practices/naming/>
- **OpenTelemetry Collector** — the OTLP receiver you export traces and metrics into:
  <https://opentelemetry.io/docs/collector/>
- **OpenTelemetry semantic conventions** — name your spans the way the ecosystem expects:
  <https://opentelemetry.io/docs/specs/semconv/>

## Jetson / GPU + thermal monitoring

- **`jetson-stats` (`jtop`) — the Jetson telemetry library** — Python access to GPU%, power, and thermals on Orin:
  <https://github.com/rbonghi/jetson_stats>
- **`tegrastats` — the stock Jetson load/thermal tool** — what `jtop` wraps; parse it if you cannot install `jtop`:
  <https://docs.nvidia.com/jetson/archives/r36.3/DeveloperGuide/AT/JetsonLinuxDevelopmentTools/TegrastatsUtility.html>
- **`nvidia-smi` query mode** — for a desktop/dGPU Path B box: `nvidia-smi --query-gpu=utilization.gpu,temperature.gpu --format=csv`:
  <https://docs.nvidia.com/deploy/nvidia-smi/>
- **`psutil`** — cross-platform CPU%, RAM, temperatures, and per-process stats:
  <https://psutil.readthedocs.io/>

## Fleet + heartbeat schema

- **Open-RMF documentation** — the fleet framework whose `FleetState`/`RobotState` your `/fleet/heartbeat` mirrors:
  <https://osrf.github.io/ros2multirobotbook/>
- **`rmf_internal_msgs` — `rmf_fleet_msgs`** — the actual `.msg` definitions to align your heartbeat with:
  <https://github.com/open-rmf/rmf_internal_msgs>
- **Open-RMF GitHub org** — fleet adapters, the demos, the schema source of truth:
  <https://github.com/open-rmf>

## OTA updates for robots (extending C7)

- **Mender — A/B (dual-rootfs) updates for embedded Linux** — the canonical open A/B updater; read the architecture even if you do not deploy it:
  <https://docs.mender.io/>
- **RAUC — robust auto-update controller** — the other major open A/B/slot updater used in robot fleets:
  <https://rauc.readthedocs.io/>
- **balenaOS / balenaCloud — container-image OTA** — the container-delta model for fleets that ship Docker images:
  <https://www.balena.io/docs/>
- **AWS IoT Greengrass — component + deployment OTA** — the cloud-orchestrated model, for context:
  <https://docs.aws.amazon.com/greengrass/v2/developerguide/>
- **The Update Framework (TUF)** — how to sign and secure an OTA channel so a compromised server cannot brick your fleet:
  <https://theupdateframework.io/>

## Talks and longer reads (free, no signup)

- **"Foxglove for robotics observability"** — the official Foxglove channel walks through building operator layouts:
  <https://www.youtube.com/@foxglovedev>
- **ROSCon talks on robot observability and fleet ops** — every ROSCon talk is posted free; search "ROSCon observability" and "ROSCon fleet":
  <https://roscon.ros.org/>
- **"My Philosophy on Alerting" (Rob Ewaschuk, the Google SRE memo)** — the canonical text on alerting on symptoms not causes; calibrate your robot P0/P1/P2 to it:
  <https://docs.google.com/document/d/199PqyG3UsyXlwieHaqbGiWVa8eMWi8zzAn0YfcApr8Q/edit>
- **Google SRE Book — "Monitoring Distributed Systems"** — the four golden signals, translated to a robot in the lecture notes:
  <https://sre.google/sre-book/monitoring-distributed-systems/>

## Tools you'll use this week

- **`ros2` CLI** — `ros2 topic`, `ros2 lifecycle`, `ros2 run`. Installed with ROS2 Jazzy.
- **`foxglove_bridge`** — `sudo apt install ros-jazzy-foxglove-bridge`.
- **Prometheus** — a single static binary from <https://prometheus.io/download/>; no install needed.
- **`pip` extras** — `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `psutil`, and `jetson-stats` on a Jetson.
- **`mcap` CLI** — inspect and trim your dashboard recording: <https://github.com/foxglove/mcap/tree/main/go/cli/mcap>.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Telemetry** | Structured, time-aligned signals you watch *while* the robot runs (vs. logs you read after). |
| **Prometheus** | A pull-model time-series database that scrapes a `/metrics` HTTP endpoint and alerts on the numbers. |
| **OpenTelemetry (OTel)** | A vendor-neutral SDK for emitting traces (spans) and metrics, exported over OTLP. |
| **Foxglove** | The operator-facing visualization tool that renders live robot state as a panel layout. |
| **MCAP** | The recording container Foxglove uses; one file replays every panel. |
| **`foxglove_bridge`** | The ROS2 node that streams live topics to Foxglove over WebSocket. |
| **`/cmd_vel` mux** | A node that selects exactly one of several velocity-command sources to forward to the base. |
| **Control authority** | Which source (AUTONOMY or TELEOP) is currently allowed to drive the robot. |
| **Arbiter** | The lifecycle node that owns control authority and switches the mux atomically. |
| **`/fleet/heartbeat`** | The 1 Hz topic where the robot reports identity, capabilities, and health to a fleet. |
| **OTA** | Over-the-air update — pushing new software to a deployed robot without physical access. |
| **A/B partition** | Two rootfs slots; update the inactive one, health-gate the switch, roll back by switching back. |
| **Health gate** | A check that must pass after an update before the new image is marked "good." |
| **Thermal throttling** | The SoC dropping clock speed when too hot — silently blows your perception latency budget. |

---

*If a link 404s, please open an issue so we can replace it.*
