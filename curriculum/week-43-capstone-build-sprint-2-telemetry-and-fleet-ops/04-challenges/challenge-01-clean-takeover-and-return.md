# Challenge 1 — Clean Takeover and Return

> **Estimated time:** 90–120 minutes. Worth more than its time-cost suggests: this is the exact capability Week 46's chaos drill grades live, and "the takeover left the robot in a weird state" is the single most common capstone-defense fail in the fleet-ops section.

You built the control-authority arbiter in exercise 3. This challenge proves it is *safe*. A button that flips a variable is easy; proving that the flip never leaves the robot in an inconsistent or unsafe state — in *either* direction — is the senior work. You will demonstrate the full cycle (autonomy → teleop → autonomy) and back it with an MCAP recording and an automated checker that anyone can re-run.

## The property you must prove

Across a takeover and a return, **all five** of these must hold:

1. **Autonomy pauses.** When authority flips to TELEOP, the autonomy behavior tree halts its navigation subtree (the Nav2 goal is *cancelled cleanly*, not abandoned). Autonomy stops *computing* drive commands, not merely stops being forwarded.
2. **Control transfers atomically.** There is no cycle in which `/cmd_vel_out` carries an autonomy command and a teleop command in overlap, and no cycle of blind coast. Every transition passes through exactly one zero `Twist` (the defined safe-stop).
3. **Teleop drives.** While authority is TELEOP, operator commands on `/cmd_vel_teleop` reach the base via `/cmd_vel_out`, *and* a teleop-link dropout safe-stops the robot within the watchdog window.
4. **Control returns cleanly.** When authority flips back to AUTONOMY, the BT un-halts, autonomy resumes from its *current* (re-localized) state — it must not assume it is where it was before the takeover — and there is again exactly one safe-stop cycle on the transition.
5. **The dashboard shows it.** The `/control/authority` banner changes the instant each flip happens; an operator watching Foxglove sees AUTONOMY → TELEOP → AUTONOMY with no ambiguous middle state.

## What to build

### Part A — The scenario

