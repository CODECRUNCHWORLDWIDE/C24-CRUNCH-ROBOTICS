#!/usr/bin/env python3
# Exercise 2 — Integrator wind-up and derivative kick (reproduce, then fix)
#
# Goal: See the two PID failure modes from Lecture 1 with your own eyes, in a
#       simulation, then fix them and watch the fix work. You will:
#         * reproduce INTEGRATOR WIND-UP by saturating the actuator with a naive
#           integrator, and fix it with BACK-CALCULATION anti-windup;
#         * reproduce DERIVATIVE KICK by stepping the setpoint with derivative-on-
#           error, and fix it with DERIVATIVE-ON-MEASUREMENT.
#
# Estimated time: 45 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone. No ROS, no robot. Just numpy + matplotlib:
#
#       python3 exercise-02-antiwindup-and-derivative-kick.py
#
#   It runs four simulations and reports metrics for each:
#       (A) naive PID, large step  -> WIND-UP: huge overshoot
#       (B) anti-windup PID, same  -> overshoot controlled
#       (C) derivative-on-error    -> KICK: command spikes on the setpoint step
#       (D) derivative-on-measure  -> no command spike
#   It prints PASS only when (B) tames the wind-up AND (D) removes the kick.
#
#   Two TODOs are marked in the FixedPID class. Until you fill them in, the
#   FixedPID behaves like the NaivePID and the program prints FAIL.
#
# ACCEPTANCE CRITERIA
#
#   [ ] (A) naive PID overshoots massively on the large step (wind-up reproduced).
#   [ ] (B) anti-windup PID keeps overshoot under the threshold (wind-up fixed).
#   [ ] (C) derivative-on-error produces a large |u| spike at the setpoint step.
#   [ ] (D) derivative-on-measurement produces NO such spike (kick fixed).
#   [ ] The program prints "PASS: wind-up tamed and kick removed" and exits 0.
#
# Expected output is at the bottom of the file.

import sys

import numpy as np

try:
    import matplotlib.pyplot as plt
    HAVE_PLT = True
except ImportError:  # plotting is optional; the metrics still print.
    HAVE_PLT = False

DT = 0.002
T_END = 5.0
# A first-order-ish plant with a HARD actuator limit, so wind-up can happen.
PLANT_GAIN = 2.0       # output velocity per unit command
U_MIN, U_MAX = -1.0, 1.0   # tight saturation -> easy to wind up


class Plant:
    """Simple integrator-with-gain plant: y_dot = PLANT_GAIN * u (u saturated)."""

    def __init__(self) -> None:
        self.y = 0.0

    def step(self, u: float, dt: float) -> float:
        u = max(U_MIN, min(U_MAX, u))   # the actuator physically saturates here
        self.y += PLANT_GAIN * u * dt
        return self.y


class NaivePID:
    """Textbook PID. Integrates regardless of saturation; differentiates the error.
    This is the version that winds up and kicks. It is the bug, on purpose."""

    def __init__(self, kp, ki, kd, dt):
        self.kp, self.ki, self.kd, self.dt = kp, ki, kd, dt
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, sp, meas):
        error = sp - meas
        self.integral += error * self.dt                       # winds up while saturated
        derivative = (error - self.prev_error) / self.dt       # derivative ON ERROR -> kick
        u = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return u


class FixedPID:
    """The shippable PID: back-calculation anti-windup + derivative-on-measurement.

    Fill in the two TODOs to fix wind-up and kick. Until you do, this class
    reproduces the naive behaviour and the program reports FAIL.
    """

    def __init__(self, kp, ki, kd, dt):
        self.kp, self.ki, self.kd, self.dt = kp, ki, kd, dt
        self.kb = 1.0 / ki if ki > 0 else 0.0   # back-calculation gain
        self.integral = 0.0
        self.prev_meas = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_meas = 0.0

    def update(self, sp, meas):
        error = sp - meas
        p = self.kp * error

        # TODO 1: derivative ON MEASUREMENT (not on error) to kill derivative kick.
        #   Replace the line below (which differentiates the ERROR and kicks) with a
        #   derivative of the negative MEASUREMENT:
        #       raw_d = -(meas - self.prev_meas) / self.dt
        raw_d = (error - (sp - self.prev_meas)) / self.dt   # <-- BUG: still kicks; fix it
        d = self.kd * raw_d

        u_unsat = p + self.ki * self.integral + d
        u = max(U_MIN, min(U_MAX, u_unsat))

        # TODO 2: back-calculation anti-windup. Replace the naive integral update
        #   below with one that bleeds the saturation excess back into the integral:
        #       self.integral += (error + self.kb * (u - u_unsat)) * self.dt
        self.integral += error * self.dt                    # <-- BUG: winds up; fix it

        self.prev_meas = meas
        return u


def run(controller_factory, setpoint_fn, label):
    """Simulate the closed loop. Returns (t, y, u_log)."""
    plant = Plant()
    ctrl = controller_factory()
    n = int(T_END / DT)
    t = np.arange(n) * DT
    y = np.zeros(n)
    u_log = np.zeros(n)
    meas = 0.0
    for k in range(n):
        sp = setpoint_fn(t[k])
        u = ctrl.update(sp, meas)
        u_log[k] = u
        meas = plant.step(u, DT)
        y[k] = meas
    return t, y, u_log


