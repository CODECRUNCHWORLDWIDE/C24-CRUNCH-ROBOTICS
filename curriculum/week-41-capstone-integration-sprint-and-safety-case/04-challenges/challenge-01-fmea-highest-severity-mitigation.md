# Challenge 1 — FMEA the Stack, Kill the Worst Failure Mode

**Time estimate:** ~2–3 hours.

## Problem statement

Run a Failure Mode and Effects Analysis (FMEA) across your **integrated** capstone autonomy stack — not one subsystem, the whole thing: perception, localization, planning, control, the learned policy, the safety filter, compute, power, and network. From that FMEA, identify the **single highest-severity failure mode**. Then design and implement a mitigation that **demonstrably reduces its risk rating**, and document the before/after with evidence.

"Demonstrably" is the load-bearing word. You are not allowed to assert that the risk went down. You must *show* it — with a test that now passes that previously failed, a measurement that crossed a threshold, or a detection that now fires when it previously did not. The before and after RPN must be computed by the *same* scoring method (use the exercise-3 tool) so the comparison is honest.

## Why "highest severity," not "highest RPN"?

RPN can hide a fatal failure behind an optimistic occurrence guess (S10 × O2 × D2 = 40, below your cutoff — yet it's a *fatality*). The challenge deliberately targets the highest-**severity** mode, because severity is the one factor you cannot negotiate: a failure that can kill someone deserves attention regardless of how rare you *think* it is. For most C24 stacks, the highest-severity mode is one of:

- **The safety filter / classical fallback fails to engage when the learned policy is unsafe.** (Severity is maximal — it is the last line of defense — and detection is genuinely hard, because a silent non-firing looks identical to "wasn't needed.")
- **The arm falls under gravity on power loss** (brake fails), or
- **The base accelerates uncommanded** (a stuck `cmd_vel`, a controller that republishes a stale command after the stop latches).

If your FMEA puts a different mode at the top of the severity column, attack that one — the method is what's graded, not which mode you pick.

## Required deliverables

Commit all of this under `safety-case/challenge-01/` in your capstone repo.

1. **`fmea.yaml`** — your full integrated-stack FMEA, in the exercise-3 format, with at least **12 rows** spanning at least 6 distinct subsystems (perception, localization, planning, control, policy, safety, compute, power, network — pick at least 6).
2. **`fmea-before.md`** — the generated table (run the exercise-3 tool on `fmea.yaml`), sorted, with criticality flags. This is the "before."
3. **A one-page `analysis.md`** that:
   - Names the single highest-severity failure mode and explains *why* it is the worst (what makes its severity maximal, and why its current detection is poor).
   - Describes the **root cause** precisely. "It might fail" is not a root cause. "The safety filter subscribes to `/policy/action` but the policy publishes a high-rate burst on `/policy/action_fast` under load that the filter never sees" is a root cause.
   - Describes the **mitigation** you designed and *why it is independent* of the existing controls (if it shares a common cause with what already failed, it is not a real mitigation — say so and pick a better one).
4. **The mitigation, implemented and runnable.** Code (a `rclpy` node, a BT.CPP condition, a Nav2 config, a contactor wiring change — whatever fits the mode) committed and demonstrably wired into your stack.
5. **`evidence/`** — the proof the mitigation works:
   - A test (script, `pytest`, or a recorded `ros2 bag` + a plot) that **fails without** the mitigation and **passes with** it. The delta is the evidence.
   - For a detection improvement: show the failure being *injected* and the mitigation *catching* it (a log line, a latched E-stop state on `/safety/estop_state`, a dashboard trigger).
6. **`fmea-after.md`** — the regenerated table after the mitigation, with the targeted row's S / O / D updated to reflect the new reality, and the new RPN. The reduction must be justified per factor (usually you reduce **Detection** — the mitigation now catches the failure — and sometimes **Occurrence**; you almost never reduce **Severity** without an inherent-design change).
7. **A before/after summary table** in `analysis.md`:

   | | Failure mode | S | O | D | RPN | Critical? |
   |---|---|---|---|---|---|---|
   | Before | … | 10 | 3 | 7 | 210 | YES |
   | After | … | 10 | 3 | 2 | 60 | (still YES if S≥9) |

   Note: if severity stays at 10, the row may *still* be flagged critical after — and that's honest. The point is not to make the flag go away; it's to reduce the *risk* and show your work. A mitigation that drops detection from 7 to 2 has cut the RPN by 70% even if the severity gate keeps the row on the watch list forever (as it should — you watch your worst failure mode forever).

## Acceptance criteria

- [ ] `fmea.yaml` has ≥ 12 rows across ≥ 6 subsystems; `--selftest` of your tool still passes.
- [ ] `fmea-before.md` and `fmea-after.md` are both *generated* (not hand-edited) from YAML by the exercise-3 tool.
- [ ] `analysis.md` names the highest-severity mode, gives a *specific* root cause, and argues the mitigation's **independence** explicitly.
- [ ] The mitigation is implemented and wired into the stack, not just described.
- [ ] `evidence/` contains a test or recording that **fails without** the mitigation and **passes with** it. Both states are shown.
- [ ] The after-RPN reduction is justified per S/O/D factor (which one changed and why).
- [ ] The before/after table is in `analysis.md`.

## A worked example of "demonstrably"

Suppose your highest-severity mode is **"safety filter fails to engage."** Root cause: the filter only checks the policy action on `/policy/action`, but a corner case publishes on a faster topic the filter doesn't see, so an unsafe action slips through.

- **Before:** Write a test that publishes an unsafe action on the fast topic. Observe that no E-stop latches — the unsafe action would reach the actuators. `evidence/before.log` shows `/safety/estop_state: false` throughout. D = 7 (the failure is invisible).
- **Mitigation:** Add a *mux/monitor* that the policy *cannot* bypass — every motion command, regardless of topic, passes through a single arbitration node that re-checks the safety filter and the latch. Now there is no fast path around the filter. (Argue independence: this monitor is a separate node; but note it shares the "Linux hang" common cause with the rest of the software, so the *hardware* E-stop remains the independent backstop — don't oversell.)
- **After:** Re-run the same test. `evidence/after.log` shows the E-stop latching within one tick of the unsafe action, `/cmd_vel_safe` going to zero. D drops from 7 to 2 (the failure is now caught at the mux). RPN 210 → 60. The severity stays 10, so the row stays on the critical watch list — correctly.

That before/after — same test, opposite outcome, RPN cut, severity honestly unchanged — *is* the challenge. Reproduce that shape for whatever your worst mode turns out to be.

## Stretch

- Run an **STPA** (System-Theoretic Process Analysis, from the STPA Handbook in resources) on the same subsystem and find an *unsafe control action* that the FMEA missed because no single component "failed." Add it to the analysis. This is the move that separates a senior safety case from a checkbox one.
- Make the mitigation's test part of CI: the unsafe-action injection runs on every commit and fails the build if the E-stop ever stops latching. A safety mitigation with a regression test is a safety mitigation that stays alive.
- If your worst mode is a *hardware* one (brake fails on power loss), build the test rig: cut power on command and measure arm sag with an encoder log. Real measurement, real evidence.

## Why this matters

This challenge is the single best interview story you will produce in C24. Walk into a robotics-startup interview and say: "The scariest failure mode in our stack was the safety filter silently not engaging. Here's the FMEA, here's the root cause, here's the independent mitigation we added, and here's the before/after test where the unsafe action used to slip through and now latches the E-stop in one tick." That is the answer that gets you hired to own robots that move near people — because it proves you can find the worst thing, attack it correctly, and *prove* the attack worked. Everything else on your résumé is "I used a library." This is "I made it safer, and here's the evidence."
