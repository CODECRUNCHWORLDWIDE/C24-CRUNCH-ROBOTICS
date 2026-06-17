# Challenge 1 — The Reward-Hacking Bestiary

**Time estimate:** ~90 minutes.

## Problem statement

You inherit a reach task: a 2-DOF planar arm (or, on Path B, a point-mass agent in a 2D plane) must move its end-effector to a target. A teammate wrote three candidate reward functions. All three produce **rising reward curves** in TensorBoard — they look like they're working. All three produce **wrong behavior** when you watch the rollout. Each is a different reward-hacking failure from the Lecture 2 §3.3 catalogue.

Your job is the senior reward-engineer's loop: **train, watch the rollout (not the curve), name the exploit, fix the reward, re-train, confirm.** You do this three times.

This is deliberately a *small* environment so you can train each variant in a couple of minutes on a laptop and iterate. The skill being graded is not RL throughput — it's reward judgment.

## The harness

Save this as `reach_bestiary.py`. It's a tiny gymnasium environment (a point-mass end-effector in a unit square reaching for a target) plus three reward functions with planted hacks. You train each with the PPO from Exercise 2 (import it, or use Stable-Baselines3 `PPO` — your call; the env is standard gymnasium).

```python
#!/usr/bin/env python3
"""Reach-task harness with three planted reward hacks. Train each, WATCH the
rollout, and diagnose the exploit from behaviour — not from the reward curve."""
import numpy as np
import gymnasium as gym
from gymnasium import spaces


class ReachEnv(gym.Env):
    """Point-mass end-effector in [-1,1]^2 reaching a fixed target. Action is a
    velocity command in [-1,1]^2; state is [pos(2), vel(2), target(2)]."""

    metadata = {"render_modes": []}

    def __init__(self, reward_mode: str = "good"):
        super().__init__()
        self.reward_mode = reward_mode
        self.observation_space = spaces.Box(-np.inf, np.inf, (6,), np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (2,), np.float32)
        self.dt = 0.1
        self.max_steps = 100

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.pos = self.np_random.uniform(-0.8, 0.8, size=2)
        self.vel = np.zeros(2)
        self.target = np.array([0.6, 0.6])
        self.t = 0
        return self._obs(), {}

    def _obs(self):
        return np.concatenate([self.pos, self.vel, self.target]).astype(np.float32)

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)
        self.vel = action
        self.pos = np.clip(self.pos + self.vel * self.dt, -1.0, 1.0)
        self.t += 1
        dist = float(np.linalg.norm(self.pos - self.target))

        # ----- three planted reward modes (one is correct) -----------------
        if self.reward_mode == "hack_velocity":
            # PLANTED HACK A: reward velocity TOWARD the target.
            to_target = (self.target - self.pos)
            unit = to_target / (np.linalg.norm(to_target) + 1e-8)
            reward = float(np.dot(self.vel, unit))            # farmable!
        elif self.reward_mode == "hack_proximity_only":
            # PLANTED HACK B: dense proximity, success bonus on mere closeness.
            reward = np.exp(-2.0 * dist) + (5.0 if dist < 0.05 else 0.0)
            # ...but success never gates on being SETTLED (low velocity).
        elif self.reward_mode == "hack_unbounded":
            # PLANTED HACK C: an unbounded inverse-distance term.
            reward = 1.0 / (dist + 1e-3)                      # explodes near target
        else:  # "good" — you will WRITE this one in your fix.
            reward = self._good_reward(dist)

        terminated = False                                    # no early terminal
        truncated = self.t >= self.max_steps
        info = {"dist": dist, "speed": float(np.linalg.norm(self.vel))}
        return self._obs(), reward, terminated, truncated, info

    def _good_reward(self, dist):
        # TODO (your fix): write a reward that makes the policy actually reach and
        # SETTLE at the target. Use potential-based shaping for the guidance term,
        # an action/effort penalty, and a success bonus GATED on being settled
        # (close AND slow). See Lecture 2 §3.1-3.4.
        raise NotImplementedError("write _good_reward in your fix")
```

