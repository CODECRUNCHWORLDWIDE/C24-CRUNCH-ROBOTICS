# Challenge 1 — Induce and fix an `ExtrapolationException`

**Time estimate:** ~90 minutes.

## Problem statement

`ExtrapolationException` is the most common tf2 error in production, and it is the one juniors guess at for two hours. This challenge forces you to *cause* it on purpose, three different ways, and then *fix* it three different ways — so that you understand the failure mode from the inside instead of pattern-matching a Stack Overflow answer.

You will build a tiny two-node system: a **broadcaster** that publishes a single `world → sensor` transform, and a **listener** that looks it up. You will then sabotage the broadcaster's timestamps and the listener's lookup, observe the exact extrapolation error each sabotage produces, and document the before/after.

The deliverable is not "make the error go away." The deliverable is a **written before/after** — a short report and two working node files — that demonstrates you can name *why* the error fired and *which* fix is correct for *which* cause. That distinction is the whole point.

## Background you need

A tf2 lookup at time `t` fails with `ExtrapolationException` when the buffer cannot produce a transform at `t`. There are exactly two ways that happens:

- **Extrapolation into the future.** You asked for `t`, but the newest sample in the buffer is older than `t`. The listener is asking for data the broadcaster has not produced yet. This is what a *too-old broadcaster stamp* causes: the broadcaster says "this transform is valid as of 2 seconds ago," the listener asks for "now," and now is in the future relative to the data.
- **Extrapolation into the past.** You asked for `t`, but the oldest sample in the buffer is newer than `t`. The transform you want has already aged out of the cache window (default 10 s). This is what asking for an *old fixed timestamp* against a fast-rolling buffer causes.

The third "extrapolation"-flavored failure is **startup latency**: you ask for `Time(0)` (latest) before the first message has arrived, and there is simply nothing in the buffer yet. A short lookup *timeout* fixes that one by blocking until data shows up.

## The three sabotages

You must reproduce all three and document each.

### Sabotage A — stale broadcaster stamp (future extrapolation)

Make the broadcaster stamp its transform with a time **2 seconds in the past** (`now - 2.0s`) on every tick, while the listener asks for `Time(0)` (latest) with **zero timeout**. The listener's "latest" resolves to a time newer than anything in the buffer.

Expected error (shape; your numbers differ):

```
ExtrapolationException: Lookup would require extrapolation into the future.
Requested time 1749488400.000000 but the latest data is at time 1749488398.000000,
when looking up transform from frame [sensor] to frame [world]
```

### Sabotage B — old fixed lookup time (past extrapolation)

Restore correct broadcaster stamps. Now make the **listener** ask for a fixed timestamp **30 seconds in the past** (`now - 30.0s`) instead of `Time(0)`. The buffer cache is 10 s, so 30 s ago has long since aged out.

Expected error:

```
ExtrapolationException: Lookup would require extrapolation into the past.
Requested time 1749488370.000000 but the earliest data is at time 1749488390.000000,
when looking up transform from frame [sensor] to frame [world]
```

### Sabotage C — startup race (empty buffer)

Restore everything. Now start the **listener first**, broadcaster second, and have the listener look up `Time(0)` with **zero timeout** in a tight loop. For the first moment, the buffer is empty and you get an extrapolation/lookup failure until the first message lands.

## The three fixes

For each sabotage, apply the *correct* fix and show the lookup now succeeds:

- **Fix A:** Stamp the broadcaster with the **current** time (`self.get_clock().now().to_msg()`), every tick. The transform must claim to be valid *now*, not in the past. (This is the fix for 90% of real-world extrapolation errors: a node that forwards data and re-uses the *incoming* stamp when it should stamp afresh, or a node with a wrong clock.)
- **Fix B:** Use `Time(0)` ("latest available") instead of a hard-coded old timestamp, **or** if you genuinely need a specific past time, increase the buffer cache duration (`Buffer(cache_time=Duration(seconds=60.0))`) so the window covers it. Document which you chose and why.
- **Fix C:** Give the lookup a **timeout** (`timeout=Duration(seconds=0.5)`). With a nonzero timeout, `lookup_transform` blocks until the transform becomes available (or the timeout elapses), absorbing the startup race.

## Acceptance criteria

- [ ] A `broadcaster.py` and a `listener.py` (real, runnable `rclpy` nodes) that, with a single config flag or constant change at the top of each file, reproduce **each** of the three sabotages.
- [ ] A captured log (paste into the report) of each of the three `ExtrapolationException` errors, with the "future" vs "past" vs "empty buffer" cases clearly distinguished.
- [ ] The corresponding fix for each, with a captured log showing the lookup now **succeeds**.
- [ ] A `REPORT.md` (300–500 words) that, for each of the three cases, states: (1) what you changed to cause it, (2) the exact error text, (3) *which* of the two extrapolation directions (future/past) or the empty-buffer race it was, (4) the fix and *why it is the right fix for that cause* — not a different cause.
- [ ] A one-paragraph "production translation": name a **real** ROS2 scenario (a sensor driver, a Nav2 costmap, a camera-to-map projection) where each of the three causes shows up in the wild. Be specific.
- [ ] `ros2 run tf2_tools view_frames` shows `world → sensor` as a single connected edge in the fixed (working) configuration.
- [ ] Committed to your Week 2 repo under `challenges/challenge-01/`.

## Starter: the broadcaster

This is the scaffold. The `STAMP_MODE` constant is your A/C sabotage switch.

