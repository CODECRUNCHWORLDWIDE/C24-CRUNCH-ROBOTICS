# Lecture 1 — Cross-Embodiment, Octo, and OpenVLA: How Generalist Policies Actually Work

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain what Open X-Embodiment is and why pooling many robots' data works, describe the Octo and OpenVLA architectures precisely enough to draw them, and tokenize a 7-DOF action by hand the way OpenVLA does.

If you remember one sentence from this entire week, remember this one:

> **A generalist robot policy is a strong visual-language prior trained on many robots' data; it gets you a meaningful head start on your task, but the gripper, the camera, and the objects are still yours — so fine-tuning is mandatory, and the number that matters is the post-fine-tuning success rate on a held-out eval set.**

In Weeks 27–30 you trained *specialists*: BC, DAgger, Diffusion Policy, ACT — each from your own 50–200 demos, each knowing nothing outside its task. This week flips the script. We download a model pretrained on a million trajectories across twenty-two robots, condition it on a *sentence*, and adapt it to our task with a fraction of the data. This lecture is the conceptual and architectural foundation. Lecture 2 is the hands-on fine-tuning and the evaluation discipline.

Three parts: (1) the cross-embodiment dataset story, (2) the Octo architecture, (3) the OpenVLA architecture and action tokenization.

---

## Part 1 — The cross-embodiment story: why pooling robots works

### 1.1 The data problem that motivated everything

Imitation learning works, but it is data-hungry per task and the data does not transfer. Your Week 29 Diffusion Policy learned "pick the red cube" from 200 demos and is useless for "open the drawer" — you start over. A robotics lab with ten tasks collects ten datasets and trains ten policies. That does not scale, and it is nothing like how a language model learns: GPT-style models pretrain once on a giant heterogeneous corpus and then do many tasks.

The hypothesis behind generalist robot policies: **if we pool robot data across many tasks, scenes, and even different robots, a single model can learn shared structure** — what a gripper approaching an object looks like, how "left" maps to a motion, how a cluttered tabletop decomposes — and then specialize cheaply. The question was whether data from a *different robot* (different arm, different camera, different action space) helps or hurts. The answer, empirically, was that it **helps**: this is **positive cross-embodiment transfer**, and it is the load-bearing result of the whole field.

### 1.2 Open X-Embodiment (OXE)

**Open X-Embodiment** is the dataset that made this concrete. It is a community effort that pooled robot-learning datasets from many labs into one standardized collection: in its assembled form, on the order of **1M+ trajectories spanning 22 distinct robot embodiments** and a wide range of manipulation skills, stored in the **RLDS** (Reinforcement Learning Datasets) format on top of TFDS. It is, as of 2026, the largest open robot-manipulation dataset and the pretraining substrate for essentially every open generalist policy, including both models this week.

The brilliant, slightly ugly trick that makes pooling *possible* is the **lowest-common-denominator action space**. Robots disagree about everything: number of joints, torque vs. position control, gripper kinematics. But almost all of them can be described by a **6-DOF end-effector pose delta plus a 1-DOF gripper command** — a 7-vector `(Δx, Δy, Δz, Δroll, Δpitch, Δyaw, grip)` in the end-effector frame. By projecting every robot's native actions into this common EE-delta space, OXE makes a Franka, a WidowX, and a Google robot speak the same action language. You lose some expressiveness (a redundant 7-DOF arm's null-space motion is gone), but you gain the ability to train one model on all of them. **Internalize this: when OpenVLA emits 7 numbers, those numbers are an EE-delta, not joint commands.** Mapping that EE-delta to your robot's joints is *your* job (MoveIt2 / an IK controller — Week 23), and getting that mapping wrong is a top-three reason a fine-tuned VLA "doesn't work."

### 1.3 RT-1 → RT-2 → RT-X: the lineage

- **RT-1 (2022)** introduced the recipe of treating robot control as **token prediction**: discretize actions into bins, train a transformer to predict the next action token from images + instruction. It worked at scale on a single robot fleet.
- **RT-2 (2023)** had the key idea OpenVLA later open-sourced: **start from a pretrained vision-language model** (trained on web image-text), and co-fine-tune it on robot data so the web knowledge (objects, relations, language) transfers into control. A VLM that already knows what a "strawberry" is needs far less robot data to learn to pick one. This is **VLA = VLM-as-policy.**
- **RT-X (2023)**, the modeling half of the OXE paper, showed that **training RT-1/RT-2-style models on the pooled OXE data beat training on any single dataset** — positive transfer, quantified. That result is the green light for everything this week.

