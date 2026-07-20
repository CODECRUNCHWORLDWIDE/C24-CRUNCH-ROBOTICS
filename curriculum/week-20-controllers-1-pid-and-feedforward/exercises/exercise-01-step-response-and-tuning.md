# Exercise 1 — Step Response and Tuning

**Goal:** Tune a PID controller for a realistic second-order plant until its step response meets a written specification, then read the four step-response metrics (rise time, overshoot, settling time, steady-state error) off the plot and confirm the second-order formulas from Lecture 1 §8 predict what you see. You will train the single most important controls habit of the week: changing one gain, watching the plot, and naming the symptom.

**Estimated time:** 45 minutes. Guided.

---

## The plant

We control a second-order system — the model for "a robot subsystem near an operating point" from Lecture 1 §8:

```
              ωn²
G(s) =  ─────────────────  ,   ωn = 4.0 rad/s,   ζ = 0.2  (underdamped, rings badly)
        s² + 2ζωn·s + ωn²
```

This plant, left to itself, overshoots massively and rings — exactly the kind of system PID is meant to civilize. Your job: design a PID so the *closed-loop* step response meets the spec below.

## The spec

| Metric | Target |
|---|---|
| Rise time (10–90%) | ≤ 0.6 s |
| Percent overshoot | ≤ 10 % |
| Settling time (2% band) | ≤ 1.5 s |
| Steady-state error | ≤ 1 % of the step |

A controller that meets all four is "in spec." A controller that meets three is not done.

---

## Step 1 — Build the simulation harness

Save this as `step_tune.py`. It simulates the closed loop and computes the four metrics. Read it — the metric code is the same `analyze_step` logic the whole week uses.

```python
#!/usr/bin/env python3
"""Tune a PID for a second-order plant against a step-response spec."""
import numpy as np
import matplotlib.pyplot as plt

DT = 0.002          # 500 Hz sim step
T_END = 4.0
WN = 4.0            # plant natural frequency
ZETA = 0.2          # plant damping (badly underdamped on purpose)


class SecondOrderPlant:
    """xdd + 2*zeta*wn*xd + wn^2 * x = wn^2 * u.  State = [x, xd]."""
    def __init__(self):
        self.x = 0.0
        self.xd = 0.0

    def step(self, u, dt):
        xdd = WN * WN * (u - self.x) - 2.0 * ZETA * WN * self.xd
        self.xd += xdd * dt
        self.x += self.xd * dt
        return self.x


class PID:
    def __init__(self, kp, ki, kd, dt, u_min=-10.0, u_max=10.0, tf=0.01):
        self.kp, self.ki, self.kd, self.dt = kp, ki, kd, dt
        self.u_min, self.u_max = u_min, u_max
        self.alpha = dt / (tf + dt) if tf > 0 else 1.0
        self.kb = 1.0 / ki if ki > 0 else 0.0
        self.integral = 0.0
        self.prev_meas = 0.0
        self.df = 0.0

    def update(self, sp, meas):
        e = sp - meas
        p = self.kp * e
        raw_d = -(meas - self.prev_meas) / self.dt          # derivative on measurement
        self.df += self.alpha * (raw_d - self.df)           # low-pass filter
        d = self.kd * self.df
        u_unsat = p + self.ki * self.integral + d
        u = max(self.u_min, min(self.u_max, u_unsat))
        self.integral += (e + self.kb * (u - u_unsat)) * self.dt   # back-calc anti-windup
        self.prev_meas = meas
        return u


def simulate(kp, ki, kd, setpoint=1.0):
    plant = SecondOrderPlant()
    pid = PID(kp, ki, kd, DT)
    n = int(T_END / DT)
    t = np.arange(n) * DT
    y = np.zeros(n)
    meas = 0.0
    for k in range(n):
        u = pid.update(setpoint, meas)
        meas = plant.step(u, DT)
        y[k] = meas
    return t, y


def analyze_step(t, y, setpoint=1.0):
    """Return (rise_time, pct_overshoot, settling_time, ss_error)."""
    # Rise time 10% -> 90%.
    try:
        t10 = t[np.argmax(y >= 0.1 * setpoint)]
        t90 = t[np.argmax(y >= 0.9 * setpoint)]
        rise = t90 - t10
    except (IndexError, ValueError):
        rise = float("nan")
    # Percent overshoot.
    peak = np.max(y)
    overshoot = max(0.0, (peak - setpoint) / setpoint) * 100.0
    # Settling time: last time it leaves the 2% band.
    band = 0.02 * setpoint
    outside = np.where(np.abs(y - setpoint) > band)[0]
    settling = t[outside[-1]] if len(outside) else 0.0
    # Steady-state error: mean of last 10% of the trace.
    ss_error = abs(setpoint - np.mean(y[int(0.9 * len(y)):]))
    return rise, overshoot, settling, ss_error


def report(kp, ki, kd):
    t, y = simulate(kp, ki, kd)
    rise, os, ts, ss = analyze_step(t, y)
    print(f"gains Kp={kp} Ki={ki} Kd={kd}")
    print(f"  rise (10-90%):   {rise:.3f} s   (spec <= 0.6)   {'PASS' if rise <= 0.6 else 'FAIL'}")
    print(f"  overshoot:       {os:.1f} %     (spec <= 10)    {'PASS' if os <= 10 else 'FAIL'}")
    print(f"  settling (2%):   {ts:.3f} s     (spec <= 1.5)   {'PASS' if ts <= 1.5 else 'FAIL'}")
    print(f"  steady-state:    {ss*100:.2f} % (spec <= 1)     {'PASS' if ss <= 0.01 else 'FAIL'}")
    return t, y


if __name__ == "__main__":
    # TODO 1: replace these starter gains and tune until ALL FOUR metrics PASS.
    KP, KI, KD = 1.0, 0.0, 0.0
    t, y = report(KP, KI, KD)
    plt.axhline(1.0, color="k", ls="--", lw=0.8, label="setpoint")
    plt.axhline(1.02, color="gray", ls=":", lw=0.6)
    plt.axhline(0.98, color="gray", ls=":", lw=0.6, label="2% band")
    plt.plot(t, y, label=f"Kp={KP} Ki={KI} Kd={KD}")
    plt.xlabel("time (s)"); plt.ylabel("output"); plt.legend(); plt.grid(True)
    plt.title("Step response"); plt.show()
```

