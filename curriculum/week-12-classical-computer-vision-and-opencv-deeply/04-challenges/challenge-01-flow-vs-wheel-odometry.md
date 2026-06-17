# Challenge 1 — Flow Velocity vs Wheel Odometry: Catch the Slip

**Time estimate:** ~90 minutes.

## Problem statement

A robot drove forward at a commanded 1.5 m/s. Its wheel odometry dutifully reported 1.5 m/s the whole time. But somewhere in the middle of the drive, the wheels hit a slick patch and **slipped** — they kept spinning, so the encoders kept reporting motion, but the robot barely moved. Wheel odometry *cannot see this*; an encoder measures wheel rotation, not body motion (Week 6). You are the perception engineer. Using nothing but the camera and the optical-flow ego-motion estimate from Lecture 2 §4.1, **find the slip window** — the frames where the true motion diverged from what the wheels claimed.

This is the optical-flow-vs-wheel-odometry cross-check, and it's a microcosm of a senior robotics skill: *no single sensor is trustworthy; you catch lies by cross-checking independent sensors that should agree.*

## The harness

Save this as `slip_harness.py`. It renders a forward-drive image sequence from the *true* motion (with a planted slip) and supplies the *lying* wheel odometry alongside. **Do not read the `true_v` slip window until you've detected it from the flow** — that's the whole point.

```python
#!/usr/bin/env python3
"""Renders a forward-drive sequence with a planted wheel-slip window, plus the
(lying) wheel odometry. Detect the slip from the optical flow alone."""
import cv2
import numpy as np

RNG = np.random.default_rng(7)
W, H = 640, 480
CX, CY = W / 2.0, H / 2.0
DT = 0.1            # 10 FPS
DEPTH_Z = 5.0       # meters to the plane the camera drives toward
COMMANDED_V = 1.5   # m/s the wheels report the whole time


def _make_true_velocity():
    """TRUE forward velocity per frame. DO NOT PEEK before detecting the slip."""
    v = np.full(15, COMMANDED_V)
    v[6:10] = 0.3   # <-- the planted slip: body barely moves, wheels keep spinning
    return v


def make_world():
    """Returns (frames, wheel_odom_v). frames render the TRUE motion; wheel_odom_v
    is what the encoders report (constant COMMANDED_V — the lie)."""
    base = np.full((H, W), 30, np.uint8)
    for _ in range(220):
        x, y = int(RNG.integers(0, W)), int(RNG.integers(0, H))
        cv2.circle(base, (x, y), int(RNG.integers(3, 8)), int(RNG.integers(120, 255)), -1)

    true_v = _make_true_velocity()
    frames = [base]
    acc = 1.0
    for v in true_v[1:]:
        s = DEPTH_Z / (DEPTH_Z - v * DT)     # apparent zoom from true forward motion
        acc *= s
        M = cv2.getRotationMatrix2D((CX, CY), 0, acc)
        frames.append(cv2.warpAffine(base, M, (W, H)))

    wheel_odom_v = np.full(len(true_v), COMMANDED_V)   # the encoders' (lying) report
    return frames, wheel_odom_v


if __name__ == "__main__":
    frames, wheel_v = make_world()
    print(f"{len(frames)} frames, wheel odometry reports a constant "
          f"{wheel_v[0]:.1f} m/s")
    # YOUR CODE: estimate flow velocity per frame, compare to wheel_v, flag the slip.
```

```bash
pip install opencv-python numpy
python3 slip_harness.py
```

## Your task

Write `catch_slip.py` that imports `make_world` and:

1. **Estimate flow velocity per frame.** Reuse the Exercise 3 method: track Shi-Tomasi corners with pyramidal LK frame-to-frame, recover the radial scale `s` from the flow about the focus of expansion, invert `s = Z/(Z − v·dt)` to a per-frame forward velocity.
2. **Build the comparison table.** Print, per frame: the wheel-odometry velocity, the flow velocity, and the absolute difference.
3. **Flag the slip.** Mark every frame where `|wheel_v − flow_v|` exceeds a threshold (e.g. 0.5 m/s). Those flagged frames are the slip window.
4. **Quantify.** Report the slip window you detected (start/end frame), and confirm it matches the planted one once you reveal `_make_true_velocity` *after* detecting it.

## Acceptance criteria

- [ ] A `catch_slip.py` that prints a per-frame wheel-vs-flow comparison table.
- [ ] The flow velocity tracks ~1.5 m/s outside the slip and drops to ~0.3 m/s inside it; the wheel odometry stays at 1.5 m/s throughout.
- [ ] Your disagreement detector flags **exactly frames 6–9** as the slip window (the planted `true_v[6:10] = 0.3`), with no false positives on the normal-driving frames.
- [ ] A `challenge-01-writeup.md` answering: *(a)* why wheel odometry physically cannot detect this slip; *(b)* why optical flow can (it measures apparent world motion, which slip doesn't fake); *(c)* what you'd do on a real robot when the two disagree (don't trust the slipping sensor; degrade gracefully; alert the operator — the Week 46 chaos-drill instinct).
- [ ] Committed to your Week 12 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The naive detector flags a frame whenever the two velocities differ at all — and then it false-positives on *every* frame, because flow is noisy and even in normal driving the flow estimate wobbles by ±0.05 m/s around the truth. **The threshold matters.** Set it too tight (0.05 m/s) and you flag noise as slip; too loose (1.4 m/s) and you miss a mild slip. The right threshold is a few times the normal-driving flow noise — which you can *measure* from the non-slip frames. A good writeup states the noise floor you measured and the threshold you chose relative to it. This is exactly the deadline-tuning lesson from Week 5 (set the threshold above normal jitter so you don't spam false alarms), applied to a different sensor.

## Stretch

- **Two slips.** Edit the harness to plant a *second*, milder slip (`true_v[12] = 0.9`). Show your detector catches the obvious one and tune the threshold so it also catches the mild one without false-positiving — the precision/recall trade-off, live.
- **Real video.** Record a short forward-drive clip from your robot's camera (or a phone), run the flow estimator on it, and compare to the robot's `/odom`. On a real drive you won't have a clean planted slip, but you'll see the flow estimate track odometry — and any genuine disagreement is a real event worth investigating.
- **Direction too.** Extend the estimate to detect *turning* (the focus of expansion shifts off-center when the robot turns). A wheel that slips during a turn is even nastier; catching it needs the 2D flow field, not just the radial scale.

## Why this matters

In Week 16 you defend a *fused* perception stack. The reviewer's sharpest question is "how do you know your state estimate isn't lying?" — and the honest answer is always "I cross-check independent sensors." This challenge is that cross-check in its simplest form: one sensor (wheels) that can be fooled, one sensor (camera flow) that can't be fooled the same way, and the discipline to trust neither blindly. Every chaos drill in Phase 6 — sensor dropout, planner deadlock — is ultimately about detecting that a component has gone wrong from the *outside*, using a signal it can't corrupt. The engineer who built the cross-check sleeps through the 3 a.m. page; the one who trusted a single sensor gets woken up.