```python
# Train one variant (sketch — use your Exercise 2 PPO or stable-baselines3):
# env = ReachEnv(reward_mode="hack_velocity")
# ... train ~50k steps ... then roll out and PRINT pos, speed, dist each step.
```

## Your task

For **each of the three planted hacks** (`hack_velocity`, `hack_proximity_only`, `hack_unbounded`):

1. **Train** a PPO policy on it (~50k steps is plenty for this toy env).
2. **Watch the rollout** — print or plot `pos`, `speed`, and `dist` over an episode. Do **not** diagnose from the reward curve; the curve is rising in all three cases.
3. **Name the exploit** against the Lecture 2 §3.3 catalogue:
   - Which failure is it (the vibrator / the knocker / the exploiter, or a clear variant)?
   - *What* is the policy doing to farm reward without solving the task? State it as observed behavior.
4. **Diagnose the reward bug** — which term is farmable, and why the optimizer found it.
5. **Fix it** by writing `_good_reward` (the same fix should defeat all three hacks — that's the point of a well-designed reward). Your fix must:
   - Use a **potential-based** guidance term (Lecture 2 §3.2) so you provably don't distort the goal.
   - Include an **action/effort penalty**.
   - **Gate the success bonus** on being *settled* (close AND slow), not merely close.
6. **Re-train on the good reward** and confirm the rollout now reaches and *holds* the target (dist small AND speed near zero at the end).

## Acceptance criteria

- [ ] A file `challenge-01-bestiary.md` with a section per hack containing parts 3–4 (name + diagnosis), each backed by quoted rollout data (the `dist`/`speed` trace that proves the exploit).
- [ ] You correctly identify each:
  - `hack_velocity` — **the vibrator**: rewarding velocity-toward-target lets the policy oscillate across the target line, farming "toward" reward without settling. The telltale is a high terminal `speed` and a `dist` that never converges.
  - `hack_proximity_only` — **the knocker / non-settled success**: the success bonus fires on mere proximity, so the policy slingshots through the target (touching the success radius at high speed) instead of stopping in it.
  - `hack_unbounded` — **the exploiter**: the unbounded `1/dist` term makes a single near-target step worth more than the whole rest of the episode, so the policy lunges and the value estimates blow up (watch `explained_variance` go negative).
- [ ] A working `_good_reward` that defeats all three, with the three required properties (potential-based guidance, effort penalty, settled-gated bonus).
- [ ] A re-trained rollout showing final `dist < 0.05` **and** final `speed < 0.05` — reached *and held*.
- [ ] Committed to your Week 28 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The seductive wrong fix for the vibrator is "just add a big velocity penalty everywhere." That makes the policy *sluggish and slow to reach* — you traded one bad behavior for another. The correct fix penalizes velocity **near the goal** (or, equivalently, rewards a *potential* on distance so the policy is rewarded for *being* close, not for *moving* close) and gates success on being settled. Reward velocity and you get a vibrator; reward position via a potential and you get a reacher. That distinction — *reward states, not state-changes* — is the senior insight this challenge plants.

## Stretch

- Add a **fourth** hack of your own design (e.g., reward "low distance variance" and watch the policy freeze far from the target to minimize variance), and have a peer diagnose it cold.
- Plot the reward curve *and* the success rate for `hack_proximity_only` on the same axes. The reward rises while true success (settled-at-target) stays low — the single most important graph in this challenge, because it's exactly what a reward hack looks like on a dashboard.
- Re-run the good reward with the success bonus as a **potential-based** term ($\gamma\Phi(s')-\Phi(s)$ with $\Phi$ = settled indicator) and confirm the NHR theorem holds: same optimal policy, faster learning.

## Why this matters

In Week 32 you defend a learned-policy stack to a panel, and in the capstone your robot's grasp policy is graded on real task success, not reward. Every team that ships RL has a reward-hacking war story; the engineers who don't have a *catastrophic* one are the ones who learned to watch the rollout instead of the curve. This challenge is that habit, built on a toy you can iterate in two minutes — so the lesson costs you ninety minutes here instead of a blown sprint later.
