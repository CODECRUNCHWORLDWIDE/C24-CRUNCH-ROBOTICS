# Lecture 2 — VLA-as-Policy: Integration, Evaluation, Failure Modes, and the Safety Leash

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can wire a VLA into the mobile manipulator as a policy, evaluate it honestly on an instruction suite with per-instruction success rates, name and recognize the five VLA failure modes, build a verification gate + classical fallback that catches hallucinations, and reason about the edge-compute latency that bounds the whole thing.

Lecture 1 gave you the model and the grounding. This lecture makes it *do something on the robot* — safely. The sentence to carry:

> **Wiring a VLA in is an afternoon. Wiring it in so that when it confidently grasps the wrong object the robot doesn't actually do it — that's the week. The safety case for a language-conditioned robot is half prompt, half runtime, and the runtime half is the gate and the fallback.**

---

## Part 1 — The VLA-as-policy integration loop

The architecture, end to end:

```
   text instruction ─────────────┐
                                  ▼
   /camera/image_raw ───────►  VLA policy  ───► action chunk (7-DOF deltas
   (RGB, optionally depth)     (OpenVLA/π0)      or continuous chunk)
                                  │
                                  ▼
                          verification GATE  ◄── explicit open-vocab grounding
                          (accept / reject)       of the instruction (OWL-ViT)
                                  │
                   accept ────────┼──────── reject (K times) ──► classical FALLBACK
                                  ▼                                (week-32 planner)
                         behavior tree dispatch
                          │                 │
                    MoveIt2 (arm)      Nav2 (base)
```

The loop, step by step:

1. **Observe.** Capture the current RGB image (and depth, for 3D targeting). Stamp it at acquisition (Week 5 §3.1 — the stamp matters because the scene moves).
2. **Query the VLA.** Feed (image, instruction) to the VLA. Get an action chunk. This is the slow step (§6).
3. **De-tokenize / un-normalize.** Convert the model output to a robot action in the right units and frame (Lecture 1 §3–4). A frame bug here is the most common "it's broken."
4. **Gate.** Run the explicit grounding of the instruction and check the proposed action's target agrees with it (Lecture 1 §5–6). Accept or reject.
5. **Dispatch.** On accept, the behavior tree routes the action: a grasp goes to MoveIt2, a base motion to Nav2, a gripper command to the gripper. The BT is the integration glue from week 19 — the VLA proposes, the BT executes through the existing motion stack.
6. **Execute a prefix, re-query.** Execute the first few actions of the chunk, then return to step 1 with a fresh observation (receding horizon).

The behavior tree matters: the VLA does **not** drive the motors directly. It proposes actions; the BT (with the gate as a condition node and the fallback as a branch) decides what actually executes. This is the same "ship the learned policy with a leash" structure as week 32, with the VLA in the policy slot and the grounding check as the leash's first link.

One framing to hold onto for the whole lecture: each step in this loop is either a *capability* step (the VLA query, the dispatch) or a *safety* step (the gate, the prefix re-query). The capability steps make the robot useful; the safety steps make it trustworthy. A demo wires only the capability steps and works in the lab; a deployment wires both and works in front of a person. Everything below is detail on the safety steps, because the capability steps are the easy half.

### 1.1 Why dispatch through the existing stack and not raw motor commands

A VLA emits an end-effector delta. You *could* convert that to joint velocities and command the motors raw. Don't — route the grasp pose through **MoveIt2** so you get collision checking, joint-limit enforcement, and a planned trajectory, and route base motion through **Nav2** so you get costmap-aware obstacle avoidance. The VLA decides *what* and *roughly where*; the planners ensure the *how* is feasible and safe. A VLA that says "grasp at (x,y,z)" and a MoveIt2 that refuses because the pose collides with the table is the affordance-error check (§4) happening for free at the motion layer.

