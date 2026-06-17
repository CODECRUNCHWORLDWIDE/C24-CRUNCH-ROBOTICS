# Lecture 2 — Diffusion Policy: Action Chunking, Receding Horizon, and Deployment

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can build a Diffusion Policy — the conditioned 1D temporal U-Net (or transformer), the observation encoder, action-chunk prediction, and receding-horizon execution — and deploy it inside a real-time ROS2 control loop with a sane latency budget.

Lecture 1 gave you the generative engine: a denoising model that turns noise into samples from an arbitrary distribution, trained with plain MSE, sampled fast with DDIM. This lecture turns that engine into a *robot policy*. Three ideas do the work, and all three are about *time*: condition on a short observation history, predict a *chunk* of future actions, and execute that chunk *receding-horizon*.

The sentence to carry in:

> **Diffusion Policy denoises a short sequence of future actions, conditioned on recent observations — and executes only the first slice of that sequence before re-planning. Predicting a chunk gives temporal consistency; executing a slice keeps it reactive.**

---

## Part 1 — From denoiser to policy: conditioning on observations

In Lecture 1 the denoiser was *unconditional* — it generated samples from $p(x_0)$. A policy must generate actions *given* the current situation: $p(A \mid O)$, where $A$ is an action chunk and $O$ is a short history of observations. The fix is **conditioning**: the noise-prediction network sees the observation embedding at every denoising step.

$$
\epsilon_\theta(A_t,\ t,\ O) \approx \text{the noise added to the action chunk } A,
$$

where $A_t$ is the noised action chunk at diffusion step $t$ and $O$ is the (clean, never-noised) observation embedding. **Only the actions are diffused; the observations are not** — they're the condition, fixed throughout the denoising loop. This "condition on obs, diffuse actions" choice (vs jointly diffusing obs+actions) is one of Chi et al.'s core design decisions, and it's why a single observation can be encoded once and reused across all denoising steps — important for latency.

### How the observation enters the network

- **Low-dimensional state** (joint positions, end-effector pose): a small MLP encodes the obs history into a conditioning vector.
- **Images**: a vision backbone (a ResNet, often with the global-pooling layer replaced by spatial-softmax to keep spatial info) encodes each frame; the per-frame features are concatenated over the obs history.

That conditioning vector is injected into the denoiser, and *how* it's injected depends on the backbone.

---

## Part 2 — The two backbones

### 2.1 The 1D temporal U-Net with FiLM conditioning (the default)

The action chunk is a sequence of shape `(T_p, action_dim)` — treat the **time axis as the convolution axis**. A 1D U-Net (Conv1d down-blocks, a bottleneck, Conv1d up-blocks with skip connections) denoises along the chunk's time dimension. The observation and timestep conditioning enters through **FiLM** — Feature-wise Linear Modulation — which produces a per-channel scale $\gamma$ and shift $\beta$ from the conditioning vector and applies them to the conv features:

$$
\text{FiLM}(h\mid c) = \gamma(c)\odot h + \beta(c).
$$

```python
class FiLM1d(nn.Module):
    """Condition Conv1d features on (obs_embedding + time_embedding)."""
    def __init__(self, cond_dim: int, channels: int):
        super().__init__()
        self.to_scale_shift = nn.Linear(cond_dim, channels * 2)

    def forward(self, h: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        # h: (B, channels, T_p); cond: (B, cond_dim)
        scale, shift = self.to_scale_shift(cond).chunk(2, dim=-1)
        return h * (1 + scale.unsqueeze(-1)) + shift.unsqueeze(-1)
```

FiLM is cheap, stable, and expressive enough — it's the backbone Chi et al. recommend as the default, and it's what LeRobot's Diffusion Policy uses. The Conv1d-over-time structure has a nice inductive bias: it models the *temporal smoothness* of an action chunk natively, which is exactly what you want from a sequence of motor commands.

### 2.2 The transformer variant

