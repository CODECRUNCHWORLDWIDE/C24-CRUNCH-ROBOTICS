# Mini-Project — Train a PPO Reach Policy to >90% in Parallel Sim, Then Deploy It in ROS2

> Train a PPO policy in **Isaac Lab** (or Gymnasium + a vectorized env on Path B) for a manipulator **reach** task, using **100+ parallel environments**, reaching **≥ 90% success in under 30 minutes of wall time**. Read the run in TensorBoard. Then wrap the trained policy in a `rclpy` inference node so it drives the robot in Gz Sim. Write a one-page training report.

This is the artifact that proves you can do robot RL *end to end*: shape a reward, launch a parallel-sim run, read the dashboard, hit a success bar, and — the part most RL tutorials skip — **get the policy off the GPU and into a ROS2 graph** where it actually controls a robot. That last bridge is what separates a notebook from a deployed policy, and it's exactly the pattern you'll re-use in Week 29 (Diffusion Policy), Week 30 (ACT), and the capstone.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** the trained reach policy and its ROS2 wrapper become a baseline you compare against in **Week 32 (the Phase 4 midterm)**, and the parallel-sim + reward-shaping muscle is exactly what **Week 34 (domain randomization)** builds on — you'll re-train *this* policy with randomization and measure the sim-to-real gap. Build it well now.

---

## What you will build

Three deliverables:

1. **A training run** — a PPO reach policy trained in Isaac Lab (Path A) or Gymnasium vector envs (Path B), with a shaped reward you wrote and defended, hitting ≥ 90% success.
2. **A ROS2 inference node** (`reach_policy_node.py`) — a `rclpy` node that loads the trained checkpoint, subscribes to the robot's joint/end-effector state, runs the policy, and publishes actions (joint velocity or end-effector delta commands) that drive the arm in Gz Sim toward a target.
3. **A one-page training report** (`TRAINING_REPORT.md`) — the reward function with justification, the hyperparameters, the TensorBoard curves (reward, success rate, KL, clip fraction, explained variance), the wall-time-to-90%, the throughput (steps/sec), and an honest "what I'd tune next."

By the end you have a public repo with a reproducible training command, a checkpoint, a working ROS2 node, and a report a reviewer can read in three minutes and trust.

---

## Path A vs Path B — pick one, document it

| | Path A (Isaac Lab) | Path B (Gymnasium) |
|---|---|---|
| Sim | Isaac Lab `Isaac-Reach-Franka-v0` (or your own `ManagerBasedRLEnv`) | A reach `gymnasium` env (e.g. `Reacher-v5` from MuJoCo, or your own from the challenge) |
| Parallelism | `--num_envs 4096` on one GPU | `gym.make_vec(..., num_envs=16)` (CPU/GPU) |
| Throughput | 100k+ steps/sec | a few thousand steps/sec |
| Wall-time-to-90% | minutes | tens of minutes (acceptable; document it) |
| Runner | `rsl_rl` or `skrl` PPO | your Exercise 2 PPO, or stable-baselines3 `PPO` |

**Path B is a first-class citizen.** The throughput axiom (Lecture 2) means Path B is slower, but the reward shaping, the diagnostics, and the ROS2 deployment are *identical*. If you take longer than 30 minutes on Path B because your sim is slow, that is fine — document the wall time and the steps/sec, and note that the gap is sim throughput, not your algorithm. The bar that does **not** move is **≥ 90% success** and **a working ROS2 node**.

---

## Deliverable 1 — the training run

### The reward (this is where the project is won or lost)

Write a shaped reach reward with three terms, exactly as Lecture 2 §3.1 lays out — and defend each in the report:

```python
# A reach reward, batched over num_envs (Isaac Lab style). On Path B, the same
# three terms apply per-env. ee_pos and target are (num_envs, 3); action is the
# command vector.
def reach_reward(ee_pos, target, action, prev_dist):
    dist = torch.norm(ee_pos - target, dim=-1)
    reward = (
        torch.exp(-2.0 * dist)                      # dense guidance (bounded, peaks at goal)
        - 0.01 * torch.sum(action ** 2, dim=-1)     # effort penalty (smooth, cheap motion)
        + 5.0 * (dist < 0.02)                       # success bonus (gated on actually reaching)
    )
    return reward, dist
```

Run the reward-shaping checklist (Lecture 2 §3.4) before you launch a long run: is there a path of increasing reward from a random start? Is success strictly best-rewarded? Can any term be farmed? You watched three hacks in the challenge — don't ship a fourth here.