There's a deeper architectural reason, too: **layered defense.** The VLA can be wrong about the object (grounding gate catches it), wrong about the reachability (MoveIt2 catches it), or wrong about the velocity (clamps catch it). Each layer catches a different class of error, and none trusts the layer above. Commanding the motors raw from the VLA collapses all three layers into "trust the 7B model completely," which is exactly the bet you must never make. Routing through the existing stack is not bureaucracy; it's the leash's structure.

### 1.2 The behavior tree as the integration glue

Why a behavior tree (week 19) and not an `if/else` in the policy node? Because the BT is *auditable* and *composable* in a way ad-hoc control flow isn't:

- The **gate** is a condition node: "is the VLA's action grounded?" The tree can't proceed to dispatch unless it returns success.
- The **fallback** is a fallback (selector) branch: try the VLA action; if it's rejected K times, fall through to the classical-grasp branch.
- The **safety stops** (E-stop, person-in-workspace) are high-priority condition nodes that pre-empt everything below them.

A reviewer reading your BT in Groot 2 (week 19) can *see* the safety structure — the gate guards the dispatch, the fallback catches the rejections, the E-stop pre-empts all. That visibility is itself a safety-case asset: "here is the tree; here is where a rejected action goes; here is what an E-stop pre-empts." An `if/else` buried in a Python node is none of those things. The BT is where the leash becomes legible.

---

## Part 2 — Evaluating a language-conditioned policy

You cannot improve or trust what you don't measure. The syllabus names three instructions; you build them into a repeatable suite.

### 2.1 The instruction suite

A small, fixed battery of instructions with defined scenes. The three from the syllabus, plus the structure to grow it:

- **"bring the red cup"** — grounding + grasp + (optional) deliver. Tests object grounding by attribute (color) and category.
- **"move the blue block to the left"** — grounding + grasp + place with a *spatial relation*. Tests relational grounding ("left"), a known weak spot.
- **"pick up the tool"** — grounding by category + affordance (grasp the handle). Tests functional grounding.

Notice that the three are deliberately chosen to stress *different* grounding capabilities, which is why you report them separately:

- "the red cup" stresses **attribute grounding** (color) — does the VLA distinguish red from orange under your lighting?
- "the blue block to the left" stresses **relational grounding** (a spatial relation on top of the object) — the hardest of the three (mode 2).
- "the tool" stresses **functional/category grounding** (a category and where to grasp it) — does it grab the handle or the blade?

A suite that only tested "the red cup" three ways would tell you nothing about relational or functional grounding, and your robot would surprise you the first time a user said "to the left." A *good* suite spans the capability space; you grow it (toward the capstone's twenty instructions, Week 44) by adding instructions that probe capabilities the current suite doesn't.

For each instruction define three things, and define them *before* you run, not after (defining success after you see the result is how you fool yourself):

- **The scene** — object placement and lighting, reset identically each trial. Mark start positions; a drifting scene confounds the result.
- **The success criterion** — a *checkable predicate*, not a vibe. "Cup grasped and lifted ≥ 5 cm" is checkable; "did a good job" is not. "Block moved left of its start by ≥ X cm" is checkable; "moved roughly left" is not. The predicate must be something you (or a script) can evaluate yes/no without judgement calls.
- **The number of trials** — N ≥ 10 per instruction for any meaningful rate. A single success proves nothing (the model might have gotten lucky); a single failure proves nothing (it might have been a fluke). Rates need samples.

The discipline of writing the predicate first is the same as a good experiment's pre-registration: it stops you from moving the goalposts to make the number look better. If "bring the red cup" succeeds when the cup is grasped but never delivered, say so in the predicate *before* you run, and report against it consistently.

### 2.2 The protocol

- **Reset the scene the same way** every trial. A drifting scene confounds the result. Mark object start positions; reset to them.
- **Fixed trials per instruction** (e.g., 10–20). Report success **rate** per instruction, not aggregate — aggregate hides which instructions fail.
- **Define partial success.** "Grasped the right object but failed the place" is *not* the same as "grasped the wrong object." A good eval distinguishes grounding success from execution success, because they have different fixes (a grounding failure needs better data/grounding; an execution failure needs better motion).
- **Log everything.** Every trial: instruction, the VLA's grounded target, the gate verdict, the outcome, and the failure mode if it failed. This log *is* the failure analysis (§4, and the homework's headline deliverable).