def overshoot_pct(y, setpoint):
    return max(0.0, (np.max(y) - setpoint) / setpoint) * 100.0


def main() -> None:
    kp, ki, kd = 1.5, 2.0, 0.05

    # A LARGE step (3.0) that drives the controller deep into saturation -> wind-up.
    big_step = lambda _t: 3.0
    # A step that arrives at t=1.0 s, to expose derivative kick at the transition.
    delayed_step = lambda t: 0.0 if t < 1.0 else 1.0

    # --- Wind-up: naive vs fixed on the large step -----------------------------
    tA, yA, uA = run(lambda: NaivePID(kp, ki, kd, DT), big_step, "A: naive (wind-up)")
    tB, yB, uB = run(lambda: FixedPID(kp, ki, kd, DT), big_step, "B: anti-windup")
    os_A = overshoot_pct(yA, 3.0)
    os_B = overshoot_pct(yB, 3.0)

    # --- Kick: derivative-on-error vs on-measurement at the step ----------------
    tC, yC, uC = run(lambda: NaivePID(kp, ki, kd, DT), delayed_step, "C: deriv-on-error (kick)")
    tD, yD, uD = run(lambda: FixedPID(kp, ki, kd, DT), delayed_step, "D: deriv-on-measure")
    # The kick shows up as the peak |u| right at the step (k near t=1.0 s).
    step_idx = int(1.0 / DT)
    window = slice(step_idx, step_idx + 5)
    kick_C = np.max(np.abs(uC[window]))
    kick_D = np.max(np.abs(uD[window]))

    print("==================== WIND-UP ====================")
    print(f"  (A) naive PID overshoot on 3.0 step:      {os_A:6.1f} %")
    print(f"  (B) anti-windup PID overshoot on 3.0 step:{os_B:6.1f} %")
    print("==================== DERIVATIVE KICK ============")
    print(f"  (C) deriv-on-ERROR   peak |u| at step:    {kick_C:6.2f}")
    print(f"  (D) deriv-on-MEASURE peak |u| at step:    {kick_D:6.2f}")
    print("=================================================")

    windup_fixed = os_A > 25.0 and os_B < 15.0          # B must tame A's overshoot
    kick_fixed = kick_C > 1.5 * kick_D + 0.5            # C kicks; D does not
    if windup_fixed and kick_fixed:
        print("PASS: wind-up tamed and kick removed. You shipped a real PID.")
        code = 0
    else:
        msgs = []
        if not windup_fixed:
            msgs.append("wind-up NOT fixed (fill in TODO 2: back-calculation)")
        if not kick_fixed:
            msgs.append("kick NOT fixed (fill in TODO 1: derivative on measurement)")
        print("FAIL: " + "; ".join(msgs))
        code = 1

    if HAVE_PLT:
        fig, ax = plt.subplots(2, 2, figsize=(11, 7))
        ax[0, 0].plot(tA, yA); ax[0, 0].axhline(3.0, color="k", ls="--", lw=0.8)
        ax[0, 0].set_title(f"(A) naive: wind-up, overshoot={os_A:.0f}%")
        ax[0, 1].plot(tB, yB); ax[0, 1].axhline(3.0, color="k", ls="--", lw=0.8)
        ax[0, 1].set_title(f"(B) anti-windup, overshoot={os_B:.0f}%")
        ax[1, 0].plot(tC, uC); ax[1, 0].set_title(f"(C) deriv-on-error u(t): kick={kick_C:.1f}")
        ax[1, 1].plot(tD, uD); ax[1, 1].set_title(f"(D) deriv-on-meas u(t): kick={kick_D:.1f}")
        for a in ax.flat:
            a.grid(True)
        fig.tight_layout()
        fig.savefig("windup_and_kick.png", dpi=110)
        print("saved windup_and_kick.png")

    sys.exit(code)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (after BOTH TODOs are correctly filled in)
# -----------------------------------------------------------------------------
#
# ==================== WIND-UP ====================
#   (A) naive PID overshoot on 3.0 step:        ~40-70 %
#   (B) anti-windup PID overshoot on 3.0 step:    ~5-12 %
# ==================== DERIVATIVE KICK ============
#   (C) deriv-on-ERROR   peak |u| at step:      large (tens)
#   (D) deriv-on-MEASURE peak |u| at step:      small (~Kp)
# =================================================
# PASS: wind-up tamed and kick removed. You shipped a real PID.
#
# Expected output (BEFORE you fix the TODOs)
# -----------------------------------------------------------------------------
#
# (B) overshoots almost as much as (A); (D) kicks almost as much as (C);
# FAIL: wind-up NOT fixed (...); kick NOT fixed (...)
#
# The lesson is visual: the naive integrator stores a push the actuator could
# never deliver, then dumps it as overshoot; the on-error derivative turns a
# setpoint step into an actuator impulse. Both fixes are one line each, and both
# are non-negotiable on real hardware.
# -----------------------------------------------------------------------------
