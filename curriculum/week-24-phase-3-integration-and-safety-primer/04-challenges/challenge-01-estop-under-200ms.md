# Challenge 1 — Stop Both Halves Under 200 ms, Measured

**Time estimate:** ~2 hours (after the composed stack and the E-stop node are working). **No starter file beyond Exercise 3** — you wire this from your own composed graph.

## The challenge

Drive the composed base+arm robot through a motion in which **both halves are moving at once** — the base translating under Nav2 and the arm executing a MoveIt2 trajectory — then latch `/safety/estop` mid-motion and prove that **both** the base and the arm reach a full stop within **200 milliseconds** of the latch. You must report a *distribution* over ten trials, not a single lucky number, and you must demonstrate that the budget holds **under load**, not only on an idle machine.

That is the easy half. The hard half — the half this challenge grades — is that your evidence is *measured and reproducible*. A reviewer must be able to run your harness on your stack and get the same shape of number. "It stops fast" is not evidence. "p95 = 58 ms, max = 61 ms over 10 trials mid-motion, 71 ms max under a `stress-ng` load, here is `measure_estop_latency.py`" is evidence.

## Why this is the right challenge for Week 24

The Phase 3 milestone is not "the robot drives and reaches." It is "the robot drives and reaches *and you can stop it on demand within a budget you measured*." A fail-safe you never measured is a hope, not a safety control — and a hope is exactly what a capstone panel (and a real deployment review) will reject. This challenge isolates the load-bearing safety property and forces you to prove it before the mini-project asks you to sign the milestone against it. A senior robotics engineer measures the stop before trusting it; this challenge makes you do it in that order.

## What you must build (architect it yourself)

You already have the pieces from Exercises 1–3. The challenge is the rig:

1. **The composed stack**, brought up under your lifecycle manager in the safety-first order (Lecture 1 §1.5): the safety wrapper activates before the BT can dispatch a motion.
2. **A simultaneous motion**: the top-level drive-reach-return tree (Lecture 1 §1.7), but instrumented so that at the moment you latch the E-stop, the base is translating *and* the arm is mid-trajectory. (Sequence them to overlap, or run the base nav and a slow arm sweep in parallel under a `Parallel` BT node.)
3. **The E-stop monitor** (Exercise 3) wired to cancel both the `NavigateToPose` goal and the `FollowJointTrajectory` goal directly on latch, plus the zero-`/cmd_vel` backstop.
4. **A measurement harness** (`measure_estop_latency.py`, from Exercise 3) that latches the topic with a timestamp and records, separately, the time to (a) the first zero `/cmd_vel` (base stopped) and (b) the arm goal reaching `CANCELED` state (arm stopped). The reported latency is the *later* of the two — the robot is not stopped until *both* halves are.
5. **A load generator**: `stress-ng --cpu $(nproc) --timeout 60s` running during a second set of trials, to measure the budget under realistic CPU contention.

## Acceptance criteria

Each criterion must be demonstrable by a command you run or a recording you play. If you cannot demonstrate it, it is not met.

- [ ] **Both halves move at latch.** A recording or log shows the base translating (`/cmd_vel.linear.x > 0`) and the arm trajectory `EXECUTING` at the instant `/safety/estop` is latched.
- [ ] **Both halves stop.** After the latch, `/cmd_vel` goes to zero AND the arm `FollowJointTrajectory` goal reaches `CANCELED`. Neither half keeps moving.
- [ ] **The base latency is measured.** Ten trials, mid-motion, reporting latch → first-zero-`/cmd_vel` mean, p95, and max.
- [ ] **The arm latency is measured.** Ten trials, reporting latch → arm-goal-`CANCELED` mean, p95, and max.
- [ ] **The robot-stopped latency is under 200 ms.** The *later* of the two per trial (the moment both are stopped); worst case over ten trials ≤ 200 ms.
- [ ] **The latch is durable.** `/safety/estop` is `RELIABLE`/`TRANSIENT_LOCAL`; demonstrate a controller node that subscribes *after* the latch still receives `true` (start it late, confirm it stops).
- [ ] **The budget holds under load.** Repeat ten trials with `stress-ng` saturating the CPU; report the latency and state whether the budget still holds. If it does not, that is an honest finding with a Phase-6 action item — not a fail to hide.
- [ ] **The harness is reproducible.** `measure_estop_latency.py` is committed; a reviewer runs it and gets the same shape of number.

## The trap (read after a first attempt)

The subtle failure is measuring only the *base*. The base zeroes `/cmd_vel` fast — that's the easy half. The arm is the one that bites: if your E-stop only zeroes `/cmd_vel` and forgets to cancel the `FollowJointTrajectory` goal, the *arm keeps executing its trajectory* while you happily report "62 ms, passed" from the base measurement. The robot is not stopped; half of it is still moving toward a person. **The robot-stopped latency is the latency of the slower half.** Measure both, report the max, and make sure your E-stop cancels the arm goal directly (not only via the BT tick, which is too slow). Prescribing "the base stopped, so we're good" is the wrong claim and you must not write it.

## Stretch

- Add a **fail-safe-state** variant on a *non-E-stop* soft fault (a simulated perception dropout): instead of fail-stop, command the arm to retract to a tucked pose before halting, and contrast the latency and the appropriateness with the fail-stop E-stop. Write which fault gets which category and why (Lecture 2 §2.2).
- Re-run the whole challenge with the E-stop topic deliberately set to `VOLATILE` and start the controller late: show the controller *misses* the latch and keeps moving — the severity-9 "E-stop missed by a late-joining node" hazard, reproduced, then fixed by switching back to `TRANSIENT_LOCAL`.
- Wire the E-stop through `twist_mux` as the highest-priority `/cmd_vel` input and show that even a misbehaving lower-priority publisher cannot override the zero command while latched.

## Why this matters

At the Phase 3 milestone you defend your controller stack and your hazard log to a reviewer. The reviewer will not accept "the robot stops when I press the button." They will ask "within how long, measured how, and does it hold when the arm is mid-trajectory and the CPU is pegged?" This challenge *is* that conversation, rehearsed — and eight weeks out, it is the exact measurement the capstone's 200 ms safety clause is graded on at Week 48. Every robot that operates near people eventually has its stop time questioned by someone whose job is to find the case where it doesn't hold. The engineer who already measured it, mid-motion, under load, ten trials, is the one who keeps the deployment.