RT-1/RT-2/RT-X were largely closed (Google DeepMind weights and data not fully released). **Octo and OpenVLA are the open re-creations** — same ideas, open weights, fine-tunable on your laptop-plus-cloud-GPU. That is why we teach them: you can actually run them.

It is worth being precise about what "positive transfer" meant in RT-X, because the word gets thrown around loosely. The claim is **not** "a model trained on robot A works zero-shot on robot B." The claim is the more modest and more useful one: a model trained on the *pool* of many robots' data performs *better on each individual robot's tasks* than a model trained on that robot's data alone. The other robots' data acts as regularization and shared-structure transfer — it teaches the general shape of manipulation, which then sharpens the per-robot policy. That is the result that justifies pretraining a generalist at all, and it is also why your fine-tuning works: you are specializing a model that already absorbed the shared structure of a thousand manipulation episodes.

### 1.4 The honest limits

A senior engineer states the limits up front:

- **Zero-shot transfer to *your* setup is weak.** The model never saw your camera angle, your gripper, your lighting, or your objects in your scene. Expect 30–50% at best zero-shot, often much less, and frequently 0% if your camera framing is far from the training distribution. Fine-tuning is not a nicety; it is the job.
- **Action-space heterogeneity is papered over, not solved.** The EE-delta hack works for tabletop manipulation; it does not cleanly cover mobile bases, bimanual coordination, or force control. The capstone's mobile manipulator handles navigation with Nav2 and uses the VLA only for the grasp — exactly because the VLA's action space is EE-deltas.
- **Latency is brutal.** OpenVLA is 7B parameters and autoregressively decodes 7 tokens per action. On an Orin that is far from real-time without heavy optimization (Week 39). Octo is ~270× smaller and far faster but less capable on language. The latency/capability trade-off is real and you will measure it.

### 1.5 What is actually *in* Open X-Embodiment

It helps to know the shape of the data, because a generalist's blind spots are the dataset's blind spots. OXE pooled datasets from many labs, and the mix is heavily weighted toward a few kinds of robot and task:

- **Embodiments.** Mostly fixed-base manipulators — Franka Panda, the WidowX (the Bridge data), Google's mobile manipulator, UR-series arms, the xArm — each with a parallel-jaw gripper. A handful of mobile and bimanual setups exist but are a small minority.
- **Tasks.** Overwhelmingly tabletop manipulation: pick-and-place, push, open/close drawers and doors, simple tool use. Long-horizon, contact-rich, deformable, and high-precision tasks are sparse.
- **Cameras.** A mix of third-person and wrist cameras, but each dataset has its *own* fixed framing. There is no canonical camera pose, which is exactly why your camera framing matters so much at fine-tune time.
- **Action spaces.** Normalized into the EE-delta convention (§1.2), but originally collected in everything from joint-position to Cartesian-velocity control, then projected.

The practical reading: **a VLA pretrained on OXE is strongest at parallel-jaw tabletop manipulation viewed from a roughly OXE-like camera, and weakest at anything structurally novel.** When you choose your fine-tuning task and your camera mount, staying *near* this distribution is free performance; straying far from it is a tax you pay in fine-tuning data. This is not a flaw to complain about — it is a map of where the prior is strong, and a senior engineer designs the robot setup to exploit it.

### 1.6 How to read a VLA paper quickly

You will skim several VLA papers this course (RT-2, OpenVLA, π0, and whatever ships in 2026). A fast, reliable reading order:

1. **The action space.** What does the model output — EE-delta, joint, discrete tokens, continuous via diffusion/flow? This determines how it plugs into *your* controller.
2. **The observation space.** One camera or several? Wrist, third-person, or both? Proprioception included? This determines what sensors you must provide.
3. **The pretraining data.** OXE? A private dataset? This determines the prior's strengths and your fine-tuning burden.
4. **The fine-tuning recipe.** Full, LoRA, or a new head? On how much data? This determines whether *you* can afford to adapt it.
5. **The latency.** Parameters and decoding strategy. This determines whether it runs on your target hardware.