```bash
python3 step_tune.py
```

With the starter gains (`Kp=1, Ki=0, Kd=0`) you'll see a slow, offset response that fails most of the spec. Good — now tune it.

---

## Step 2 — Tune with the structured loop (Lecture 2 §2.1)

Follow the procedure, changing **one gain at a time** (`TODO 1`):

1. **Raise `Kp`** (try 2, 4, 8) until the response is fast and *just* starts to overshoot. Watch the rise time drop and the overshoot climb. Notice the steady-state offset that `Kp` alone can't kill.
2. **Add `Kd`** (try 0.2, 0.5, 1.0) to damp the overshoot. Watch the peak come down. Too much `Kd` and the response goes sluggish — that's your ceiling.
3. **Add a little `Ki`** (try 0.5, 1, 2) to drive the steady-state error to zero. Watch the offset close. Too much and the overshoot returns.
4. **Re-check all four metrics.** Iterate until every line says PASS.

A known-good neighborhood (don't just copy it — *arrive* at it, then compare): something near `Kp≈8, Ki≈4, Kd≈1.2` meets the spec for this plant. Your numbers will differ; what matters is that you can explain *why each gain is where it is*.

---

## Step 3 — Connect the plot to the formulas

For your tuned response, the closed loop behaves approximately like a second-order system with some effective `ζ` and `ωn`. From Lecture 1 §8:

```
percent overshoot ≈ exp( −π·ζ / sqrt(1 − ζ²) ) × 100%
settling time (2%) ≈ 4 / (ζ·ωn)
```

- From your measured **overshoot**, solve for the effective `ζ`. (For ~8% overshoot, ζ ≈ 0.62.)
- From your measured **settling time** and that `ζ`, solve for the effective `ωn`.
- Confirm the numbers are in the right ballpark. They won't be exact — your closed loop is third-order once you add the integrator — but they'll be close, and the *exercise* is seeing that the formulas have predictive power.

Write the two solved values into a comment at the bottom of your `step_tune.py`.

---

## Step 4 — Watch a gain misbehave

Deliberately break it to cement the symptom→gain map:

- Set `Ki` to 5× your tuned value. Observe the overshoot return and the settling time blow up. **Symptom: integral-induced overshoot.**
- Set `Kd` to 0 with your tuned `Kp`/`Ki`. Observe the overshoot. **Symptom: missing damping.**
- Set `Kp` to 10× your tuned value. Observe the oscillation. **Symptom: proportional instability.**

Each of these is a plot you should be able to *diagnose at a glance* by Friday.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `python3 step_tune.py` prints **PASS** on all four metrics with your tuned gains.
- [ ] You can state which gain you changed to fix each metric (rise → `Kp`; overshoot → `Kd`/`Kp`; offset → `Ki`).
- [ ] You computed the effective `ζ` and `ωn` from the overshoot and settling formulas and they're in the right ballpark.
- [ ] You produced the three "broken" plots in Step 4 and can name the symptom in each.
- [ ] Your tuned step-response plot is saved (e.g. `step_response.png`).

---

## Stretch

- Replace your hand-tuning with `scipy.optimize.minimize` over an ITAE cost (Lecture 2 §2.3) and compare the auto-tuned gains to yours. Where does the optimizer beat you? Does it produce a `Kd` you'd actually ship?
- Run Ziegler–Nichols on this plant: find the ultimate gain `Ku` (raise `Kp` with `Ki=Kd=0` until sustained oscillation) and period `Tu`, apply the Z–N PID table, and observe how aggressive (overshoot-heavy) the Z–N gains are versus your hand-tuned ones.
- Add measurement noise (`meas += np.random.normal(0, 0.01)`) and watch your `Kd` term start to chatter. Lower the filter cutoff (`tf`) until it's clean again. This is why the filter exists.

---

When this feels comfortable, move to [Exercise 2 — Anti-windup and derivative kick](exercise-02-antiwindup-and-derivative-kick.py).
