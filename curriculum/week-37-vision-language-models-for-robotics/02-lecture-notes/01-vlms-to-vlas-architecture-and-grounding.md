# Lecture 1 — From VLMs to VLAs: Architecture, Action Tokens, and Grounding

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain how a vision-language model becomes a vision-language-*action* model, describe the two dominant action representations (discrete tokens vs. continuous flow-matching), articulate why cross-embodiment pretraining transfers, and distinguish implicit grounding from the explicit, gateable grounding you'll build the safety case on.

If you remember one sentence from this entire week, remember this one:

> **A VLM answers questions about an image; a VLA answers the question "what should the robot do next?" — and it does so by treating a robot action as just another thing it can output, whether as discretized text tokens (RT-2, OpenVLA) or as a continuous action expert (π0). The magic is that web-scale vision-language knowledge transfers to motor control. The trap is that it transfers *confidence* too, even when it's wrong.**

In 2026 this is the biggest shift in robot autonomy since deep perception. A model that has read the internet knows what a "cup" is, what "red" means, that a "tool" is graspable by its handle — and a VLA wires that knowledge to a gripper. This lecture is the architecture and the grounding; Lecture 2 is the integration, the evaluation, and the leash.

---

## 1. The lineage: VLM → VLA

### 1.1 Vision-language pretraining

It starts with **VLMs** — models trained on huge image-text corpora. Two flavors matter:

- **Contrastive (CLIP-style).** Train an image encoder and a text encoder so that matching image-text pairs have high similarity and mismatched pairs low. The product is a *shared embedding space* where "a photo of a red cup" lands near an image of a red cup. CLIP is the workhorse behind open-vocabulary detection (§5) — it's how you detect objects named by free text instead of a fixed class list.
- **Generative (captioning / VQA).** A vision encoder feeds visual tokens into a language model (PaLI-X, Prismatic/Llava-style architectures), which generates text — a caption, an answer to "what is the person holding?", or a bounding-box description. This generative VLM is the *backbone* a VLA is built from.

The key property both give you: **open-vocabulary understanding.** The model is not limited to a class list someone defined at training time. It understands "the chipped blue mug behind the stapler" compositionally, because it learned language and vision jointly at web scale. That compositional, open-vocab understanding is exactly what a robot needs to follow an instruction it has never seen verbatim.