Five questions, five minutes, and you know whether a new VLA is relevant to your robot. Everything else in the paper is detail you read only if the answers are promising.

Applied to the two models this week, the five-question read produces:

| Question | OpenVLA | Octo |
|---|---|---|
| Action space | Discrete tokens → 7-D EE-delta | Continuous chunk → EE-delta |
| Observation space | One image + instruction | Image(s) + language (+ goal image) + proprio |
| Pretraining data | OXE | OXE (~800k) |
| Fine-tuning recipe | LoRA on the LLM | New head ± trunk |
| Latency | High (7B, autoregressive) | Low (small, one diffusion sample) |

That table is the whole lecture in five rows — and it is the template you fill in for the *next* VLA you meet.

---

## Part 2 — Octo: a transformer generalist with a diffusion action head

Octo is the smaller, more "robotics-native" of the two. It is a transformer policy, not a repurposed LLM, designed from the ground up to be a **flexible, fine-tunable generalist**.

### 2.1 The shape of the model

Octo tokenizes its inputs into a single sequence and runs a transformer over them with **block-wise causal attention**:

- **Observation tokens.** Each camera image is patch-tokenized (a small CNN/ViT stem turns an image into a set of tokens). Proprioception (joint angles, gripper state) is tokenized too. These are the "what the robot sees and feels" tokens.
- **Task tokens.** The **language instruction** is tokenized with a pretrained text encoder (a T5-style encoder), producing language tokens. Octo also supports goal-image conditioning.
- **Readout tokens.** Octo inserts learned **readout tokens** into the sequence — think of them as `[CLS]`-like slots whose output embeddings are *read out* and fed to the action head. They attend to observation and task tokens but observation/task tokens do **not** attend back to them, which keeps the representation modular (you can add a new readout + head for a new robot without disturbing the rest).
- **Block-wise causal attention.** Tokens are grouped into blocks (timestep t's observation block, the task block, the readout block). Attention is masked so that, e.g., observations at time `t` can attend to the task and to past observations but not the future. This is what lets Octo consume a short history of observations and predict an action *chunk* for the next several steps.

### 2.2 The diffusion action head

Here is Octo's most important design choice, and the reason it connects directly to your Week 29 Diffusion Policy: **the action head is a diffusion model.** Rather than regressing a single action (which collapses multimodal demonstrations to their mean — the Week 29 lesson) or classifying discrete bins, Octo's head takes the readout-token embedding as conditioning and runs a small diffusion (denoising) process to sample an **action chunk** — a short sequence of future EE-delta actions. This gives Octo the same multimodal-action benefit Diffusion Policy gave you, inside a generalist that also understands language.

This is a genuinely different answer to the "continuous action from a network" problem than OpenVLA's binning, and the contrast is instructive:

- **OpenVLA: discretize, then classify.** Turn the continuous action into 256 bins and predict a bin token. Simple, reuses the LLM's next-token machinery, but quantizes (the 256-bin coarseness) and is autoregressive (slow, 7 sequential tokens).
- **Octo: keep it continuous, sample with diffusion.** No quantization — the action is a real-valued chunk sampled from a learned distribution. Naturally multimodal (two valid grasps → a bimodal sample distribution, not a blurred average). The cost is the diffusion sampling steps, though for a small head these are cheap.

Neither is "correct"; they are two reasonable engineering choices, and the field in 2026 is actively split — some new VLAs (flow-matching policies like π0) follow Octo's continuous-action lineage, while OpenVLA-OFT retrofits a continuous head onto OpenVLA precisely to escape binning. Knowing *both* answers — and *why* each was chosen — is what lets you read the next VLA paper and immediately place it.

### 2.3 Sizes and the fine-tuning story

Octo ships in two sizes: **Octo-Small (~27M parameters)** and **Octo-Base (~93M)**. Both are pretrained on ~800k OXE trajectories. The fine-tuning recipe is the part that matters for you:

- You attach a **new observation tokenizer and/or a new action head** matching *your* robot's sensors and action space.
- You fine-tune on your demos, optionally freezing the transformer trunk and training only the new heads (fastest, least data) or fine-tuning the whole thing (more data, more capability).

Because Octo is tiny, fine-tuning is fast and inference is cheap — single-digit-to-low-tens of milliseconds on a decent GPU. The trade-off: its language grounding, riding on a T5 text encoder rather than a 7B LLM, is weaker than OpenVLA's. For "pick the red one vs. the blue one" Octo is fine; for "put the cup that's behind the bowl onto the leftmost coaster" OpenVLA's LLM prior pulls ahead.

> **The one-line Octo summary:** a small, fast, JAX transformer generalist with a Diffusion-Policy-style action head and learned readout tokens, designed to be re-headed and fine-tuned per robot.

### 2.4 Why readout tokens matter (the modularity payoff)

The readout-token design deserves a second look because it is the mechanism behind Octo's "re-head it for your robot" flexibility, and it is a genuinely clever bit of architecture. The rule is: **observation and task tokens attend among themselves, readout tokens attend to observation/task tokens, but nothing attends *back* to the readout tokens.** That one-directional masking has a consequence: the readout tokens are pure *consumers* of the scene representation. They read it; they do not change it.

Why does that help? Because you can add a *new* readout token and a *new* action head for a new robot — with a different action dimensionality, say — and bolt them onto a pretrained Octo **without disturbing the representation the rest of the network learned.** The new head learns to map the (frozen, already-good) scene representation to the new robot's actions. Contrast a design where the action head's gradients flow back through the whole transformer: re-heading would perturb everything. Octo's masking makes the trunk a stable, reusable feature extractor and the heads cheap, swappable adapters. It is the same instinct as LoRA (freeze the expensive part, adapt a cheap part), expressed in attention masks instead of low-rank deltas.

---

## Part 3 — OpenVLA: the VLM *is* the policy

OpenVLA is the model you fine-tune this week. It is the open re-creation of RT-2: take a strong **vision-language model**, and turn next-token prediction into robot control by making the "next tokens" be **action tokens**.

### 3.1 The backbone: Prismatic-7B

OpenVLA is built on a **Prismatic VLM** with about **7 billion parameters**, composed of:

- **A language model: Llama-2-7B.** This is the autoregressive transformer that does the actual sequence modeling. Its web-scale pretraining is the source of the "knows what objects are and what words mean" prior.
- **A fused dual visual encoder: DINOv2 + SigLIP.** This is the design choice that distinguishes OpenVLA. Rather than a single CLIP-style encoder, OpenVLA concatenates features from **two** vision backbones:
  - **DINOv2** — self-supervised features that are strong on **spatial / geometric** structure ("where are the surfaces and objects, how are they arranged").
  - **SigLIP** — contrastive image-text features that are strong on **semantics** ("this region is a *red cup*").
  Fusing them gives the policy both the *where* (DINOv2) and the *what* (SigLIP), which matters enormously for grounded manipulation. A projection layer maps the fused visual features into the LLM's token-embedding space, so the image becomes a sequence of "visual tokens" the Llama backbone attends to alongside the instruction.

So a single forward pass ingests: **visual tokens** (from the fused encoder) + **instruction text tokens** → the Llama transformer → **action tokens** out.

Why two visual encoders instead of one? The OpenVLA authors found that the fused DINOv2+SigLIP encoder *outperformed* either alone on manipulation, and the reason is intuitive once you name what each provides:

- A semantics-only encoder (SigLIP/CLIP-style) knows *that* there is a red cup, but is comparatively weak at *exactly where* its edges and surfaces are — and a grasp is fundamentally a geometric act.
- A geometry-only encoder (DINOv2-style) knows the spatial layout, but is weaker at *which* object the instruction refers to.

Manipulation needs both: the *what* to obey the instruction and the *where* to actually place the gripper. Fusing the two encoders gives the policy a representation that is simultaneously semantically grounded and geometrically precise. This is the single most-cited architectural reason OpenVLA grasps better than a naive CLIP-backbone VLA, and it is worth remembering when you debug *grounding* vs. *control* failures (Lecture 2 §3.3): grounding failures lean on the SigLIP side, control-placement failures lean on the DINOv2 side.

### 3.2 The prompt-as-task pattern

OpenVLA specifies the task entirely through the **prompt**. The template is, essentially:

```
In: What action should the robot take to {instruction}?
Out:
```

The image is injected as visual tokens at the start, `{instruction}` is your natural-language command ("pick up the red cube"), and the model autoregressively generates the `Out:` continuation — which is **7 action tokens**. The instruction *is* the task specification. Change the sentence, change the behavior — no retraining, in principle. That is the "natural-language steering wheel" the syllabus promises (and Week 37 wires into the mobile manipulator).

### 3.3 Action tokenization — the heart of OpenVLA

This is the mechanism that turns an LLM into a controller, and you must understand it exactly because Exercise 2 makes you implement it. OpenVLA predicts a **7-dimensional continuous action** — the OXE EE-delta `(Δx, Δy, Δz, Δroll, Δpitch, Δyaw, grip)` — but a language model can only emit **discrete tokens**. The bridge is **per-dimension uniform binning**:

1. **Normalize, then bin.** For each of the 7 action dimensions, OpenVLA computes the **1st and 99th percentiles** of that dimension over the training data (using percentiles, not min/max, rejects outliers that would waste bins). It then divides the `[q01, q99]` range into **256 uniform bins**. A continuous action value is mapped to the index `0..255` of the bin it falls into. Values outside `[q01, q99]` clamp to the end bins.
2. **Map bins onto rare LLM tokens.** The Llama tokenizer has ~32,000 tokens. OpenVLA reserves the **256 least-frequently-used token IDs** (the tail of the vocabulary that almost never appears in natural text) and maps bin index `i` to one of those 256 token IDs. Now "action dimension 0 is in bin 137" *is* a specific token the LLM can predict.
3. **Predict 7 tokens.** The model autoregressively emits one token per action dimension — 7 tokens total — which decode to 7 bin indices, which de-bin to 7 normalized values, which **un-normalize** back to real EE-delta units using the same per-dimension stats.

The whole pipeline, both directions:

```
continuous action  a ∈ R^7
        │  normalize per-dim to [q01, q99], clamp
        ▼
   bin index  i ∈ {0..255}^7      (256 uniform bins per dim)
        │  map bin -> reserved rare token id
        ▼
   7 action tokens                 <-- what the LLM predicts
        │  token id -> bin index
        ▼
   bin centers -> normalized values
        │  un-normalize with per-dim (q01,q99) stats
        ▼
continuous action  â ∈ R^7         (EE-delta you send to your IK/MoveIt2 controller)
```

Two things bite everyone, and you will hit both:

- **The un-normalization stats are dataset-specific and must travel with the model.** OpenVLA stores per-dataset normalization statistics keyed by an `unnorm_key`. If you fine-tune on *your* data, your action stats differ from the pretraining data's, and **you must compute and register your own un-norm stats** or the model will emit correctly-shaped but wrongly-scaled actions — the robot twitches by millimeters when it should move centimeters, or lunges. This is the single most common silent fine-tuning bug. We hammer it in Lecture 2 and Exercise 2.
- **256 bins is coarse.** A bin is `(q99 - q01) / 256` wide. For a translation range of, say, ±5 cm, that is sub-millimeter resolution — fine. For a coarse-collected dataset with huge action ranges, bins can be too wide and fine motions get quantized away. Binning resolution is a real limitation of the token-prediction approach, and it is exactly what OpenVLA-OFT's continuous-action head (a stretch-goal read) fixes.

In `transformers`, the whole inference path collapses into one helper, but it is worth seeing what `predict_action` does under the hood so the `unnorm_key` argument stops being magic:

```python
# What model.predict_action(**inputs, unnorm_key=KEY) does, conceptually:
#
# 1. Build the prompt + visual tokens, run the Llama backbone, GENERATE 7 tokens.
generated_ids = model.generate(**inputs, max_new_tokens=7, do_sample=False)
action_token_ids = generated_ids[-7:]              # the 7 action tokens
#
# 2. Token id -> bin index (reverse the rare-token mapping).
bins = VOCAB_SIZE - action_token_ids               # 0..255 per dim
#
# 3. Bin -> normalized value (bin center), per dimension.
norm = (bins + 0.5) / 256.0
#
# 4. UN-NORMALIZE with the stats keyed by unnorm_key.  <-- the load-bearing step
stats = model.norm_stats[unnorm_key]["action"]      # YOUR dataset's stats after fine-tune
q01, q99 = stats["q01"], stats["q99"]
action = q01 + norm * (q99 - q01)                   # back to real EE-delta units
# action is now a 7-vector you hand to your IK/MoveIt2 controller.
```

Read step 4 twice. The `unnorm_key` selects *which* `(q01, q99)` to un-normalize with. Pass the pretraining key after fine-tuning on your data and step 4 silently uses the wrong scale — the exact trap from above. There is no exception because the *bins* (steps 1–3) are perfectly valid; only the final scaling is wrong. This is why Exercise 2 makes you round-trip a known action through *your* stats: it is the one check that catches the trap before it reaches a real arm.

### 3.4 OpenVLA vs. Octo, side by side

| Dimension | OpenVLA | Octo |
|---|---|---|
| Parameters | ~7B | ~27M (Small) / ~93M (Base) |
| Backbone | Prismatic VLM: Llama-2-7B + DINOv2+SigLIP | From-scratch transformer + T5 text encoder |
| Action representation | **Discrete** action tokens (256 bins/dim, rare LLM tokens) | **Continuous** action chunk via a **diffusion head** |
| Language grounding | Strong (7B LLM prior) | Moderate (T5 encoder) |
| Inference latency | High (7B, autoregressive 7 tokens) | Low (small transformer, one diffusion sample) |
| Multimodal actions | Limited by binning + autoregressive | Native (diffusion head, like Week 29) |
| Framework | PyTorch / HF `transformers` | JAX / Flax |
| Fine-tuning | LoRA on the LLM (this week's lab) | New head ± trunk, native recipe |
| Best when | Rich language, harder grounding, GPU available | Latency-bound, simpler language, edge-ish |

Neither is strictly better. The senior takeaway for 2026: **OpenVLA when language grounding is the hard part and you have a GPU; Octo (or a small specialist like last week's ACT) when latency is the hard part.** And — crucially — for many narrow tasks, *last week's ACT or Diffusion Policy beats both*, because a specialist trained on your exact task with no 7B-parameter tax is faster and often more reliable. A generalist earns its keep when you need language conditioning or broad task coverage, not when you have one fixed task you can demo a hundred times.

---

## 3.5 A fully worked tokenization example

Abstract binning is easy to nod along to and hard to get right, so let us do one dimension end to end with numbers. Take the translation dimension `Δx`. Suppose, over your training data, the 1st and 99th percentiles are:

```
q01(Δx) = -0.04 m      q99(Δx) = +0.04 m
```

The bin width is `(q99 - q01) / 256 = 0.08 / 256 = 0.0003125 m = 0.3125 mm`. Now the model wants to encode a specific commanded motion `Δx = +0.015 m` (reach forward 1.5 cm):

1. **Normalize to [0, 1]:** `(0.015 - (-0.04)) / (0.04 - (-0.04)) = 0.055 / 0.08 = 0.6875`.
2. **Bin:** `floor(0.6875 × 256) = floor(176.0) = 176`. So `Δx` is in **bin 176** of 256.
3. **Token:** with `VOCAB_SIZE = 32000` and the last 256 ids reserved, bin 176 maps to token id `32000 - 256 + 176 = 31920`. The LLM predicts token **31920** for this dimension.

De-tokenizing reverses it:

1. **Token → bin:** `31920 - (32000 - 256) = 176`.
2. **Bin → normalized (use the bin center):** `(176 + 0.5) / 256 = 0.6885`.
3. **Un-normalize:** `-0.04 + 0.6885 × 0.08 = -0.04 + 0.05508 = +0.01508 m`.

You commanded `+0.01500` and recovered `+0.01508` — an error of 0.08 mm, well under half a bin width (0.156 mm). **Quantization is the only loss**, and at 0.3 mm bins it is negligible for tabletop manipulation. This is exactly the round-trip Exercise 2 makes you implement; doing it on paper first means the code is just bookkeeping.

Now repeat the de-tokenization with the **wrong** stats — `q01 = -0.20, q99 = +0.20` left over from a different OXE dataset:

1. Bin 176 → normalized 0.6885 (unchanged — the *bins* are right).
2. Un-normalize against the wrong range: `-0.20 + 0.6885 × 0.40 = -0.20 + 0.2754 = +0.0754 m`.

You recover `+0.075 m` instead of `+0.015 m` — **5× too far**, same sign, no error raised. That 5× is precisely the ratio of the two ranges (`0.40 / 0.08`). This is the un-normalization trap from §3.3, and seeing it in arithmetic is why it becomes a bug you *recognize* on a real robot rather than chase for an afternoon.

## 3.6 The data and training story — why this is even possible

A reasonable objection: "how can a 7B model learn robot control from ~1M trajectories when LLMs need trillions of tokens?" Three things make it work, and knowing them sharpens your intuition for when a VLA will and won't transfer.

- **The hard part is pretrained already.** OpenVLA does not learn vision and language from robot data — it *inherits* them from the Prismatic VLM's web-scale pretraining. The robot data only has to teach the *mapping from grounded perception to action*, which is a far smaller learning problem than "what is a cup." This is the RT-2 insight: web knowledge transfers into control.
- **Actions are low-dimensional and structured.** Predicting 7 discrete tokens from a rich visual-language context is a *much* easier target than predicting open-ended text. The output space is tiny (256^7 in principle, but heavily structured by physics), so a modest amount of demonstration data covers it.
- **Cross-embodiment pooling multiplies the data.** A single robot's 50k trajectories would not be enough; OXE's pooled ~1M across 22 embodiments is, because the shared structure (approach, align, grasp, lift) recurs across all of them. Positive transfer (§1.3) is what turns "not enough data per robot" into "enough data across robots."

The flip side, again for honesty: this also predicts the failure modes. A VLA transfers well when your task resembles the pretraining distribution (tabletop pick-and-place with a parallel-jaw gripper — heavily represented in OXE) and poorly when it does not (a suction gripper, a deformable object, a camera angle nothing in OXE used). The pretraining is a prior, and priors help most exactly where the new data resembles the old.

A practical corollary that saves real hours: **before** you fine-tune, run the zero-shot model on a few of your own frames (Exercise 1, Part B). If the zero-shot actions are at least *directional* — the gripper opens near an object, the arm moves toward it — you are near enough to the pretraining distribution that fine-tuning will likely succeed. If the zero-shot actions are pure noise, you are far out of distribution, and you should fix the obvious things (camera framing, image resolution, the gripper convention) *before* spending GPU hours fine-tuning. A failed fine-tune that was doomed by a 90-degree camera-angle mismatch is the most preventable waste of the week, and a thirty-second zero-shot sanity check catches it.

## 3.7 Why the generalist still needs a controller underneath it

One more architectural point that trips people up: **OpenVLA does not move your robot.** It emits an EE-delta — a desired change in end-effector pose plus a gripper command. Something downstream must turn that into joint motion that respects your robot's kinematics, limits, and collisions. That something is the stack you already built: an inverse-kinematics / Cartesian controller or **MoveIt2** (Week 23) that takes the EE-delta target and produces a feasible joint trajectory. The VLA is the *brain* that decides *where the hand should go next*; the controller is the *body* that figures out *how the joints get it there*. Conflating the two — feeding EE-deltas to a joint controller as if they were joint commands — is a top-three reason a fine-tuned VLA "doesn't work," and it is a *control* failure (Lecture 2 §3.3), not a policy failure. Keep the boundary crisp: language + image → VLA → EE-delta → IK/MoveIt2 → joints.

---

## 4. Where this lands in the stack

By the capstone, the picture is: **Nav2** drives the base, **perception** (Weeks 9–16) finds and segments objects, and a **fine-tuned OpenVLA** takes the language instruction + the wrist/scene image and emits the EE-delta that **MoveIt2** (Week 23) turns into a joint trajectory — wrapped in the **safety filter and classical fallback** you build next week (Week 32). The VLA is one component, leashed, not the whole brain. This lecture gave you the component; Lecture 2 makes it yours.

---

## 4.1 Common misconceptions, cleared up

These are the misunderstandings that show up in code review and at the Week 32 midterm. Get ahead of them now.

- **"A VLA is end-to-end pixels-to-torques."** No. OpenVLA is pixels+language-to-**EE-delta**. There is a controller (IK/MoveIt2) between the VLA and the motors. The VLA never sees a joint or a torque.
- **"Zero-shot means I don't need data."** No. Zero-shot means *no fine-tuning*, and zero-shot performance on your setup is usually poor. The whole point of the week is that you *do* need data — your demos — to fine-tune.
- **"Bigger model = better policy."** Not for a fixed narrow task. A 7B VLA is *more general* but not necessarily *more accurate* on one task than a 90M ACT trained on the same demos. Generality and per-task accuracy are different axes.
- **"The action tokens are arbitrary."** No — they are the 256 *least-frequent* Llama tokens, chosen precisely so the model is not torn between emitting an action symbol and emitting that symbol's normal text meaning. The choice is deliberate.
- **"Fine-tuning will fix a bad camera angle."** Partially. Fine-tuning on data *from your angle* helps a lot; but if your angle is wildly outside anything OXE saw and you have few demos, even fine-tuning struggles. Matching the camera to the training distribution is cheaper than fine-tuning your way out of a bad one.
- **"Octo is just a small OpenVLA."** No — different lineage (from-scratch transformer vs. repurposed LLM), different action head (diffusion vs. discrete tokens), different framework (JAX vs. PyTorch). They share the *generalist* idea and the OXE data, not the architecture.

---

## 5. Recap

You should now be able to:

- Explain Open X-Embodiment, the EE-delta lowest-common-denominator action space, and the RT-1→RT-2→RT-X lineage that established positive cross-embodiment transfer.
- Describe Octo: a small transformer generalist with block-wise causal attention, readout tokens, and a Diffusion-Policy-style action head.
- Describe OpenVLA precisely: a 7B Prismatic VLM (Llama-2-7B + fused DINOv2+SigLIP) that predicts discrete action tokens via 256-bin-per-dimension tokenization on the rare tail of the Llama vocabulary.
- Tokenize and de-tokenize a 7-DOF EE-delta the way OpenVLA does, including the un-normalization step and why it must use *your* dataset's stats after fine-tuning.
- Contrast the two action-representation answers — OpenVLA's discrete binning vs. Octo's continuous diffusion head — and say why each was chosen.
- Read a new VLA paper in five questions (action space, observation space, pretraining data, fine-tuning recipe, latency) and decide whether it fits your robot.
- Keep the VLA→EE-delta→IK/MoveIt2→joints boundary crisp, and recognize that feeding EE-deltas to a joint controller is a control failure, not a policy failure.
- State honestly when a generalist is the right tool and when last week's specialist wins.

Next: how to actually fine-tune OpenVLA with LoRA on your Week 29 data in the LeRobot format, and how to evaluate it without lying to yourself. Continue to [Lecture 2 — Fine-Tuning, LeRobot, and Honest Evaluation](./02-finetuning-lerobot-and-honest-evaluation.md).

---

## 6. Where the field is heading (a 2026 footnote)

So you can place these models in their moment: Octo and OpenVLA (both 2024) are the *open foundation* of robot VLAs, and the field has not stood still since. The active directions, all of which build on the ideas in this lecture:

- **Continuous-action VLAs.** OpenVLA-OFT and flow-matching policies (π0-style) replace discrete binning with continuous action heads, attacking both the quantization limit (§3.3) and the latency of autoregressive decoding.
- **Smaller, faster VLAs.** A push toward 1–3B (and below) models that can actually run on edge compute like the Orin, because the 7B latency wall (§1.4) is the main thing keeping VLAs off real-time robots.
- **Better cross-embodiment.** More embodiments in the pretraining pool, and architectures that handle heterogeneous action spaces more gracefully than the EE-delta lowest-common-denominator hack.

None of this changes what you learn this week: the *concepts* — cross-embodiment pretraining, language conditioning, the action-representation choice, mandatory fine-tuning, honest held-out evaluation — are stable, and they are how you'll evaluate whatever ships next. You are learning the grammar, not memorizing one sentence.

---

## References

- *OpenVLA: An Open-Source Vision-Language-Action Model* — Kim et al., 2024: <https://arxiv.org/abs/2406.09246>
- *Octo: An Open-Source Generalist Robot Policy* — Octo Model Team, 2024: <https://arxiv.org/abs/2405.12213>
- *Open X-Embodiment / RT-X* — OXE Collaboration, 2023: <https://arxiv.org/abs/2310.08864>
- *RT-2: Vision-Language-Action Models* — Brohan et al., 2023: <https://arxiv.org/abs/2307.15818>
- *DINOv2*: <https://arxiv.org/abs/2304.07193> — *SigLIP*: <https://arxiv.org/abs/2303.15343>
- *OpenVLA repository*: <https://github.com/openvla/openvla>