Set up a doorway-stall scenario in sim (or on hardware in a safe area): the robot is navigating to a goal, and an obstacle blocks the narrow passage so Nav2 cycles its recovery behaviors (this is Week 46's drill 2, rehearsed). The operator:

1. Watches the dashboard, sees the robot stuck (the costmap shows the block; the policy arrow oscillates).
2. Presses "take over": `ros2 topic pub -1 /control/takeover std_msgs/Bool "{data: true}"`.
3. Drives the robot back and around the obstacle with `teleop_twist_keyboard` remapped to `/cmd_vel_teleop`.
4. Presses "hand back": `ros2 topic pub -1 /control/takeover std_msgs/Bool "{data: false}"`.
5. Autonomy resumes and completes the goal.

### Part B — Record the evidence

Record the entire scenario as an MCAP from the `foxglove_bridge` (or `ros2 bag record -o takeover_run --storage mcap /cmd_vel_out /cmd_vel_auto /cmd_vel_teleop /control/authority /control/takeover /fleet/heartbeat`). This MCAP is your evidence and a dry run of the week-48 dashboard recording.

### Part C — The automated checker

Write `check_takeover.py` that reads the MCAP and *proves* properties 1–4 from the recorded messages. The checker is the heart of the challenge — it turns "looks fine" into "provably fine." A working skeleton:

```python
#!/usr/bin/env python3
"""check_takeover.py — verify a clean takeover/return from a recorded bag.

Reads /cmd_vel_out, /cmd_vel_auto, /cmd_vel_teleop, and /control/authority from an
MCAP and asserts the safety properties. Exit 0 = clean, non-zero = a violation.
"""
import sys

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import Twist
from std_msgs.msg import String

EPS = 1e-6  # treat |v| < EPS as a zero (safe-stop) command


def is_zero(tw: Twist) -> bool:
    return (abs(tw.linear.x) < EPS and abs(tw.linear.y) < EPS
            and abs(tw.angular.z) < EPS)


def load(path: str):
    reader = SequentialReader()
    reader.open(StorageOptions(uri=path, storage_id="mcap"),
                ConverterOptions("", ""))
    types = {"/cmd_vel_out": Twist, "/cmd_vel_auto": Twist,
             "/cmd_vel_teleop": Twist, "/control/authority": String}
    events = []  # (t_ns, topic, msg)
    while reader.has_next():
        topic, data, t = reader.read_next()
        if topic in types:
            events.append((t, topic, deserialize_message(data, types[topic])))
    events.sort(key=lambda e: e[0])
    return events


def main() -> int:
    events = load(sys.argv[1])

    # --- Property: authority went AUTONOMY -> TELEOP -> AUTONOMY ---
    authority_seq = [m.data for (_, top, m) in events if top == "/control/authority"]
    transitions = [a for i, a in enumerate(authority_seq)
                   if i == 0 or a != authority_seq[i - 1]]
    if transitions != ["AUTONOMY", "TELEOP", "AUTONOMY"]:
        print(f"FAIL: authority path was {transitions}, expected the full cycle")
        return 1

    # --- Property: every authority flip is followed by a zero on /cmd_vel_out
    #     BEFORE any non-zero from the new source (the one-cycle safe-stop). ---
    cur_authority = "AUTONOMY"
    saw_zero_since_flip = True
    for t, topic, msg in events:
        if topic == "/control/authority":
            if msg.data != cur_authority:
                cur_authority = msg.data
                saw_zero_since_flip = False     # arm: expect a zero next on cmd_out
        elif topic == "/cmd_vel_out":
            if is_zero(msg):
                saw_zero_since_flip = True
            elif not saw_zero_since_flip:
                print(f"FAIL: non-zero /cmd_vel_out after flip to {cur_authority} "
                      f"without a safe-stop at t={t}")
                return 1

    print("PASS: full AUTONOMY->TELEOP->AUTONOMY cycle with a safe-stop on each flip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Extend the checker to also assert property 3's watchdog: find a window where `/cmd_vel_teleop` goes silent for longer than the watchdog while authority is TELEOP, and confirm `/cmd_vel_out` went to zero within that window. (You can induce the dropout by stopping `teleop_twist_keyboard` mid-takeover during the recording.)

## Acceptance criteria

- [ ] The scenario runs end-to-end: robot stalls, operator takes over, drives clear, hands back, autonomy completes the goal.
- [ ] `check_takeover.py` exits **0** on your recorded MCAP, proving the authority cycle and the per-flip safe-stop.
- [ ] The checker is extended to verify the **teleop-link watchdog** safe-stops the robot when `/cmd_vel_teleop` goes silent under TELEOP authority.
- [ ] You demonstrate (in the recording) that on return to AUTONOMY, autonomy **re-localizes / re-plans** rather than blindly continuing — the resumed Nav2 goal is a fresh plan from the current pose.
- [ ] The **dashboard banner** (`/control/authority` Indicator) is visible changing AUTONOMY → TELEOP → AUTONOMY in the recording.
- [ ] No cycle of `/cmd_vel_out` ever carries overlapping autonomy+teleop commands (the checker proves this implicitly via the safe-stop assertion; state it explicitly in your writeup).
- [ ] A 200–300 word `writeup.md` covering: how you proved each property, one edge case you found (e.g., what happens if the operator presses takeover *during* the one-cycle safe-stop), and what you would add before trusting this on a real robot in a shared space.

## The edge cases that separate a pass from an A

These are the things a reviewer probes, and Week 46 will throw at you:

1. **Double-press.** The operator presses takeover twice in quick succession. Your arbiter's `request_authority` is idempotent, so the second press is a no-op — confirm it does *not* trigger a second safe-stop that would stutter the robot.
2. **Flip during a safe-stop.** The operator hands back to autonomy during the one-cycle safe-stop of the takeover they just initiated. Reason about (and test) what your state machine does. The clean answer: the pending flip resolves to the latest requested authority and a single safe-stop covers it.
3. **Teleop link dies under TELEOP.** Already in the criteria. The robot must halt, not coast. Prove the watchdog fires.
4. **Autonomy still publishing under TELEOP.** If your BT does *not* halt cleanly, autonomy keeps publishing `/cmd_vel_auto`. The arbiter correctly ignores it (authority is TELEOP), but the *dangling Nav2 goal* is a latent bug — on return, you get a stale goal. Prove your BT cancels the goal, not just stops ticking.
5. **The safety filter under teleop.** Confirm the obstacle-proximity clamp from your Week 41 safety case is still in the loop under TELEOP — a remote operator must not be able to drive into a wall. Forward teleop *through* the safety filter, not around it.

## Submission

Commit to your Week 43 GitHub repository at `challenges/challenge-01-takeover/` containing:

- `takeover_run.mcap` — the recorded scenario (or a link if it is large; keep it under 100 MB by trimming with the `mcap` CLI).
- `check_takeover.py` — your extended checker.
- `writeup.md` — the 200–300 word writeup.
- A one-line `README.md` with the exact command to re-run the checker.

The instructor reviews by running `python3 check_takeover.py takeover_run.mcap`, expecting exit 0, then scrubbing the MCAP in Foxglove to confirm the banner transitions and the absence of an overlap cycle. A submission whose checker passes but whose MCAP shows the robot lurching on a flip is the most common review-fail — the lurch means your safe-stop is not actually happening before the new source forwards.

---

**References**

- ROS2 Jazzy — managed (lifecycle) nodes: <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Node-Lifecycle.html>
- `twist_mux` — the priority-based mux you extended: <https://github.com/ros-teleoperation/twist_mux>
- `rosbag2` MCAP storage: <https://github.com/ros2/rosbag2>
- BehaviorTree.CPP — halting a subtree cleanly: <https://www.behaviortree.dev/docs/>
- MCAP CLI (trim/inspect): <https://github.com/foxglove/mcap/tree/main/go/cli/mcap>