### Launch it

Path A:

```bash
# Isaac Lab (flags vary by version; check the docs you pinned in resources.md).
python scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --num_envs 4096 --headless --max_iterations 300
tensorboard --logdir logs/
```

Path B:

```bash
# Your Exercise 2 PPO, scaled to vectorized envs, or stable-baselines3:
python train_reach_ppo.py --num_envs 16 --total_steps 2_000_000 --logdir runs/
tensorboard --logdir runs/
```

### Read the dashboard

You must hit the **"reward curve climbed" promise** from the week README: `success_rate ≥ 0.90`, `approx_kl` in [0.005, 0.02], `clip_fraction` in [0.1, 0.3], `explained_variance` climbing toward 1.0. If success climbs but KL spikes, you're about to collapse — lower the LR or the epochs. Capture screenshots of all five traces for the report.

---

## Deliverable 2 — the ROS2 inference node

This is the bridge. The trained policy is a `torch` module; the robot speaks ROS2. The node:

1. Loads the checkpoint at startup (`torch.load`, `model.eval()`).
2. Subscribes to the robot state — `/joint_states` (`sensor_msgs/JointState`) and the current target (a `geometry_msgs/PoseStamped` on `/reach_target`), assembling the same observation vector the policy was trained on.
3. Runs the policy **deterministically** at inference — use the mean action (`dist.mean` or the actor's `mu`), not a sample. (You explore stochastically during training; you act deterministically at deployment.)
4. Publishes the action — joint-velocity commands (`std_msgs/Float64MultiArray` to the controller) or an end-effector delta — at a fixed rate (e.g. 30 Hz), with the QoS discipline from Week 5 (commands are `RELIABLE` / `KEEP_LAST(1)`).

```python
#!/usr/bin/env python3
"""reach_policy_node.py — wrap a trained PPO reach policy in a rclpy node.
Sketch; fill in the obs assembly to match how you trained."""
import torch
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64MultiArray


class ReachPolicyNode(Node):
    def __init__(self):
        super().__init__("reach_policy_node")
        self.policy = torch.jit.load("reach_policy.pt")    # or load_state_dict
        self.policy.eval()
        self.joint_pos = None
        self.target = None

        # Sensor-class subscription QoS (Week 5): best_effort sensor stream.
        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=5)
        # Command-class publish QoS (Week 5): reliable, only-the-latest.
        cmd_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                             history=HistoryPolicy.KEEP_LAST, depth=1)

        self.create_subscription(JointState, "/joint_states", self._on_joints, sensor_qos)
        self.create_subscription(PoseStamped, "/reach_target", self._on_target, cmd_qos)
        self.pub = self.create_publisher(Float64MultiArray, "/arm_velocity_cmd", cmd_qos)
        self.create_timer(1.0 / 30.0, self._control_tick)   # 30 Hz inference

    def _on_joints(self, msg):
        self.joint_pos = list(msg.position)

    def _on_target(self, msg):
        p = msg.pose.position
        self.target = [p.x, p.y, p.z]

    def _control_tick(self):
        if self.joint_pos is None or self.target is None:
            return
        # TODO 1: assemble the observation EXACTLY as in training (same order,
        #         same normalization). A mismatched obs is the #1 deploy bug.
        obs = self._build_obs(self.joint_pos, self.target)
        with torch.no_grad():
            action = self.policy(torch.as_tensor(obs).float().unsqueeze(0))
            # Deterministic at deployment: use the mean, not a sample.
            action = action.squeeze(0).cpu().numpy()
        self.pub.publish(Float64MultiArray(data=action.tolist()))

    def _build_obs(self, joint_pos, target):
        # TODO 2: match the training observation. Document the layout in the report.
        raise NotImplementedError


def main():
    rclpy.init()
    rclpy.spin(ReachPolicyNode())
    rclpy.shutdown()


if __name__ == "__main__":
    main()
```

The **single biggest deployment bug** is an observation mismatch: the node assembles the obs vector in a different order or scale than training. Export the obs spec alongside the checkpoint and assert on it. (`torch.jit.save` the policy as a self-contained `.pt` so the node has no dependency on your training code.)

---

## Deliverable 3 — the training report

`TRAINING_REPORT.md`, one page, with:

1. **Task + reward** — the reward function and a sentence per term defending it; the checklist from §3.4 applied.
2. **Hyperparameters** — a table (LR, clip ε, γ, λ, num_envs, rollout length, epochs, entropy coef).
3. **The curves** — five TensorBoard screenshots (reward, success rate, KL, clip fraction, explained variance), each with a one-line reading.
4. **Throughput + wall time** — steps/sec and minutes-to-90%. State your path.
5. **Deployment** — confirmation the ROS2 node drives the arm in Gz Sim toward a target, with the obs layout documented.
6. **What I'd tune next** — one honest paragraph. (A reviewer trusts a report that admits its limits.)

---

## Rules

- **You may** use Isaac Lab, `rsl_rl`/`skrl`, stable-baselines3, or your own Exercise 2 PPO. Use a real, maintained framework — don't reinvent PPO for the mini-project (you already did, in Exercise 2).
- **You must** write your own reward and defend it. A reward lifted unchanged from an example doesn't demonstrate the §3 skill.
- **You must** deploy the policy in a ROS2 node with the correct command/sensor QoS from Week 5. A policy that only runs in the trainer is half a deliverable.
- **You must not** claim >90% success without the TensorBoard `success_rate` trace to back it. "It looked good" is not a success metric.
- Python 3.12, PyTorch ≥ 2.3, ROS2 Jazzy.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-28-rl-reach-<yourhandle>`.
- [ ] A reproducible training command in the README that another learner can run.
- [ ] TensorBoard logs (or exported curves) showing `success_rate ≥ 0.90`.
- [ ] The reward function is your own, documented, and passes the §3.4 checklist (no farmable term).
- [ ] `reach_policy_node.py` loads the checkpoint and drives the arm in Gz Sim toward a `/reach_target` — demonstrated in a short clip or a logged success.
- [ ] Command QoS is `RELIABLE`/`KEEP_LAST(1)`; sensor QoS is `BEST_EFFORT`/`KEEP_LAST(5)` (Week 5 discipline carried forward).
- [ ] `TRAINING_REPORT.md` with all six sections.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Reward design** | 25 | Three principled terms; the §3.4 checklist applied; potential-based where it matters; no farmable hack; each term defended in the report. |
| **Training result** | 25 | `success_rate ≥ 0.90` backed by the TensorBoard trace; healthy KL/clip/explained-variance; wall time and throughput reported. |
| **ROS2 deployment** | 25 | The node loads the checkpoint, assembles the *correct* obs, acts deterministically, publishes at a fixed rate with correct QoS, and visibly drives the arm. |
| **Dashboard literacy** | 15 | Five traces captured and *read* — each screenshot has a correct one-line interpretation, not just "it went up." |
| **Report & hygiene** | 10 | One-page report, reproducible command, checkpoint committed sensibly (Git-LFS or release asset, not a 500 MB blob in history), honest "what I'd tune next." |

**90+** is portfolio-grade and ready to be the baseline in Week 32. **70–89** trains and deploys but the reward or the dashboard reading is thin. **Below 70** usually means either success was claimed without the trace, or the policy never made it into ROS2 — fix whichever first.

---

## Stretch goals

- **Train SAC on the same task** and compare sample efficiency (steps-to-90%) against PPO. Confirm Lecture 2's claim: in massively-parallel sim, PPO's wall-time-to-90% usually wins despite SAC's per-sample efficiency.
- **Add observation/reward normalization** and measure the convergence speedup. Free lunch.
- **Curriculum.** Start the target close to the gripper and move it farther as success rises. Watch the policy learn the easy task first and bootstrap to the hard one — the "curriculum is real" axiom from the syllabus.
- **Deterministic vs stochastic deploy.** Run the ROS2 node once sampling actions and once using the mean. Quantify the success-rate and jerk difference. (This previews the deployment-smoothness question that Diffusion Policy and ACT answer differently in Weeks 29–30.)

---

## How this connects to the rest of C24

- **Week 29 (Diffusion Policy)** and **Week 30 (ACT)** reuse this repo's eval harness and the ROS2-node deployment pattern; you'll compare a learned *imitation* policy against this RL baseline.
- **Week 32 (Phase 4 midterm)** asks you to defend a learned-policy stack with a safety wrapper and a fallback — this trained policy is the thing you wrap.
- **Week 34 (domain randomization)** re-trains *this exact policy* with visual + dynamics randomization and measures the sim-to-real gap closure.

When you've finished, push the repo and take the [quiz](../quiz.md).
