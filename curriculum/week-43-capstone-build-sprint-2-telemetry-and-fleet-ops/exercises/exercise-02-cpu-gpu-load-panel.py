#!/usr/bin/env python3
"""Exercise 2 — CPU/GPU/thermal load panel for the capstone dashboard.

Publishes a ``diagnostic_msgs/DiagnosticArray`` on ``/diagnostics`` at 1 Hz with
CPU%, RAM%, GPU%, and SoC temperature. Foxglove renders it as Gauge + Indicator
panels; the same numbers feed the Prometheus gauges from Lecture 1.

The GPU/thermal source is auto-detected so the one file works on three targets:

  * Jetson Orin (Path A)  -> ``jtop`` (jetson-stats) if importable, else ``tegrastats``.
  * Desktop dGPU (Path B) -> ``nvidia-smi`` query mode.
  * CPU-only fallback     -> GPU fields reported as unavailable, CPU/RAM still live.

Why this matters: thermal throttling on an Orin silently drops the clock and blows
your 30 ms perception budget. The operator needs to *see* the temperature climb
before the cycle-latency alert fires, not after.

Run:
    python3 exercise-02-cpu-gpu-load-panel.py
    # then add /diagnostics to a Foxglove Gauge panel.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

import psutil
import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node

# ---------------------------------------------------------------------------
# Thresholds. WARN/ERROR map to DiagnosticStatus levels so the Foxglove
# Indicator can color the panel. Tune for your hardware target.
# ---------------------------------------------------------------------------
CPU_WARN, CPU_ERROR = 80.0, 95.0
GPU_WARN, GPU_ERROR = 85.0, 97.0
TEMP_WARN, TEMP_ERROR = 75.0, 85.0  # °C; Orin throttles around 87 °C


@dataclass
class LoadSample:
    cpu_percent: float
    ram_percent: float
    gpu_percent: float | None      # None => GPU telemetry unavailable on this box
    temp_c: float | None


class _GpuSource:
    """Auto-detecting GPU/thermal reader. Picks the best available backend once."""

    def __init__(self) -> None:
        self._backend = self._detect()

    @staticmethod
    def _detect() -> str:
        try:
            import jtop  # noqa: F401  (jetson-stats)
            return "jtop"
        except ImportError:
            pass
        if shutil.which("tegrastats"):
            return "tegrastats"
        if shutil.which("nvidia-smi"):
            return "nvidia-smi"
        return "none"

    @property
    def backend(self) -> str:
        return self._backend

    def read(self) -> tuple[float | None, float | None]:
        """Return (gpu_percent, temp_c); either may be None if unavailable."""
        if self._backend == "jtop":
            return self._read_jtop()
        if self._backend == "tegrastats":
            return self._read_tegrastats()
        if self._backend == "nvidia-smi":
            return self._read_nvidia_smi()
        return None, self._cpu_temp_fallback()

    def _read_jtop(self) -> tuple[float | None, float | None]:
        # jtop opens a service socket; we read one snapshot and close.
        from jtop import jtop

        try:
            with jtop() as jet:
                if not jet.ok():
                    return None, None
                stats = jet.stats
                # jetson-stats exposes "GPU" as a utilisation percent and a
                # set of thermal zones; "Temp tj" (junction) is the one to gate on.
                gpu = float(stats.get("GPU", 0.0))
                temp = stats.get("Temp tj") or stats.get("Temp CPU")
                return gpu, (float(temp) if temp is not None else None)
        except Exception:  # jtop service not running, etc.
            return None, None

    def _read_tegrastats(self) -> tuple[float | None, float | None]:
        # tegrastats streams; --interval 1000 with a single line is enough.
        # Example fragment: "GR3D_FREQ 47%@..." and "tj@58.5C".
        try:
            out = subprocess.run(
                ["tegrastats", "--interval", "1000"],
                capture_output=True, text=True, timeout=2.0,
            ).stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, None
        gpu = self._scan(out, "GR3D_FREQ", "%")
        temp = self._scan(out, "tj@", "C")
        return gpu, temp

    def _read_nvidia_smi(self) -> tuple[float | None, float | None]:
        try:
            out = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=utilization.gpu,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2.0,
            ).stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, None
        if not out:
            return None, None
        gpu_str, temp_str = (f.strip() for f in out.splitlines()[0].split(","))
        return float(gpu_str), float(temp_str)

    @staticmethod
    def _scan(text: str, key: str, unit: str) -> float | None:
        """Pull the number that follows ``key`` and precedes ``unit``."""
        idx = text.find(key)
        if idx < 0:
            return None
        rest = text[idx + len(key):]
        end = rest.find(unit)
        if end < 0:
            return None
        token = rest[:end].lstrip("@").strip()
        try:
            return float(token)
        except ValueError:
            return None

    @staticmethod
    def _cpu_temp_fallback() -> float | None:
        temps = psutil.sensors_temperatures()
        for label in ("coretemp", "cpu_thermal", "k10temp", "acpitz"):
            if label in temps and temps[label]:
                return float(temps[label][0].current)
        return None


def _level_for(value: float | None, warn: float, error: float) -> bytes:
    if value is None:
        return DiagnosticStatus.STALE
    if value >= error:
        return DiagnosticStatus.ERROR
    if value >= warn:
        return DiagnosticStatus.WARN
    return DiagnosticStatus.OK


def _worst(levels: list[bytes]) -> bytes:
    # ERROR > WARN > STALE > OK by the ordinal values in DiagnosticStatus.
    order = {DiagnosticStatus.OK: 0, DiagnosticStatus.WARN: 1,
             DiagnosticStatus.ERROR: 2, DiagnosticStatus.STALE: 3}
    return max(levels, key=lambda lv: order[lv])


class LoadPanelNode(Node):
    def __init__(self) -> None:
        super().__init__("load_panel")
        self.declare_parameter("robot_id", "capstone-01")
        self.declare_parameter("publish_period", 1.0)
        self._robot = self.get_parameter("robot_id").value

        self._gpu = _GpuSource()
        self.get_logger().info(f"GPU/thermal backend: {self._gpu.backend}")

        self._pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        period = float(self.get_parameter("publish_period").value)
        self.create_timer(period, self._tick)

    def _sample(self) -> LoadSample:
        cpu = psutil.cpu_percent(interval=None)   # non-blocking
        ram = psutil.virtual_memory().percent
        gpu, temp = self._gpu.read()
        return LoadSample(cpu, ram, gpu, temp)

    def _tick(self) -> None:
        s = self._sample()
        status = DiagnosticStatus()
        status.name = "capstone/compute_load"
        status.hardware_id = self._robot

        levels = [
            _level_for(s.cpu_percent, CPU_WARN, CPU_ERROR),
            _level_for(s.gpu_percent, GPU_WARN, GPU_ERROR),
            _level_for(s.temp_c, TEMP_WARN, TEMP_ERROR),
        ]
        status.level = _worst(levels)

        status.values = [
            KeyValue(key="cpu_percent", value=f"{s.cpu_percent:.1f}"),
            KeyValue(key="ram_percent", value=f"{s.ram_percent:.1f}"),
            KeyValue(key="gpu_percent",
                     value="n/a" if s.gpu_percent is None else f"{s.gpu_percent:.1f}"),
            KeyValue(key="temp_c",
                     value="n/a" if s.temp_c is None else f"{s.temp_c:.1f}"),
            KeyValue(key="gpu_backend", value=self._gpu.backend),
        ]
        if status.level == DiagnosticStatus.ERROR:
            status.message = "compute saturated or thermal limit reached"
        elif status.level == DiagnosticStatus.WARN:
            status.message = "compute load elevated"
        elif status.level == DiagnosticStatus.STALE:
            status.message = "GPU/thermal telemetry unavailable"
        else:
            status.message = "nominal"

        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        arr.status = [status]
        self._pub.publish(arr)

        gpu_str = "n/a" if s.gpu_percent is None else f"{s.gpu_percent:.0f}%"
        temp_str = "n/a" if s.temp_c is None else f"{s.temp_c:.0f}°C"
        self.get_logger().info(
            f"[ops] cpu={s.cpu_percent:.0f}% gpu={gpu_str} thermal={temp_str} "
            f"({status.message})"
        )


def main() -> None:
    rclpy.init()
    node = LoadPanelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Foxglove wiring
# ---------------------------------------------------------------------------
# 1. Run this node, then in Foxglove add a *Gauge* panel bound to
#    /diagnostics -> status[0].values where key=="gpu_percent". Set range 0..100,
#    color stops green<85, amber 85..97, red>97 to match the thresholds above.
# 2. Add a second Gauge for cpu_percent and a third for temp_c (range 0..90,
#    red>85 to flag throttling).
# 3. Add an *Indicator* panel bound to status[0].level so the panel goes amber on
#    WARN and red on ERROR — the at-a-glance "the box is hot" signal.
#
# Hint: if /diagnostics already carries other nodes' statuses (diagnostic_updater),
# filter the Foxglove panels by status.name == "capstone/compute_load".
#
# Hint: on a Jetson, `sudo pip install jetson-stats` and `sudo systemctl restart
# jtop.service` once; then this node prefers the jtop backend automatically.