### 2.3 Honest reporting

The syllabus skill is "honest failure documentation." A result table:

| Instruction | Trials | Grounded right | Executed success | Success rate | Dominant failure |
|---|---:|---:|---:|---:|---|
| bring the red cup | 15 | 14 | 12 | 80% | place slip |
| move blue block left | 15 | 13 | 7 | 47% | spatial: went right |
| pick up the tool | 15 | 11 | 9 | 60% | grounding: grabbed pen |

A table like this is worth more than "it mostly works," because it tells the next engineer *exactly* where to invest: the spatial-relation failure on instruction 2 is the thing to fix, and "47%" is honest where "it works in the demo" is a lie. The reviewer at the Phase milestone is reading for this kind of honesty.

### 2.4 What a single number hides

It's worth dwelling on *why* aggregate-only reporting is not just lazy but actively misleading. Suppose you reported only "62% overall." That number:

- **Hides the bimodality.** 80% on one instruction and 47% on another is a *very different system* from 62% on both — the first has one fixable weak spot, the second is uniformly mediocre. The aggregate erases the distinction.
- **Hides the failure mechanism.** "62%" doesn't tell you whether the failures are grounding (fix: data), spatial (fix: post-check), or execution (fix: motion). The right fix depends entirely on the mechanism, which only the per-instruction, per-mode breakdown reveals.
- **Invites cherry-picking.** A demo shows the 80% instruction; the 47% one never appears. The aggregate makes that omission look honest when it isn't.

The discipline — per-instruction, grounded/executed split, dominant failure, intervention rate — is the same discipline a good ML eval has (per-class metrics, not just top-line accuracy), applied to robots. The cost of an honest table is an afternoon; the cost of a dishonest aggregate is a capstone reviewer (or worse, a deployment) discovering the 47% the hard way.

---

## Part 3 — frames and the re-query cadence (practical integration)

Two practical points that decide whether your integration works:

**Frames (recap, because it's the #1 bug).** The VLA outputs a delta in its training frame (often end-effector or camera-aligned). Before dispatch, transform it into the frame MoveIt2/Nav2 expect with a tf2 lookup, and *sanity-check* once: command a pure +x delta with the gate off and confirm the gripper moves the direction you expect. If it moves sideways, your frame is wrong; fix it before any evaluation, because every failure number is meaningless until the frame is right.

**Re-query cadence.** Execute a *prefix* of the chunk (not the whole thing) before re-querying, so the policy stays reactive to a scene that changed (the object got bumped, a person reached in). Too long a prefix = stale, unreactive; too short = you pay the query latency too often (§6). A common choice: execute ~25–50% of the chunk, then re-query. Tune it against your latency budget.

There's a temporal-ensembling refinement worth knowing (the ACT lesson, week 30): instead of hard-switching from one chunk to the next, you can *blend* the overlapping portions of successive chunks, weighting recent predictions more. This smooths the seam between chunks and reduces the jerk you'd get from re-deciding. For this week a clean prefix-then-re-query is enough; if your execution looks jerky at chunk boundaries, temporal ensembling is the fix, and you've already seen it in week 30.

### 3.1 When to re-query *immediately* (don't wait for the prefix)

The prefix cadence is the *default*, but two events should force an immediate re-query regardless of where you are in the chunk:

- **The gate rejected the current action.** No point executing more of a chunk whose action you just refused — re-query for a fresh proposal (or, after K rejections, fall back).
- **The scene changed materially.** If perception reports the target object moved, or a new obstacle appeared, the chunk you're executing was computed against a stale world. Re-query now, don't finish a stale plan into a changed scene.

This is the reactivity the receding horizon is *for*: the prefix length is how long you're willing to trust a chunk *absent* new information, but new information (a rejection, a scene change) should short-circuit it. A policy loop that rigidly executes its prefix even after the gate rejected the action is wasting cycles being wrong.

---

## Part 4 — The VLA failure taxonomy (name them to catch them)

You cannot gate against a failure you can't name. A failure you can name, you can build a detector for; a failure you can't name reaches the actuators unexamined. So before building the leash, enumerate the ways a VLA goes wrong. Five modes, in rough order of how-dangerous-and-how-silent:

1. **Grounding error.** The VLA acts on the *wrong object* — "red cup" → the red stapler. Cause: ambiguous scene, attribute confusion (color under odd light), category confusion. Caught by: the explicit-grounding gate (§5) — this is the mode the gate exists for.
2. **Spatial-relation error.** Right object, *wrong relation*: "move the block to the left" and it goes right, or "behind the cup" and it goes in front. Cause: spatial reasoning is a known VLA weakness. Caught by: a relation check (did the block actually move left of its start?) — harder to gate pre-execution; often caught post-hoc and counted against the instruction.
3. **Affordance error.** Right object, *infeasible grasp*: a pose that's semantically reasonable but unreachable, in collision, or grabs the wrong part. Cause: the VLA doesn't fully model kinematics/collisions. Caught by: **MoveIt2** refusing the plan (§1.1) — the motion layer is your affordance gate.
4. **Distribution shift.** The deployed scene (lighting, viewpoint, novel object, clutter) is outside the fine-tune distribution; the VLA degrades — more grounding and spatial errors, lower-quality actions. Cause: the fine-tune didn't cover this. Caught by: low explicit-grounding confidence (the detector also struggles, or disagrees) and a rising rejection rate — a *fleet* of rejections is a distribution-shift alarm.
5. **Confident hallucination.** The worst: a wrong action emitted with *no internal uncertainty signal*. VLAs do not natively output calibrated confidence on their actions. Caught by: nothing the VLA tells you — only the *external* gate (grounding disagreement) and the motion-layer feasibility check. This is *the* reason the safety case can't be "trust the model."

The pattern across all five: **the VLA will not tell you when it's wrong.** Every catch comes from an *independent* signal — the explicit grounding, the motion planner, the post-hoc success check. Build those, because the model's own confidence is not a safety signal.

### 4.1 A coverage map: which signal catches which mode

Lay it out as a table, because it's the design spec for your leash — every mode must have at least one catching signal, or it reaches the actuators uncaught:

| Failure mode | Caught by | When |
|---|---|---|
| 1. Grounding error | Explicit-grounding gate (target disagreement) | Pre-execution |
| 2. Spatial-relation error | Post-execution verification (did it end up left?) | Post-execution |
| 3. Affordance error | MoveIt2 feasibility / collision check | Pre-execution (at planning) |
| 4. Distribution shift | Rising rejection rate / low grounding confidence | Aggregate, over time |
| 5. Confident hallucination | The external gate (nothing internal) | Pre-execution |

Read the "When" column: modes 1, 3, 5 are caught *pre-execution* (the action never runs) — these are the ones your gate fully handles. Mode 2 is caught *post-execution* (the action ran; you detect it was wrong and undo/retry) — a fundamentally weaker guarantee, because the wrong action already happened. Mode 4 is caught *over time* (a trend, not a single event). The honest safety case states this clearly: "the gate prevents modes 1/3/5 from reaching the actuators; mode 2 is caught after the fact by a verification step; mode 4 is monitored by the intervention rate." Anyone who claims their gate "catches everything pre-execution" has not thought about mode 2.

---

## Part 5 — The safety leash

The "ship it with a leash" pattern (week 32) extended for language. Three layers, cheapest first.

### 5.1 The verification gate (grounding agreement)

Before executing a VLA action, run the explicit open-vocab grounding of the instruction (Lecture 1 §5.3) and check agreement:

```python
def gate(vla_action, instruction, image, depth) -> tuple[bool, str]:
    """Accept the VLA action only if its target agrees with an INDEPENDENT
    open-vocab grounding of the instruction. Returns (accept, reason)."""
    phrase = extract_target_phrase(instruction)        # "the red cup" -> "red cup"
    boxes, scores = owlvit_detect(image, phrase)
    if len(boxes) == 0 or scores.max() < GROUND_CONF_MIN:
        return False, f"grounding weak: '{phrase}' not confidently in scene"
    target_px = project_action_target_to_image(vla_action, depth)   # where the VLA aims
    best = boxes[scores.argmax()]
    iou = box_point_agreement(best, target_px)         # IoU or center-distance score
    if iou < AGREEMENT_MIN:
        return False, f"VLA target disagrees with grounding (agreement {iou:.2f})"
    return True, f"agreement {iou:.2f}, grounding conf {scores.max():.2f}"
```

Two ways it rejects: (a) the instruction's object isn't confidently *in the scene at all* (the detector can't find a "red cup") — refuse to act on a phantom; (b) the VLA's target *disagrees* with where the object actually is — caught grounding error. Both are logged.

Picking the two thresholds (`GROUND_CONF_MIN`, `AGREEMENT_MIN`) is a real engineering decision with a precision/recall character:

- **`GROUND_CONF_MIN` too low** → phantom objects pass (you act on things that aren't there). **Too high** → valid instructions get rejected because the detector wasn't quite confident enough. The homework tunes this against labeled present/absent scenes.
- **`AGREEMENT_MIN` too low** → a VLA targeting a *nearby wrong* object (the stapler next to the cup) sneaks through. **Too high** → a slightly-off-but-correct VLA target gets rejected and the fallback fires unnecessarily, inflating the intervention rate.

The right operating point catches real errors without rejecting good actions, and you find it empirically (the Challenge 1 calibration-curve stretch). There is no universal value — it depends on your detector, your scenes, and your tolerance for false rejections vs. missed hallucinations. A safety-critical deployment errs toward *over*-rejecting (a false reject costs a fallback; a missed hallucination costs a wrong grasp).

### 5.2 The feasibility gate (MoveIt2 / clamps)

Even an accepted-by-grounding action must be physically safe. Grounding agreement says "the VLA is aiming at the right object"; it says *nothing* about whether the *motion* to get there is safe. So a second, physics-based layer:

- **MoveIt2** plans the grasp; if it's in collision or unreachable, it refuses — affordance error caught. This is the planner doing what it's good at (weeks 23–24): it knows the kinematics and the collision geometry the VLA doesn't.
- **Velocity / acceleration / workspace clamps** (week 32): reject any action exceeding velocity, acceleration, or workspace bounds, regardless of what the VLA or the grounding say. A clamp is the last, dumbest, most reliable line — it doesn't trust anything, it just checks numbers against limits.

The ordering matters: grounding gate first (cheap, catches wrong-object), then MoveIt2 feasibility (catches unreachable/collision), then clamps (catches out-of-bounds velocities). Each layer is cheaper and dumber than the one above and trusts less. The clamp doesn't know what a "cup" is and doesn't need to — it knows the gripper must not exceed 0.3 m/s, and it enforces that against *any* commanded action from *any* source. That's the layer you want to be the most reliable, and it's the simplest, which is not a coincidence: the most safety-critical check should be the one with the fewest ways to be wrong.

### 5.3 The classical fallback

After **K consecutive rejections** (the syllabus's "rejected three times in a row" from week 32), hand control to the **classical fallback**: the non-learned planner (a scripted grasp at the explicit-grounding's location, or a heuristic from week 25). The fallback is less capable but *predictable* — and predictable beats clever-but-wrong when the VLA is clearly struggling. The BT branch:

```
Fallback (Sequence):
  ├─ Condition: vla_rejections >= 3
  ├─ Action: classical_grasp(target = explicit_grounding_location)
  └─ Action: log("fell back to classical after 3 VLA rejections")
```

Measure the **intervention rate** — how often the fallback fires. It's a diagnostic, read it carefully:

- **A high rate** → your VLA is frequently being rejected, which usually means it's out of distribution (mode 4) and needs more fine-tune data covering the failing cases. The fallback is keeping you safe, but a robot that falls back half the time isn't really running its learned policy.
- **A near-zero rate on a hard suite** → suspicious. Either your VLA is genuinely excellent (verify with the success rate), or your gate isn't actually catching anything (is the agreement threshold too loose? is the gate even wired in?). A zero intervention rate with a low success rate is the worst case — the gate is asleep and wrong actions are reaching the actuators.
- **A moderate rate that drops as you add fine-tune data** → exactly what you want to see; it means the fallback is catching real OOD cases and your data collection is closing the gap.

The intervention rate is a first-class metric, same as week 32's "measure intervention rate." Report it alongside success; the two together tell the real story that either alone hides.

### 5.3.1 The fallback must be genuinely safe, not just different

A subtle trap: the classical fallback grasps the *explicit-grounding* location, which is independent of the VLA — good. But the fallback's *grasp* still goes through MoveIt2 and the clamps, because the explicit grounding can *also* be wrong (OWL-ViT is a model too). The fallback is *more trustworthy* than the VLA (it's a simpler, more predictable computation), not *infallible*. So the fallback grasp is still feasibility-checked and clamped. "Predictable" is the fallback's virtue, not "correct" — and predictable-but-still-checked beats clever-but-unchecked. Never let the fallback be the one path that skips the feasibility gate.

### 5.4 "Half prompt, half runtime"

The syllabus line for Week 38 — "the safety case is half-prompt, half-runtime" — starts here. The *prompt* half: phrase the instruction and any system prompt to reduce ambiguity (this matters more when the VLA is a planner, Week 38). The *runtime* half — the gate, the clamps, the fallback — is what this lecture builds, and it's the half that *actually* stops a wrong action, because **a prompt cannot prevent the model from hallucinating; only a runtime check can refuse to execute the hallucination.** Internalize that asymmetry; it's the thesis of the next two weeks.

### 5.5 The operator in the loop

Even with a perfect leash, a deployed language-conditioned robot keeps a human reachable — not for every action, but for the cases the leash can't resolve. This previews the Week 43 operator dashboard and the capstone's "remote teleop takeover," and it's part of the safety case:

- **Escalation on repeated fallback.** If the VLA is rejected and the fallback *also* can't complete the task (the grounding is genuinely ambiguous, or the object isn't graspable), the right move is not to keep trying — it's to *escalate to the operator*: "I can't confidently complete 'bring the red cup'; please advise or take over." A robot that loops forever on an impossible instruction is worse than one that asks for help.
- **Observable decisions.** The operator dashboard should show the VLA's proposed target, the gate's verdict, and the fallback status (the Week 43 "policy actions" and "safety filter status" panels). The operator can *see* the robot reaching for the wrong object *before* it commits, and intervene. The gate is the automatic catch; the operator is the catch for what the gate can't decide.
- **Takeover.** A one-click "pause autonomy and grant teleop" (capstone property #6) lets a human drive when the autonomy is stuck. This is the ultimate fallback — below the classical planner — and it's why the safety case for a shared-space robot is never "fully autonomous," it's "autonomous with an operator who can see and intervene."

The principle: the leash handles the failures it *can* (modes 1, 3, 5 pre-execution; mode 2 post; mode 4 monitored); the operator handles the residual the leash *can't*. A complete safety case names both layers and the boundary between them.

---

## Part 6 — Edge-compute reality: the latency that bounds everything

A 7B VLA is not free. On a Jetson Orin, a single OpenVLA forward pass is on the order of **hundreds of milliseconds** (and worse if you naively run FP32; FP16/INT8 quantization helps but costs accuracy — the Week 39 lesson). That means:

- **You cannot query the VLA at control rate.** Control wants 50+ Hz; the VLA gives you maybe 3–10 Hz. The gap is bridged by **action chunking** (§3.3): one query buys you a chunk of actions to execute over many control cycles.
- **Async inference.** While the robot executes the current chunk, kick off the *next* VLA query in the background, so the next chunk is ready when the current one is consumed — hiding the latency behind execution. π0-style systems do exactly this to sustain smooth control from a slow backbone.
- **The grounding gate adds latency too.** OWL-ViT is cheaper than the VLA but not free. Run it in parallel with (or pipelined against) the VLA query, not serially after, or you double your loop time.
- **The latency is a design constraint, not a bug to optimize away.** "Make the VLA faster" has limits; the architecture (chunk + async + a slower VLA over a fast classical safety layer) is how you ship a usable language-conditioned robot in 2026, not a 50 Hz VLA that doesn't exist at 7B.

This is the Week 39 edge-ML lesson previewed: the latency budget is a first-class artifact, and the VLA is the biggest line item in it. Your mini-project should *measure* the per-instruction latency, because the capstone's ≤ 50 ms perception budget and the VLA's hundreds-of-ms query have to coexist — and they coexist via chunking and async, not magic.

### 6.1 How the two budgets coexist

The capstone wants perception inside 50 ms *and* a VLA that queries in hundreds of ms. These aren't contradictory because they live on *different loops*:

- **The fast loop** (perception, control, safety): runs at 30–50+ Hz. Fused state estimate, obstacle detection, the velocity/workspace clamps, the E-stop. This loop must be fast because it's what keeps the robot safe *between* VLA decisions.
- **The slow loop** (VLA policy): runs at 3–10 Hz. It decides *what* to do next (the action chunk); the fast loop *executes* and *guards* it. The slow loop being slow is fine because the fast loop is reacting to the world the whole time the VLA is thinking.

The design principle: **never put the VLA on the safety-critical fast path.** The clamps and the E-stop must respond in milliseconds regardless of what the VLA is doing — so they run on the fast loop, independent of the VLA query. If a person steps in while the VLA is mid-query, the fast loop's safety stop fires *now*, not after the 300 ms query returns. This separation — slow, smart policy over a fast, dumb safety layer — is the same architecture as the whole leash, viewed through the latency lens. It's also why "make the VLA real-time" is the wrong goal: you don't need it real-time; you need a real-time safety layer *under* it.

A rough per-instruction budget on an Orin, to make it concrete (your numbers will differ):

```
image capture + preprocess        ~5 ms     (fast loop)
VLA forward pass (FP16, 7B)      ~250 ms     (slow loop)  ← the dominant line item
de-tokenize + un-normalize         ~1 ms
OWL-ViT grounding (parallel)     ~120 ms     (overlaps the VLA query, not added)
gate agreement check               ~2 ms
MoveIt2 plan                      ~50 ms
-----------------------------------------------
critical path ≈ 250 ms (VLA) + 50 ms (plan) ≈ 300 ms per re-query
```

Two things to read off this: the VLA dominates (so optimizing anything else is rearranging deck chairs), and the grounding *overlaps* the VLA query rather than adding to it (run them in parallel — §6 below). At 300 ms per re-query and a chunk covering ~1 s of motion, you re-query roughly once per second of execution while the fast loop runs the safety layer at 50 Hz throughout. That's a usable language-conditioned robot, and it's built from a slow policy and a fast guard, not a fast policy.

### 6.2 Quantization and its cost

You'll reach for quantization (FP16, INT8) to speed the VLA on the edge (the Week 39 toolkit). Know the trade-off before you do:

- **FP16** is nearly free in accuracy on most VLAs and roughly halves memory and speeds inference — usually a clear win on an Orin.
- **INT8** is faster still but can cost measurable accuracy, and for a VLA "accuracy" means *grounding and action quality* — i.e., more of the mode-1/mode-2 failures. So you must *re-run your eval suite* after quantizing, not assume the speedup is free. The latency you bought might come back as a lower success rate, and only the per-instruction eval (§2) will show it.

The honest rule: quantize, then re-measure the success rate, and accept the quantization only if the latency win is worth the accuracy cost *for your task*. This is the Week 39 "speedup vs. accuracy delta" discipline, and the VLA is where it bites hardest because its errors are safety-relevant.

---

## 7. Recap

You should now be able to:

- Wire the VLA-as-policy loop: observe → query → de-tokenize/un-normalize → gate → dispatch through the BT to MoveIt2/Nav2 → execute a prefix → re-query.
- Explain why the VLA dispatches through MoveIt2/Nav2 (collision/feasibility/obstacle safety) rather than commanding motors raw.
- Build an instruction suite, run a disciplined eval protocol (fixed resets, N trials, partial-success distinction), and report per-instruction success rates honestly.
- Name the five failure modes (grounding, spatial, affordance, distribution shift, confident hallucination) and say which independent signal catches each.
- Build the three-layer leash: the grounding verification gate, the feasibility gate (MoveIt2 + clamps), and the classical fallback after K rejections — and track the intervention rate.
- Reason about VLA inference latency on the edge, and explain how action chunking + async inference make a hundreds-of-ms 7B model usable for control.
- Separate the fast safety loop from the slow policy loop, and explain why the safety-critical checks must never depend on the VLA query.
- Pick the gate thresholds as a precision/recall trade-off, and read the intervention rate as a distribution-shift signal.
- Locate the operator-in-the-loop layer below the classical fallback, and name the boundary between what the leash catches and what the operator handles.
- Map each of the five failure modes to its catching signal and whether the catch is pre-execution, post-execution, or over-time — and admit which mode (spatial relation) the pre-execution gate cannot catch.

The through-line of the whole lecture, worth saying once more: **the VLA is powerful and untrustworthy, so you build a fast, dumb, reliable safety layer under a slow, smart, fallible policy.** The gate, the clamps, the fallback, the operator, the fast/slow loop split — they are all the same idea at different altitudes. A language-conditioned robot is not "a VLA driving a robot"; it is "a safety architecture that *lets* a VLA drive a robot when, and only when, an independent check agrees." That distinction is the entire safety case, and it's what a Phase-milestone reviewer is listening for.

One last thing to carry into the capstone. The capstone *requires* a VLA that selects the grasp from a language instruction (property #4) and a classical fallback when the policy is rejected three times (property #5) — which is to say, the capstone requires *exactly this lecture's architecture*, not as a nice-to-have but as a graded acceptance criterion. So the `crunch_vla` mini-project you build this week is not a throwaway exercise; it's the literal policy layer of the robot you'll defend at week 48. Build the gate to be auditable, the eval to be honest, and the fallback to actually fire, because a capstone panel will read this code and run this eval. The work you do this week to make a VLA *safe* is the work that lets you put "language-conditioned mobile manipulator with a documented safety case" at the top of your résumé.

Next: the exercises put a real VLA + grounding gate on the robot, and the mini-project builds the full language-conditioned manipulation node with its eval suite. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *OpenVLA (inference, fine-tune, action de-tokenization)*: <https://github.com/openvla/openvla>
- *π0 / OpenPI (async inference, action expert)*: <https://github.com/Physical-Intelligence/openpi>
- *OWL-ViT (the gate's open-vocab detector)*: <https://huggingface.co/docs/transformers/en/model_doc/owlvit>
- *LIBERO / SIMPLER (language-conditioned eval suites)*: <https://libero-project.github.io/> · <https://simpler-env.github.io/>
- *MoveIt2 Python (dispatch a grasp)*: <https://moveit.picknik.ai/main/doc/api/python_api/moveit_py.html>
- *Predictive safety filters / learned-policy safety (week 32 lineage)*: <https://arxiv.org/abs/1905.10732>