Alternatively, treat the chunk as a sequence of action tokens and the observation as conditioning tokens, and denoise with a transformer (cross-attention from action tokens to obs tokens, or concatenated tokens with causal/full attention). The transformer often **wins on longer horizons and higher-dimensional observations** (it attends globally rather than through a fixed receptive field), at some cost in training stability and tuning sensitivity. The honest 2026 guidance: **start with the U-Net+FiLM** (it's more forgiving and trains faster); reach for the transformer when your horizon is long or your observation is rich and the U-Net plateaus. You'll have the U-Net in the exercise; the transformer is a stretch goal.

### 2.3 The observation encoder, in detail

The conditioning vector has to come from *somewhere*, and for a visuomotor policy that somewhere is a vision encoder. The details matter more than they look:

- **The backbone.** A ResNet-18 (or -34) is the standard image encoder — small enough for real-time inference, expressive enough for manipulation. You typically *train it end-to-end* with the policy rather than freezing a pretrained one, because manipulation features (where is the object edge, is the gripper aligned) differ from ImageNet classification features.
- **Spatial-softmax pooling.** A crucial Diffusion Policy detail: replace the ResNet's global-average-pooling head with a **spatial-softmax** that extracts the (x, y) *coordinates* of feature activations. Global pooling throws away *where* a feature is — disastrous for a policy that needs to know *where* the object is in the image. Spatial-softmax keeps the spatial information as a compact set of keypoints, and it measurably improves manipulation success.
- **Multiple cameras.** Each camera gets its own encoder pass; the per-camera features are concatenated into the conditioning vector. A wrist camera plus a third-person camera is a common, effective combination.
- **The observation horizon.** Conditioning on the last $T_o$ frames (e.g. 2) rather than just the current one lets the policy infer velocity and short-term dynamics — important when a single frame is ambiguous about which way something is moving.

For the low-dimensional-state case (joint angles, end-effector pose, no images), the encoder is just a small MLP — much cheaper, and what the exercises use to keep things runnable on a laptop. But know the image path, because the capstone's real perception runs through exactly this spatial-softmax-ResNet pipeline.

### 2.4 Classifier-free-guidance-style conditioning strength

Borrowed from image diffusion: you can train the policy to *sometimes* see the observation and sometimes see a null/dropped observation, then at inference *amplify* the difference — pushing the sampled action further in the direction the observation implies. This **conditioning-strength** knob (analogous to classifier-free guidance, CFG) can sharpen the policy's commitment to the observed situation. In practice it's a secondary knob — most Diffusion Policies work well without it — but it's in the toolbox, and you'll see it referenced in the paper and in library configs. The intuition to keep: it trades a little diversity for a little more obedience to the observation.

---

## Part 3 — Action chunking and receding horizon (the timing trinity)

This is the part that makes Diffusion Policy a *good* controller, separate from it being a good generative model. Three horizons:

- **Observation horizon** $T_o$: how many past observations condition the prediction (e.g. 2). A short window of history disambiguates velocity/direction.
- **Prediction horizon** $T_p$: how many future actions the policy predicts in one chunk (e.g. 16). The chunk is what gets denoised.
- **Execution horizon** $T_a$: how many of those predicted actions you actually *execute* before re-observing and re-predicting (e.g. 8), with $T_a < T_p$.

### 3.1 Why predict a chunk instead of one action?

Predicting one action at a time (like BC) makes the policy **myopic and jittery**: small errors compound, and there's no temporal coherence — successive actions can fight each other. Predicting a **chunk** of $T_p$ actions in one shot gives the policy a *plan*: the actions within a chunk are jointly consistent (they came from one denoising process over the whole sequence), so the motion is smooth and committed. Chunking is also how the policy expresses a *decision* that unfolds over time — "I'm going to go around the left" is a property of a sequence, not a single action.

### 3.2 Why execute only part of the chunk (receding horizon)?

If you predict 16 actions and *execute all 16* before re-observing, you're flying blind for 16 steps — any disturbance (the object slipped, a human nudged it) is ignored until the chunk runs out. That's stale and unsafe. So you **execute only the first $T_a$** actions, then re-observe and re-predict a fresh chunk. This is exactly **Model Predictive Control's receding horizon** (Week 22), applied to a learned policy: plan long, commit short, re-plan often.

The trade-off you tune:

- **Short $T_a$** (e.g. 1–2): very reactive (re-plans almost every step) but you cross chunk boundaries often, and consecutive chunks can disagree slightly → jerk at the seams.
- **Long $T_a$** (e.g. close to $T_p$): smooth (few re-plans) but stale and less reactive to disturbances.
- A common sweet spot is $T_a \approx T_p / 2$. You'll sweep this in the mini-project against a jerk-vs-success plot.

```python
class RecedingHorizonController:
    """Maintain an action queue; refill it by re-predicting a chunk when it drains
    to the execution horizon. Decouples the (slow) inference rate from the (fast)
    control rate — the controller always has an action to emit."""
    def __init__(self, policy, T_p=16, T_a=8):
        self.policy, self.T_p, self.T_a = policy, T_p, T_a
        self.queue = []

    def step(self, obs):
        if len(self.queue) == 0:
            chunk = self.policy.predict_action_chunk(obs)   # DDIM denoise -> (T_p, act_dim)
            self.queue = list(chunk[: self.T_a])            # keep only the first T_a
        return self.queue.pop(0)
```

### 3.3 The action-queue / latency-decoupling pattern

Denoising takes time — even 16 DDIM steps is, say, 20–40 ms on a small GPU. If your control loop runs at 30 Hz (33 ms budget), you cannot afford to denoise *every* tick. The receding-horizon **action queue** solves this elegantly: predict a chunk (one slow denoise), then *pop one action per control tick* from the queue (fast), re-predicting only when the queue drains to $T_a$. The slow inference rate (re-plan every $T_a$ ticks) is decoupled from the fast control rate (emit every tick). This is the pattern that makes a 40-ms-inference policy run a 30 Hz controller — and it's exactly the deployment structure you build in the mini-project.

### 3.4 How to actually set the three horizons

Concrete starting points, and how to adjust them:

- **Observation horizon $T_o$** — start at **2**. One frame can't tell you velocity; two can. Go higher only if your task needs longer temporal context (e.g. a multi-step sequence where what to do *now* depends on what happened several frames ago). More history costs encoder compute and rarely helps past 2–3 for reactive manipulation.
- **Prediction horizon $T_p$** — start at **16**. Long enough to capture a coherent sub-behavior and give the receding-horizon loop room; short enough that the chunk's tail is still predictable from the current observation. If the motion looks short-sighted, lengthen it; if the chunk's later actions are garbage (the world changed too much), shorten it.
- **Execution horizon $T_a$** — start at **$T_p / 2$** (8). This re-plans often enough to stay reactive without re-planning *every* tick (which would be jerky at seams and might blow the latency budget). Shorten $T_a$ for a more dynamic task (more frequent re-planning); lengthen it if your inference is slow and you need fewer re-plans per second.

The interactions to keep in mind: a longer $T_p$ with a fixed $T_a$ means you re-plan less often *relative to* how far ahead you predict (more committed, smoother, less reactive). A shorter $T_a$ means more re-plans per second — more reactive, but each re-plan is a denoise, so it stresses the latency budget harder. The mini-project's two sweeps (DDIM steps and $T_a$) exist precisely to let you *find* these values for your task and your hardware rather than trusting the defaults — the defaults are a starting point, not an answer.

A subtle deployment detail the queue code glosses over: when you re-plan, you predict from the *current* observation, but the actions you just executed were predicted from an *older* one. If the two chunks disagree at the handoff (the seam), you get a small discontinuity. Shortening $T_a$ makes seams more frequent (more disagreements, more total jerk); lengthening it makes each seam staler. There's no free lunch — which is exactly why ACT's temporal ensembling (Week 30) exists as an *alternative* smoothing strategy that blends across the seam instead of switching at it.

---

## Part 4 — Putting the model together

The full Diffusion Policy forward pass, end to end:

```python
class DiffusionPolicy(nn.Module):
    def __init__(self, obs_dim, action_dim, T_p, n_diffusion_steps=100):
        super().__init__()
        self.T_p, self.action_dim = T_p, action_dim
        self.obs_encoder = nn.Sequential(            # low-dim obs encoder (MLP)
            nn.Linear(obs_dim, 256), nn.ReLU(), nn.Linear(256, 256))
        self.time_embed = SinusoidalTimeEmbedding(128)
        self.unet = ConditionalUNet1d(               # the FiLM-conditioned 1D U-Net
            action_dim=action_dim, cond_dim=256 + 128)
        betas = torch.linspace(1e-4, 0.02, n_diffusion_steps)
        self.register_buffer("alpha_bar", torch.cumprod(1 - betas, dim=0))

    def compute_loss(self, obs, action_chunk):
        """Training: noise the GT chunk at a random t, predict the noise, MSE."""
        B = obs.shape[0]
        cond = self.obs_encoder(obs)
        t = torch.randint(0, len(self.alpha_bar), (B,), device=obs.device)
        eps = torch.randn_like(action_chunk)
        ab = self.alpha_bar[t].view(B, 1, 1)
        noised = torch.sqrt(ab) * action_chunk + torch.sqrt(1 - ab) * eps
        cond_t = torch.cat([cond, self.time_embed(t)], dim=-1)
        eps_pred = self.unet(noised, cond_t)
        return F.mse_loss(eps_pred, eps)

    @torch.no_grad()
    def predict_action_chunk(self, obs, n_ddim_steps=16):
        """Inference: DDIM-denoise a chunk conditioned on the observation."""
        cond = self.obs_encoder(obs)
        # ... DDIM loop over n_ddim_steps, conditioning the U-Net on `cond` at each
        #     step (cond is computed ONCE; only the action chunk is re-denoised) ...
        return action_chunk   # (B, T_p, action_dim)
```

Two details that matter:

- **Normalize the actions** to roughly $[-1, 1]$ before training (the diffusion process assumes data on a standard scale, since it terminates in $\mathcal{N}(0,I)$). Un-normalize after sampling. A common bug is forgetting the un-normalize at deploy, so the robot gets tiny actions and barely moves.
- **Encode the observation once per chunk**, not once per denoising step. The obs doesn't change during the 16-step denoise; re-encoding it 16× is wasted compute you can't afford in the control loop.

---

## Part 5 — Deployment in ROS2

The ROS2 node mirrors the Week-28 pattern, with the receding-horizon controller in the middle:

```python
class DiffusionPolicyNode(Node):
    def __init__(self):
        super().__init__("diffusion_policy_node")
        self.policy = torch.jit.load("diffusion_policy.pt"); self.policy.eval()
        self.controller = RecedingHorizonController(self.policy, T_p=16, T_a=8)
        self.obs_history = deque(maxlen=2)           # observation horizon T_o = 2

        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=5)
        cmd_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                             history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(JointState, "/joint_states", self._on_state, sensor_qos)
        self.pub = self.create_publisher(Float64MultiArray, "/arm_cmd", cmd_qos)
        self.create_timer(1.0 / 30.0, self._control_tick)    # 30 Hz control

    def _control_tick(self):
        if len(self.obs_history) < self.obs_history.maxlen:
            return
        obs = self._assemble_obs(self.obs_history)   # same layout as training!
        action = self.controller.step(obs)           # pops from queue; re-plans when drained
        self.pub.publish(Float64MultiArray(data=self._unnormalize(action).tolist()))
```

The latency budget reasoning you must be able to do:

- Control rate 30 Hz → 33 ms per tick. The *pop* from the queue is microseconds, so most ticks are free.
- A re-plan happens every $T_a = 8$ ticks → every ~267 ms. The DDIM denoise (16 steps) must finish inside that window with margin. If it doesn't, you reduce DDIM steps (the latency knob) or shorten $T_p$ — and you measure, you don't guess.
- The QoS is the same Week-5 discipline: state in `BEST_EFFORT`, commands `RELIABLE`/`KEEP_LAST(1)`.

### A worked budget

Concretely, suppose you measure the DDIM denoise at 32 ms on your GPU and the control loop runs at 30 Hz ($T_a = 8$):

- A re-plan is needed every 8 ticks = every 266 ms.
- The 32 ms denoise fits comfortably in that 266 ms window — *if you run it on a background thread so it doesn't block the control tick.* The naive mistake is running the denoise *inside* the control callback, which would stall that one tick for 32 ms and miss the 33 ms deadline.
- The fix is the action-queue's whole point: the denoise runs *off* the control thread (or at least is allowed the full $T_a$-tick window to complete), and the control thread only ever pops. As long as the denoise completes before the queue drains, the control loop never starves.
- **What if the denoise were 300 ms (too slow)?** Then it wouldn't finish before the 266 ms re-plan window, the queue would drain, and the controller would stall. Your options, in order: cut DDIM steps (16 → 8 → 4, measuring success at each), lengthen $T_a$ (re-plan less often, accepting more staleness), or shorten $T_p$ (cheaper denoise). You pick by measuring success against latency — which is exactly the mini-project's DDIM-step sweep.

This arithmetic — re-plan period vs denoise time, run off the control thread — is the deployment reasoning that separates a policy that runs at 30 Hz from one that hitches every quarter-second.

---

## Part 6 — Evaluation: the head-to-head and the multimodality visualization

The week's intellectual payoff is *seeing* why Diffusion Policy wins. Two evaluations:

1. **The head-to-head on a fixed protocol.** Same eval seeds, same success criterion, same demo set. Report success rate for BC, BC+DAgger (both from Week 27), and Diffusion Policy. On a genuinely multimodal task, Diffusion Policy should clearly win — that's the whole thesis. *Fix the eval protocol before you train so you can't unconsciously tune to it.*
2. **The multimodality scatter.** Pick a state you *know* is multimodal (a junction where left and right are both demonstrated). Sample the policy 512 times from different noise seeds and scatter the first predicted action. Diffusion Policy shows **two clusters**; BC shows **one blob** centered in the invalid middle. This is the "the distribution had two modes" promise from the README, and it's the single most convincing artifact you'll produce this week.

```python
# Visualize multimodality at a known junction state.
acts = torch.stack([policy.predict_action_chunk(obs)[0, 0] for _ in range(512)])
plt.scatter(acts[:, 0], acts[:, 1], s=4, alpha=0.3)   # diffusion: TWO clusters
# Overlay the BC prediction (deterministic): ONE point, in the valley between them.
```

### 6.1 What a *good* eval reveals beyond the headline number

The head-to-head success rate is the headline, but a thorough eval surfaces more:

- **Per-condition breakdown.** Does Diffusion Policy win uniformly, or only on the *multimodal* initial conditions? If the gap is concentrated at the ambiguous states, that's the cleanest evidence the win is *about* multimodality and not something incidental.
- **Failure-mode taxonomy.** When Diffusion Policy fails, *how*? (Missed grasp, knocked the object, timed out.) When BC fails, is it the predictable "drove into the obstacle at the junction"? Categorizing failures is more informative than a single rate.
- **Action-distribution entropy over the rollout.** Diffusion Policy's predicted distribution should be *wide* (multimodal) at ambiguous states and *narrow* (confident) at unambiguous ones. If it's wide everywhere, the policy is uncertain (under-trained); if narrow everywhere, it may have lost the multimodality (over-conditioned). Plotting this over a rollout tells you *where* the policy is deciding versus executing.

These are the analyses that turn "Diffusion Policy scored higher" into "Diffusion Policy scored higher *because* it kept both modes at the junction, and here's the per-condition data proving it" — the difference between a result and an *explained* result, which is what a Week-32 panel rewards.

---

## Part 7 — The "it barely moves / it's jerky" failure decision tree

When a Diffusion Policy deploys badly, the symptom is rarely a crash — it's subtle misbehavior. Walk this tree; it covers the failures in priority order:

```
Diffusion Policy deployed and behaving wrong.
│
├─ Does the arm BARELY MOVE (tiny actions)?
│   ├─ Yes → almost always a NORMALIZATION bug. You trained on actions normalized to
│   │        ~[-1, 1] but forgot to UN-normalize the sampled action before publishing,
│   │        so the robot gets [-1,1]-scale commands when it expects rad/s. (Part 5.)
│   └─ No ↓
│
├─ Does it move plausibly but do the WRONG THING entirely?
│   ├─ Yes → OBSERVATION MISMATCH. The node assembles the obs in a different order or
│   │        scale than training. Assert the obs against a saved spec. (Part 5.)
│   └─ No ↓
│
├─ Is the motion JERKY at regular intervals?
│   ├─ Yes → chunk-boundary jerk. Your execution horizon T_a is too long (stale) or the
│   │        consecutive chunks disagree. Shorten T_a, or check the receding-horizon
│   │        re-plan cadence. (Part 3.2.)
│   └─ No ↓
│
├─ Is inference too SLOW for the control loop?
│   ├─ Yes → reduce the DDIM step count (the latency knob), or lengthen T_a so you
│   │        re-plan less often, or shorten T_p. Measure, don't guess. (Part 5.)
│   └─ No ↓
│
└─ Is the action distribution UNIMODAL where it should be multimodal?
    └─ Either the conditioning leaked the answer (the obs over-determines the action),
       the chunk is too short to express the choice, or you trained on unimodal data.
       Check the DATA's multimodality first (Part 6), the architecture second.
```

Tape this next to the Week-5 QoS decision tree. Between deployment latency, normalization, obs layout, and chunk horizons, almost every "my Diffusion Policy misbehaves on the robot" problem is one of these five, in this priority order — and the normalization/obs bugs (the silent ones) are first because they're the most common and the most maddening to find without a checklist.

### Why this is the same shape as MPC

It's worth naming the through-line to Week 22 explicitly, because it's not a coincidence. Receding-horizon execution — predict a horizon, execute a slice, re-observe, re-plan — is *exactly* Model Predictive Control's core loop. Diffusion Policy is, in this sense, a *learned* MPC: instead of solving a QP to get the next horizon of actions, it *denoises* a chunk of them; instead of a hand-written cost, it has a distribution learned from demonstrations. The receding-horizon discipline you built for the kinematic-bicycle MPC in Week 22 transfers wholesale — the "plan long, commit short, re-plan often" instinct is the same, and the same trade (longer commit = smoother but staler) applies. Recognizing that a learned policy and a classical controller share a control *structure* is the kind of cross-connection that makes a senior engineer; it's why the capstone can wrap a learned policy in the same safety scaffolding as a classical one (Week 32), because at the execution level they're the same loop.

---

## 8. Recap

You should now be able to:

- Condition the denoiser on an observation embedding (diffuse actions, not observations) and explain why that choice helps latency.
- Build the 1D temporal U-Net with FiLM conditioning, and say when to reach for the transformer instead.
- Use the observation/prediction/execution horizons, explain why chunking gives consistency and receding-horizon execution keeps reactivity, and tune $T_a$ against jerk-vs-success.
- Apply the action-queue pattern to decouple slow inference from a fast control loop, and reason about the DDIM-step latency budget.
- Deploy a Diffusion Policy in ROS2 with correct QoS and action (un)normalization.
- Run the head-to-head eval and produce the multimodality scatter that proves the thesis.

Next: the exercises put DDPM, DDIM, and a full Diffusion Policy in your hands, the challenge stages the BC-vs-diffusion multimodal showdown, and the mini-project trains the real thing on your Week-27 demos and deploys it. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *Diffusion Policy: Visuomotor Policy Learning via Action Diffusion* — Chi et al. (2023): <https://arxiv.org/abs/2303.04137>
- *Denoising Diffusion Implicit Models* (the deployable sampler) — Song et al. (2021): <https://arxiv.org/abs/2010.02502>
- *FiLM: Visual Reasoning with a General Conditioning Layer* — Perez et al. (2018): <https://arxiv.org/abs/1709.07871>
- *LeRobot diffusion policy* (the maintained reference): <https://github.com/huggingface/lerobot>
- *`diffusion_policy` reference implementation* — Chi et al.: <https://github.com/real-stanford/diffusion_policy>
- *Model Predictive Control receding horizon* (the control analogy, C24 Week 22): <https://docs.ros.org/en/jazzy/>

---

## Appendix — A deployment-readiness checklist

Before you call a Diffusion Policy deployment done, confirm:

- [ ] Actions normalized for training, un-normalized at inference; stats saved with the checkpoint.
- [ ] Observation layout asserted against a saved spec at node startup.
- [ ] DDIM step count chosen from a measured success-vs-latency sweep, not guessed.
- [ ] The denoise runs off the control thread (or within the $T_a$-tick re-plan window), so control ticks never stall.
- [ ] Receding-horizon $T_a$ tuned against jerk-vs-success; the action queue refills before it drains.
- [ ] QoS: commands `RELIABLE`/`KEEP_LAST(1)`, sensor state `BEST_EFFORT`/`KEEP_LAST(5)`.
- [ ] The eval protocol was fixed before training; the head-to-head and the multimodality scatter both produced.

This is the union of everything Part 5–7 covered, in one place — the list a senior engineer runs down before signing off a learned policy for the robot.