```python
#!/usr/bin/env python3
# challenge-01 broadcaster: publishes world -> sensor.
# Flip STAMP_MODE to reproduce the sabotages.

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

# "fresh"  -> stamp with now()         (correct; Fix A)
# "stale"  -> stamp with now() - 2.0s  (Sabotage A: future extrapolation)
STAMP_MODE = "stale"

STALE_OFFSET = Duration(seconds=2.0)


class WorldSensorBroadcaster(Node):
    def __init__(self) -> None:
        super().__init__("ws_broadcaster")
        self._br = TransformBroadcaster(self)
        self._timer = self.create_timer(0.05, self._tick)  # 20 Hz
        self.get_logger().info(f"broadcaster up, STAMP_MODE={STAMP_MODE}")

    def _tick(self) -> None:
        now = self.get_clock().now()
        if STAMP_MODE == "stale":
            stamp_time = now - STALE_OFFSET
        else:
            stamp_time = now

        tf = TransformStamped()
        tf.header.stamp = stamp_time.to_msg()
        tf.header.frame_id = "world"
        tf.child_frame_id = "sensor"
        tf.transform.translation.x = 1.0
        tf.transform.translation.y = 2.0
        tf.transform.translation.z = 0.5
        tf.transform.rotation.w = 1.0  # identity
        self._br.sendTransform(tf)


def main() -> None:
    rclpy.init()
    node = WorldSensorBroadcaster()
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
```

## Starter: the listener

The `LOOKUP_MODE` and `TIMEOUT_S` constants are your B/C sabotage switches.

```python
#!/usr/bin/env python3
# challenge-01 listener: looks up sensor in world.
# Flip LOOKUP_MODE / TIMEOUT_S to reproduce the sabotages.

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener, ExtrapolationException, LookupException

# "latest" -> Time(0)              (correct default; Fix B/C)
# "old"    -> now() - 30.0s        (Sabotage B: past extrapolation)
LOOKUP_MODE = "old"

# 0.0 reproduces the startup race (Sabotage C); 0.5 is Fix C.
TIMEOUT_S = 0.0

# Default cache is 10 s. Bump to 60 s as one option for Fix B.
CACHE_S = 10.0

OLD_OFFSET = Duration(seconds=30.0)


class WorldSensorListener(Node):
    def __init__(self) -> None:
        super().__init__("ws_listener")
        self._buffer = Buffer(cache_time=Duration(seconds=CACHE_S))
        self._listener = TransformListener(self._buffer, self)
        self._timer = self.create_timer(0.5, self._tick)
        self.get_logger().info(
            f"listener up, LOOKUP_MODE={LOOKUP_MODE}, TIMEOUT_S={TIMEOUT_S}, CACHE_S={CACHE_S}"
        )

    def _tick(self) -> None:
        if LOOKUP_MODE == "old":
            when = self.get_clock().now() - OLD_OFFSET
        else:
            when = Time()  # latest available

        try:
            tf = self._buffer.lookup_transform(
                "world", "sensor", when, timeout=Duration(seconds=TIMEOUT_S)
            )
        except ExtrapolationException as exc:
            self.get_logger().warning(f"EXTRAPOLATION: {exc}")
            return
        except LookupException as exc:
            self.get_logger().error(f"LOOKUP: {exc}")
            return

        t = tf.transform.translation
        self.get_logger().info(f"OK: sensor in world = [{t.x:.3f}, {t.y:.3f}, {t.z:.3f}]")


def main() -> None:
    rclpy.init()
    node = WorldSensorListener()
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
```

## How to run

```bash
source /opt/ros/jazzy/setup.bash
# Terminal A:
python3 broadcaster.py
# Terminal B:
python3 listener.py
```

Flip the constants at the top of each file to move between sabotage and fix, restart the affected node, and capture the log.

## Why this matters

`ExtrapolationException` is not an exotic edge case — it is the daily reality of timestamped data flowing between asynchronous nodes:

- A **sensor driver** that stamps with the *driver receive time* instead of the *hardware capture time* produces a transform that is always a few milliseconds stale; a fast consumer asking for "now" hits future extrapolation. (This is Sabotage A in the wild, and it is why REP 103/105 care so much about honest stamping.)
- A **Nav2 costmap** that buffers a 10 s window will throw past-extrapolation if a transform required for an old sensor reading has aged out — exactly Sabotage B. The Nav2 fix is the `transform_tolerance` parameter, which is this challenge's timeout in disguise.
- A node that comes up **before** its upstream broadcaster — a camera-to-map projector started before the localization node — hits the startup race of Sabotage C every cold boot. The fix is the lookup timeout, which is why every well-written tf2 listener in Nav2 and MoveIt2 passes one.

By the end of this challenge, when a teammate pastes an `ExtrapolationException` into the team channel, you will ask one question — "future or past?" — and you will already know the fix.

## Stretch

- Add a `--cache-time` parameter to the listener and demonstrate that Sabotage B becomes survivable when the cache window exceeds the lookup offset. Capture the threshold (it should be right around 30 s).
- Use `ros2 run tf2_ros tf2_monitor world sensor` while Sabotage A runs and read the reported *delay*. Confirm it shows roughly the 2 s stale offset. `tf2_monitor` is the tool that catches stale stamps without writing a single line of code.
- Reproduce Sabotage A but with the broadcaster on a deliberately wrong clock (set `use_sim_time` true with no `/clock` publisher) and explain why this is the same bug wearing a different hat.