How the generative VLM is wired, concretely, because it's the backbone you'll fine-tune: a **vision encoder** (often a ViT, sometimes two encoders — a CLIP-style one and a DINO-style one, as in OpenVLA's Prismatic backbone) turns the image into a sequence of **visual tokens**. Those visual tokens are projected into the language model's embedding space and *prepended* to the text tokens, so the language model attends to image and text jointly. The language model (a Llama-class transformer in OpenVLA) then generates output tokens conditioned on both. The visual tokens are how "the red cup" in the text can attend to the cup's pixels in the image — grounding happens *inside* this attention, which is precisely why it's opaque (§5.1). When you fine-tune, you typically update the projection and the language model (and sometimes the vision encoder) on your robot data; the web-scale knowledge in the pretrained weights is the prior you're adapting, not replacing.

### 1.2 The leap to actions: RT-2's trick

A VLM outputs *text*. A robot needs *actions* — say, a 7-DOF end-effector command: Δx, Δy, Δz, Δroll, Δpitch, Δyaw, gripper. How do you make a text model emit a motor command?

RT-2's answer, and the one OpenVLA inherits: **discretize each action dimension into bins, and represent each bin as a token in the model's vocabulary.** A continuous Δx in [−1, 1] becomes one of, say, 256 bins; bin index 137 maps to a specific reserved token. The action "move +5 cm in x, close gripper" becomes a short string of these special tokens. Now the VLA is *literally* a VLM that, given an image and the instruction "pick up the cup," generates a sequence of action tokens instead of a caption. De-tokenize those tokens back to continuous values and you have a robot command.

This is the conceptual core. It sounds almost too cheap to work, and the reason it *does* work is §1.1:

- The model already understands the instruction and the scene from web pretraining — what a cup is, what "red" means, that "left" is a direction.
- Co-training (or fine-tuning) on robot trajectories just teaches it to *also* speak "action" — to map that understanding to the action-token vocabulary.
- The web knowledge comes for free and is the entire point: it's why the model generalizes to objects and phrasings the *robot* data never contained, only the *web* data did.

RT-2's headline result was exactly this transfer: it could follow instructions about objects it had never been shown *in a robot demonstration*, because it had seen them on the web. That generalization-from-web-knowledge is what separates a VLA from a from-scratch imitation policy (weeks 27–30), which only knows what its demonstrations showed. The VLA inherits a world model; the imitation policy starts blank. That inheritance is the whole reason VLAs are the 2026 story — and the reason they *also* inherit the web's confident-wrongness, which the leash exists to catch.

### 1.3 OpenVLA — the open-weight one you fine-tuned

**OpenVLA** (7B parameters) is the open reproduction of this recipe: a Prismatic-style VLM backbone (a Llama-2 7B language model + dual vision encoders), trained on the Open-X Embodiment data with discretized action tokens. It is the model you fine-tuned in week 31. Properties to internalize:

- **7B parameters.** Big enough to carry web knowledge, small enough to run on a single GPU (with quantization on an Orin-class device, slowly). The latency reality of that size is Lecture 2 §6.
- **Action tokens.** Same RT-2 trick: 7-DOF action, each dim discretized, emitted as tokens, de-tokenized to a command.
- **Fine-tuning is mandatory.** Zero-shot OpenVLA on *your* robot, *your* camera, *your* objects is mediocre; fine-tuning on a few dozen-to-hundred demos (week 31) is what makes it usable. The syllabus is blunt about this: "generalist robot models are real, smaller than you think, and finetuning is mandatory."

### 1.4 The 2026 generation: continuous actions (π0 / flow matching)

Discretizing actions into tokens is lossy and clumsy for high-frequency, smooth control. The 2026-current generation — **π0** (Physical Intelligence, open-released as OpenPI) and relatives — keeps the VLM backbone but replaces the discrete action tokens with a **continuous action expert** that uses **flow matching** (a diffusion-family technique) to generate a *chunk* of continuous actions directly. The intuition:

- The VLM backbone processes image + instruction into a rich representation (the "understanding").
- An attached **action expert** module takes that representation and, via flow matching, produces a smooth chunk of continuous actions at high frequency (e.g., 50 Hz control from a slower VLM query) — the same action-chunking + receding-horizon idea you learned with Diffusion Policy and ACT (weeks 29–30), now conditioned on language.

The trade-off for you, the integrator:

- **Discrete-token VLAs (OpenVLA)** are simpler to reason about and de-tokenize — the action is literally a string of tokens you map back to numbers. Easier to debug, slightly coarser control.
- **Continuous VLAs (π0)** give smoother, higher-frequency control and tend to win on dexterous tasks, at the cost of a more complex action head (the flow-matching expert) that's harder to inspect.

But here's the part that makes your life easy: **both are "instruction + image in, action chunk out."** Your integration code (Lecture 2) treats either as a black-box policy with that signature; the gate and fallback you build don't care which. This is the abstraction that lets you swap models without rewriting the safety layer — and you *will* swap models, because the frontier moves every few months.

---

## 2. Cross-embodiment: why one model drives many robots

A striking claim of the RT-X / Open-X Embodiment work: a *single* policy trained across data from *many different robots* (different arms, grippers, cameras) performs **better on each robot** than a policy trained only on that robot's data. That is counterintuitive — you'd expect mixing in *other* robots' data to *dilute* performance on yours, the way training a classifier on off-distribution data usually hurts. Why would mixing robots *help*?

- **Shared physics and semantics.** "Grasp the handle," "move left," "avoid the obstacle" mean the same thing regardless of which arm executes them. The model learns the *task structure* from the union of all robots, then specializes the *motor mapping* per embodiment.
- **Data leverage.** No single robot has enough data to learn general manipulation. Pooling 20+ robots' datasets (Open-X is ~1M+ trajectories across embodiments) gives the model the scale that web-pretraining gave the VLM.
- **Embodiment conditioning.** The model is told (implicitly via the data, or explicitly via a token) which embodiment it's controlling, so it can output the right action space. The shared task structure is learned across all robots; the embodiment-specific motor mapping is selected per robot. You get the breadth of the union and the specificity of the one.

Where it breaks — and you must know this for the safety case:

- **Your robot is out of distribution.** If your gripper, camera placement, or workspace differs materially from anything in the pretraining mix, zero-shot transfer is poor. This is *why fine-tuning is mandatory*: you pull your specific embodiment into the model's distribution.
- **Novel objects/scenes still fail.** Cross-embodiment helps with *motor* transfer, not with grounding an object the model has never seen under lighting it has never seen. That's a §5 grounding problem and a Lecture 2 distribution-shift problem.

The honest 2026 framing: cross-embodiment pretraining gives you a strong *prior*; fine-tuning gives you *competence on your robot*; neither gives you *reliability* — that's the leash in Lecture 2.

### 2.1 The data side — why it dominates the architecture

A recurring lesson across the VLA generation (and one the syllabus repeats in the grasping weeks): **the data matters more than the architecture.** Two practical consequences for you:

- **Demonstration quality sets the ceiling.** Your week-31 fine-tune is only as good as the demonstrations you collected (weeks 27, 29). Sloppy teleop, inconsistent grasps, or demonstrations that don't cover the object poses you'll see at test time cap the VLA's success rate no matter how big the model. When the fine-tuned VLA fails on "pick up the tool," the first question is not "is the model too small?" but "did my demos show the tool in *this* pose, under *this* lighting?"
- **Distribution coverage is the lever.** Cross-embodiment pretraining gives breadth; your fine-tune gives depth on *your* distribution. The gap the VLA fails in is the gap between your fine-tune's distribution and the deployment scene. This is why the failure analysis (Lecture 2 §2) tracks *which* instructions/scenes fail — those are the distribution holes to fill with more demos.

This connects directly to the capstone (Week 44): "fine-tune the policy on 50 capstone-specific demos" is exactly closing the deployment-distribution gap, and the per-instruction eval is how you find which 50 demos to collect. The architecture is mostly fixed (you use OpenVLA or π0); the data is the part you control and the part that moves the number.

A useful mental model for budgeting your effort:

```
performance = pretraining prior (fixed)  ×  fine-tune coverage of YOUR distribution
                 ↑ you don't control            ↑ you control this — spend here
```

You cannot improve the pretraining prior (it's baked into the open checkpoint). You *can* improve fine-tune coverage by collecting demonstrations that span the object poses, lighting, and phrasings you'll meet at test time. So when the number is low, the lever is almost always "collect demos that cover the failing cases," not "find a bigger model." That's the opposite of the instinct you bring from web ML, where the model is the lever and the data is fixed; in robot learning, the data is the lever and the model is fixed.

### 2.2 What "fine-tuning" actually changes

Concretely, fine-tuning OpenVLA on your demos does two things at once: it adapts the **action mapping** (your gripper's geometry, your control frame, your action statistics) so the de-tokenized actions land where you mean, and it adapts the **grounding** toward *your* objects and phrasings. A model fine-tuned on "the red cup" demonstrations grounds "the red cup" more reliably in your scene than the zero-shot model — but only for the objects and phrasings your demos contained. Ask the fine-tuned model for an object it never saw in fine-tuning and you fall back to the (weaker, out-of-distribution) pretraining prior. This is why a fixed, known eval vocabulary (Lecture 2 §2.1) and honest reporting of *out-of-vocabulary* failures matter: the model is competent inside its fine-tune distribution and unreliable outside it, and you must know where the boundary is.

---

## 3. The action representation, concretely

You will write code that takes the VLA's output and dispatches it. So be precise about what comes out.

### 3.1 Discrete-token output (OpenVLA)

A forward pass on (image, instruction) yields a sequence of action tokens. The OpenVLA API de-tokenizes for you into a normalized 7-vector, typically:

```
action = [dx, dy, dz, droll, dpitch, dyaw, gripper]
```

where the first six are an end-effector **delta** (in the robot's control frame) and `gripper` is open/close (or a continuous width). Two things bite integrators:

- **Normalization.** The action is in the *normalized* space the model was trained on (often per-dimension, using the fine-tune dataset's statistics). You must *un*-normalize with the same statistics before sending it to the robot, or your 5 cm move becomes 50 cm. OpenVLA ships the dataset stats with the checkpoint; use them.
- **Frame.** The delta is in a specific frame (commonly the end-effector or a camera-aligned frame). You must apply it in the *right* frame, or "move left" sends the gripper backward. §4 and Lecture 2 §3 are about getting frames right.

### 3.2 Continuous chunk output (π0)

π0 emits a *chunk* of H continuous actions (e.g., 50 actions covering ~1 s at 50 Hz) directly. You execute the first few, then re-query — receding horizon, exactly the DP/ACT pattern. The frame and (often) absolute-vs-delta convention differ by checkpoint; read the model card. The integration shape is the same: chunk out, execute a prefix, re-query.

### 3.3 The chunk + receding-horizon pattern (recap from weeks 29–30)

Whether discrete or continuous, a VLA query is *expensive* (Lecture 2 §6: hundreds of ms for a 7B model). You cannot query it at control rate. So you query for a **chunk** of actions and execute several before re-querying. This pattern buys you three things at once:

- **Latency amortization.** One slow query (300 ms) covers many control cycles, so the per-action cost is the chunk-length divided by the query time, not the full query per action.
- **Smoothness.** Per the Diffusion Policy / ACT lesson (weeks 29–30), committing to a short chunk produces more consistent, less jittery behavior than re-deciding the action every single step from a fresh (and noisy) observation.
- **Reactivity, preserved.** The receding horizon — execute K of H actions, then re-query with a fresh observation — keeps the policy responsive to a changing scene despite the slow query. Tune K: too large and you execute stale actions into a changed world; too small and you pay the query latency too often.

The chunk length and the re-query prefix are the two knobs that trade latency against reactivity, and the right setting depends on your query time and how fast your scene changes — a fast-moving workspace wants a shorter prefix even at a higher query cost.

---

## 4. Frames: the integrator's most common bug

A VLA outputs an action in *some* frame. Your robot expects a command in *its* frame. The single most common "the VLA is broken" bug is actually a frame bug. Three frames in play:

- **Camera frame** — where the image was taken; the VLA "sees" here.
- **End-effector frame** — many VLAs output deltas here ("move forward relative to the gripper").
- **Base / map frame** — what Nav2 and your world model use.

If the VLA outputs an end-effector-frame delta and you apply it as a base-frame delta, "reach forward" becomes "reach in some world direction unrelated to where the gripper points." The fix is the tf2 discipline from Week 2, in three steps:

- **Know the frame the VLA outputs in.** Read the model card / dataset config. OpenVLA's action convention is documented; don't guess. If two checkpoints differ, the frame can differ — check the one you loaded.
- **Transform into the controller's frame.** Use a tf2 lookup from the VLA's output frame to the frame MoveIt2/Nav2 expects, at the observation's timestamp (not `now()` — the robot moved). A wrong-time lookup on a moving base injects the same motion-proportional error as a wrong stamp (Week 5 §3.1).
- **Verify before you trust.** Command a pure +x delta with the gate off and confirm the gripper moves the direction you expect. If it moves sideways or backward, your frame is wrong; fix it *before* any evaluation, because every success number is meaningless until the frame is right.

This is exactly the `frame_id` honesty lesson from Week 5 §3.2, now load-bearing for a learned policy: a VLA that "doesn't work" is, more often than not, a VLA whose perfectly-good output you applied in the wrong frame. The model is fine; the integration lied about the frame.

---

## 5. Grounding: implicit vs. explicit (the heart of the safety story)

**Grounding** is mapping a language phrase to a specific entity in the scene. "The red cup" must become *that* object at *that* pixel/3D location. This is where VLAs are strongest *and* where they fail most dangerously, so we draw a sharp line.

### 5.1 Implicit grounding (what the VLA does internally)

When OpenVLA processes "bring the red cup" with an image, it grounds "red cup" *internally* — somewhere in its attention it attends to the cup's pixels and conditions the action on them. This grounding is **opaque** in a way that matters for safety:

- You get an *action* out, but no inspectable "I believe the red cup is at pixel (412, 302)." The grounding is buried in attention weights you cannot read at runtime.
- If the VLA grounds "red" to an orange under warm light, or to a red stapler in a cluttered scene, there is *no signal in the output* that says so. You find out only when the gripper closes on the wrong object.
- The model emits the wrong action with the *same* output format and the *same* (absent) confidence as a right action. There is nothing to threshold.

Implicit grounding is genuinely powerful — it's compositional, open-vocabulary, and free (you trained for it once). But it is **un-auditable**, and an un-auditable grounding is unsafe to trust *alone* on a robot that can break things or hurt people. The fix is not to make the VLA's internal grounding inspectable (you can't, not reliably) but to run a *second, external* grounding you *can* inspect — which is §5.2.

### 5.2 Explicit grounding (what you build to gate on)

The fix: run an **independent, explicit** grounding you *can* inspect. Use an open-vocabulary detector — **OWL-ViT** or **Grounding-DINO** — that takes the *same* phrase ("red cup") and returns boxes with **confidence scores**. Optionally feed the top box to **SAM** to get a precise mask. Now you have, separately from the VLA:

- *Where* the explicit detector thinks "red cup" is (a box + a 3D point via the depth camera).
- *How confident* it is (a score you can threshold).

This is your **gate** (Lecture 2 §5): if the VLA's action targets a location that *disagrees* with the explicit grounding of the same instruction, reject the action — the VLA is probably grounding to the wrong object. Two independent groundings that agree are trustworthy; two that disagree are a caught hallucination. The whole safety case rests on having a *second opinion* the VLA can't fake.

### 5.3 Open-vocabulary detection in practice (OWL-ViT)

OWL-ViT (Open-World Localization ViT) does zero-shot detection from text queries. The shape, in ~20 lines with Hugging Face `transformers`:

```python
from transformers import OwlViTProcessor, OwlViTForObjectDetection
import torch
from PIL import Image

processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")
model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32")

image = Image.open("scene.png")
queries = [["a red cup", "a blue block", "a tool"]]   # free-text classes
inputs = processor(text=queries, images=image, return_tensors="pt")
with torch.no_grad():
    outputs = model(**inputs)

# Post-process to boxes in pixel coords with scores.
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(
    outputs, threshold=0.1, target_sizes=target_sizes
)[0]
for box, score, label in zip(results["boxes"], results["scores"], results["labels"]):
    print(f"{queries[0][label]}: score={score:.2f} box={box.tolist()}")
```

The exercise (`exercise-02-open-vocab-grounding.py`) wraps this into a node that, given an instruction, extracts the target noun phrase, runs OWL-ViT, and publishes the grounded box + confidence — the signal your gate consumes. Two things about the `score` are load-bearing:

- **The score is your threshold.** Unlike the VLA, OWL-ViT gives you a *calibrated-enough* confidence per detection. You pick a `GROUND_CONF_MIN` below which you treat the object as "not confidently present" (the homework tunes this). That threshold is a real, tunable safety knob — the VLA has none.
- **A low score is itself a signal.** If you ask OWL-ViT for "the red cup" and the best box scores 0.08, the object the instruction names probably *isn't in the scene*. That's the absent-object case (Lecture 2 §4, mode 5; §5.1) caught *before* the VLA's action is even evaluated — you refuse to act on a phantom.

So the explicit grounding does double duty: it's the *reference* the gate compares the VLA's target against, *and* an independent "is the named object even here?" check. Both come from one OWL-ViT call, which is why it's the cheapest high-value addition to the whole stack.

### 5.4 Why two groundings and not just the better one?

A fair question: if OWL-ViT can ground "red cup," why not just use *it* to pick the object and skip the VLA? Because grounding ≠ manipulation. The detector tells you *where* the cup is; it does not tell you *how* to grasp it (the approach pose, the gripper width, the lift trajectory) — that's the VLA's job, learned from demonstrations. You need both: the VLA for the *action*, the detector for an *independent check on the action's target*. Using each for what it's good at, and gating one with the other, is the architecture. This is the same "don't trust one model's confidence; cross-check it" instinct that underlies the whole safety stance of Phase 4–6.

### 5.5 From a 2D box to a 3D target: closing the loop with depth

The gate compares the VLA's action *target* against the detector's *box*. But the VLA's target is a 3D point (a grasp pose), and OWL-ViT gives you a 2D pixel box. To compare them you bring both into a common space. Two directions, and you'll use both:

- **VLA target → image.** Project the VLA's 3D grasp target into the image plane using the camera intrinsics and the tf2 transform from the target's frame to the camera frame (Week 2 / Week 12 calibration). Now it's a pixel you can compare against the OWL-ViT box (the IoU/center-distance check in §6).
- **OWL-ViT box → 3D.** Take the detector's box center, read the depth at that pixel from the RGB-D camera (Week 14), and back-project through the intrinsics to a 3D point in the camera frame, then transform to the base frame. Now you have the *grounded object's* 3D location — which is exactly what the **classical fallback** (Lecture 2 §5.3) grasps when the VLA is rejected. The detector's 3D point is the safe, independent grasp target.

This is why the grounding gate is not just a 2D pixel comparison — it's the bridge between the VLA's learned action and a verifiable 3D location, and the same machinery (box → depth → 3D) produces the fallback's grasp target. The frame discipline from §4 is load-bearing here: a wrong tf2 lookup makes the gate compare the VLA's target against the detector's box *in mismatched frames*, and you'll reject good actions (or accept bad ones) for no reason you can see. Verify the projection on a known object before you trust the gate's verdicts — the same "command a known input, check the known output" discipline as the §4 frame check.

### 5.6 Segmentation for precision: SAM after the box

A bounding box is coarse — for a cluttered scene or a small object, the box may include neighboring objects, and a grasp aimed at the box *center* can land between two things. The standard refinement: feed the OWL-ViT box to **SAM (Segment Anything)** or **SAM 2**, which returns a precise pixel *mask* of the object inside the box. The mask gives you (a) a tighter centroid for the 3D target, (b) the object's extent for a gripper-width estimate, and (c) a cleaner agreement check (mask-IoU instead of box-IoU). For the exercises a box is enough; for the mini-project and the capstone, SAM-refining the box is the difference between "grasp somewhere on the cup" and "grasp the cup's center of mass," and it's a cheap add (one forward pass on an already-cropped region). The pipeline is: open-vocab *detect* (OWL-ViT) → *segment* (SAM) → *back-project* (depth + intrinsics) → 3D target, and that 3D target is both the gate's reference and the fallback's grasp.

---

## 6. A worked grounding-disagreement example

Concrete. Instruction: "bring the red cup." Scene: a red cup at pixel (410, 300) and a red stapler at (620, 280).

- **VLA** processes image + instruction, grounds internally, and (suppose it errs under the warm lighting) emits a grasp action whose target, projected to the image, lands at ~(615, 285) — the stapler.
- **Explicit grounding gate** runs OWL-ViT on "a red cup," gets its top box centered at (412, 302), score 0.86.
- **Gate check:** project the VLA's grasp target into the image, compute IoU (or center distance) against the OWL-ViT box. IoU ≈ 0.03 — they point at *different objects*. **REJECT.** The VLA was about to grasp the stapler; the gate caught it because an independent grounding of the same words disagreed.

Without the gate, the robot grasps a stapler and "completes" the task with full confidence and no error. With the gate, you get a logged rejection and (after K rejections) a fallback. That single example is the entire reason this week is half about grounding and half about the leash.

---

## 7. The VLA landscape in 2026: what to reach for

You will not train a VLA; you will *choose and fine-tune* one. Know the landscape so you can defend the choice at a design review. The open-weight options that matter:

| Model | Size | Action representation | Notes |
|---|---|---|---|
| **OpenVLA** | 7B | Discrete action tokens (RT-2 style) | Open, well-documented, fine-tune recipes published; the C24 default and your week-31 model. Simple to de-tokenize. |
| **Octo** | ~93M–300M | Continuous (diffusion action head) | Smaller, faster, transformer generalist on Open-X; weaker on hard tasks but cheap to run. |
| **π0 / OpenPI** | ~3B+ backbone | Continuous (flow-matching action expert) | 2026-current; smoother high-frequency control; best for dexterous tasks; more complex action head. |
| **π0.5 / successors** | varies | Continuous + better generalization | The moving frontier; check the latest release before committing. |

The decision factors, in order: **(1) does an open checkpoint exist you can fine-tune?** (yes for all above); **(2) does it fit your compute?** (Octo on a modest GPU, OpenVLA/π0 needing more); **(3) discrete vs. continuous actions** — discrete (OpenVLA) is simpler to integrate and debug, continuous (π0) is smoother and better for dexterity; **(4) latency on your edge device** (Lecture 2 §6). For the C24 capstone, OpenVLA is the safe default (it's what you fine-tuned, it's documented, the de-tokenization is transparent); π0 is the upgrade if your task needs dexterous high-frequency control and you have the compute. There is no single "best" — there is "best for this task, this compute, this latency budget," and being able to say *which* and *why* is the senior answer.

The thing that does *not* change across these choices: every one is "instruction + image in, action chunk out," and every one needs the leash. The model is the swappable part; the grounding gate, the frame discipline, and the fallback are the stable parts. Architect so that swapping OpenVLA for π0 next quarter touches one module (`vla_backend`) and nothing else.

### 7.1 The integration mistakes that waste a week (so you don't)

A checklist of the bugs that make engineers say "the VLA is broken" when it isn't. Internalize these before you wire anything:

1. **Forgot to un-normalize.** The de-tokenized action is in the model's normalized space; you must un-normalize with the *checkpoint's* dataset stats (§3.1). Symptom: motions wildly too large or too small. The single most common first-day bug.
2. **Wrong frame.** The delta is in the end-effector/camera frame; you applied it as a base-frame delta (§4). Symptom: "reach forward" goes sideways. Catch it with the pure-+x sanity check before any evaluation.
3. **Stale observation.** You queried the VLA with an image from before the last motion, or stamped it at publish time not acquisition time (Week 5 §3.1). Symptom: the VLA acts on where things *were*, not where they *are* — especially bad with a long chunk prefix.
4. **Querying too fast or too slow.** Querying at control rate (impossible — §6) or executing the whole chunk before re-querying (unreactive). Symptom: either the loop stalls on inference, or the robot blindly executes a stale chunk into a changed scene.
5. **Trusting the VLA's confidence.** There isn't one you should trust (§5.1, Lecture 2 §4). Symptom: "but the model was so confident" right before it grasped the wrong object. The gate is the only confidence that counts.
6. **Wrong unnorm key.** OpenVLA ships per-dataset action statistics; using the wrong dataset's stats un-normalizes incorrectly even though everything *runs*. Symptom: subtly-off actions that look like a model problem but are a config problem. Always set the `unnorm_key` to match your fine-tune dataset.

Five of these six are *configuration/integration* bugs, not *model* bugs. Before you conclude "I need a bigger model" or "the VLA can't do this task," walk this list — the answer is usually here, and it's usually a one-line fix. The same instinct as Week 5's "discovery before QoS before semantics" decision tree: check the cheap, common causes before the expensive, rare ones.

---

## 8. Instruction design: the prompt half of grounding

Before the runtime gate (Lecture 2 §5), there's a cheaper lever: how you *phrase* the instruction to the VLA. A VLA grounds better on instructions that resemble its training distribution, so:

- **Match the training phrasing.** If your fine-tune demos were labeled "pick up the red cup," the VLA grounds "pick up the red cup" better than "fetch me that crimson mug." Use the vocabulary your demos used. This is not the VLA being dumb; it's the distribution lesson (§2.1) applied to *words*.
- **Be specific, not flowery.** "Move the blue block to the left of the plate" grounds better than "tidy up the blocks a bit." Vague instructions force the VLA to *guess* the goal, and guessing is where hallucination lives. The planner in Week 38 will *decompose* vague instructions into specific skill calls — but a raw VLA needs a specific instruction.
- **Disambiguate when the scene is ambiguous.** Two red cups → "the red cup on the left" beats "the red cup." If your instruction is ambiguous and the scene has two matches, the VLA picks *one*, often inconsistently, and you've manufactured a grounding error you could have avoided in the prompt.

This is the "prompt half" of the safety case (a phrase the syllabus uses for Week 38, foreshadowed here): good instruction design *reduces* the rate at which the VLA grounds wrong. But — and this is the asymmetry you'll meet again next lecture — **a well-phrased instruction cannot *prevent* a hallucination; it can only make it less likely.** A VLA can still ground "the red cup on the left" to the right-side cup under bad lighting. The prompt half reduces; only the runtime gate (Lecture 2 §5) *prevents*. Use both: phrase the instruction well to lower the rejection rate, and gate the output to catch what slips through.

---

## 9. A full trace: "bring the red cup," start to action

Tie every piece together in one walkthrough. The robot is at a table; the camera sees a red cup, a blue block, and a tool. The operator says "bring the red cup."

1. **Observe.** The RGB-D camera captures a frame; you stamp it at acquisition (Week 5 §3.1), not after processing. You have an image and a depth map, both in the camera frame, both at time `t`.
2. **Query the VLA.** You pass (image, "bring the red cup") to OpenVLA. ~300 ms later you get a chunk of action tokens. You de-tokenize (§3.1) and un-normalize with the fine-tune dataset's `unnorm_key` stats — getting a 7-vector end-effector delta in the model's control frame.
3. **Frame-transform.** You look up the tf2 transform from the model's control frame to the arm's base frame and apply the delta there (§4). You've already verified, with a pure +x test, that this transform is right — so "reach toward the cup" actually reaches toward the cup.
4. **Explicit grounding (in parallel).** While the VLA was running, you also ran OWL-ViT on the same image with the phrase "red cup" (extracted from the instruction). It returns a box at pixel (412, 302), score 0.86. You read the depth at that box center and back-project to a 3D point in the base frame (§5.5) — the *grounded* cup location.
5. **Gate.** You project the VLA's grasp target into the image and compare with the OWL-ViT box (§6). Suppose they agree (IoU 0.79): the VLA is targeting the same object the independent grounding found. **ACCEPT.**
6. **Dispatch.** The behavior tree routes the accepted grasp to MoveIt2, which plans a collision-free trajectory to the pose. MoveIt2's feasibility check is your affordance gate — if the pose were unreachable or in collision, it'd refuse here (an affordance error caught for free, §5.4 and Lecture 2 §4).
7. **Execute a prefix, re-query.** You execute the first part of the chunk (the approach), then re-observe and re-query with a fresh image — receding horizon — so if the cup shifts or a hand reaches in, the next chunk reacts.

Now replay step 5 with a *disagreement*: the VLA, under warm lighting, targeted the tool instead. The gate's IoU is 0.03 — the VLA and the independent grounding point at different objects. **REJECT, log it, increment the rejection counter.** After three such rejections the behavior tree's fallback branch fires: the classical planner grasps the OWL-ViT-grounded cup location (the 3D point from step 4) — predictable, not clever, and *correct on the object the words actually named*. That is the entire architecture of the week in seven steps plus one fallback: a fast classical safety layer wrapped around a slow, powerful, untrustworthy learned policy. Every later piece — the evaluation, the failure taxonomy, the leash — is detail on top of this skeleton.

---

## 10. Recap

You should now be able to:

- Trace the lineage VLM → VLA: vision-language pretraining (CLIP, captioning VLMs), then RT-2's actions-as-tokens, then OpenVLA (open 7B) and the π0 continuous-action generation.
- Explain the two action representations (discrete tokens vs. flow-matching continuous chunks) and why your integration treats both as "instruction + image in, action chunk out."
- Articulate cross-embodiment transfer, why it gives a strong prior, and why fine-tuning is still mandatory and reliability still isn't free.
- Handle the action output correctly: un-normalize with the dataset stats, apply the delta in the right frame, and use the chunk + receding-horizon pattern to live within the query latency.
- Distinguish implicit grounding (opaque, un-auditable) from explicit grounding (OWL-ViT/G-DINO, inspectable, gateable) and explain why the safety case needs an independent second opinion.
- Run an open-vocab detector to ground an instruction's target and use the disagreement between the VLA's target and the detector's as a caught-hallucination signal.
- Choose a VLA for a task/compute/latency budget, design instructions that ground well, and walk the full instruction-to-action trace including the fallback.

### A note on where this week sits — and where Week 38 goes

It's worth naming the boundary now, because the next week inverts it. This week, **the VLA *is* the policy**: a single instruction maps, in one (chunked) query, to an action. That works beautifully for a *single* primitive task — "pick up the cup" — and it's the right tool when the task is one grasp, one place, one motion. It does *not* compose well: a VLA does not reliably chain "grasp the cup, then the plate, then the bowl, then wipe the table," and it has no symbolic notion of "I've done three of five steps." For *multi-step* tasks you need a level above the VLA — a *planner* that decomposes "clear the table" into a sequence of skills, each of which might be executed *by* a VLA. That's Week 38: the LLM emits a plan over skills; this week's VLA-plus-leash becomes one of those skills. So hold this week as "the policy that does one thing well, safely," and next week as "the planner that sequences many such policies." Both need grounding; both need a leash; the difference is the altitude at which the language model operates — motor actions here, skill sequences there.

Next: wiring the VLA into the robot as a policy, evaluating it honestly on an instruction suite, naming its failure modes, and building the leash. Continue to [Lecture 2 — VLA-as-Policy, Evaluation, and the Safety Leash](./02-vla-as-policy-evaluation-and-the-safety-leash.md).

---

## References

- *OpenVLA*: <https://arxiv.org/abs/2406.09246> · <https://openvla.github.io/>
- *RT-2 (actions as text tokens)*: <https://robotics-transformer2.github.io/>
- *Open X-Embodiment / RT-X (cross-embodiment)*: <https://robotics-transformer-x.github.io/>
- *π0 / OpenPI (flow-matching action expert)*: <https://www.physicalintelligence.company/blog/pi0> · <https://github.com/Physical-Intelligence/openpi>
- *CLIP (vision-language pretraining)*: <https://arxiv.org/abs/2103.00020>
- *OWL-ViT (open-vocab detection)*: <https://arxiv.org/abs/2205.06230>
- *Grounding-DINO*: <https://arxiv.org/abs/2303.05499>
- *Segment Anything (SAM/SAM2)*: <https://segment-anything.com/>
