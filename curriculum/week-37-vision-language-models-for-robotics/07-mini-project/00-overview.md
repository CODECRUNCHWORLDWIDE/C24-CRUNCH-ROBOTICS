# Mini-Project — `crunch_vla`: Language-Conditioned Manipulation, Gated and Measured

> Build the node that takes a plain-English instruction and makes the mobile manipulator do it — *safely*. A VLA proposes actions; an independent open-vocab grounding gate accepts or rejects them; a classical fallback takes over after repeated rejections; and an instruction-suite harness evaluates the whole thing with per-instruction success rates and an honest failure analysis.

This is the artifact that turns this week's two lectures into the system the syllabus asks for: "text instruction in, action chunks out, behavior tree dispatches." It is also the direct ancestor of the capstone's policy layer — the capstone requires "a vision-language model that selects the grasp pose from the language instruction," and *this is that*, with the leash already attached.

**Estimated time:** ~9 hours, split across Thursday, Friday, Saturday, and Sunday in the suggested schedule.

**Compounds forward:** This node becomes the **capstone's policy layer** (capstone required property #4: a VLM that selects the grasp from the instruction; property #5: classical fallback when the learned policy is rejected three times in a row). The instruction suite you build is the seed of the capstone's "twenty-instruction eval suite" (Week 44). The failure analysis is a section of the capstone safety case (Week 41). Build it well now; you will extend, not replace, it.

---

## What you will build

A small ament-python package `crunch_vla` with three deliverables:

1. **`crunch_vla/policy_node.py`** — the integration node. Subscribes to `/camera/image_raw` (+ depth) and an instruction (`/vla/instruction` topic or a goal). Queries the VLA for an action chunk, runs the grounding gate, dispatches accepted actions through the behavior tree to MoveIt2 (arm) / Nav2 (base), falls back to the classical planner after K rejections, and publishes status + every decision to a log.
2. **`crunch_vla/gate.py`** — the verification gate (from Exercise 3, hardened): explicit open-vocab grounding of the instruction, agreement check against the VLA's target, the K-rejection fallback trigger, the velocity/workspace clamps. This is the safety-relevant code; it gets the most tests.
3. **An instruction-suite eval** (`eval/suite.py` + a runner) covering at minimum the three syllabus instructions ("bring the red cup," "move the blue block to the left," "pick up the tool"), each with a defined scene, success criterion, and N trials, producing a per-instruction success-rate table and a failure-mode breakdown.

By the end you have a public repo of ~400–500 lines (excluding the model weights) demonstrating an end-to-end language-conditioned manipulation pipeline with a working safety leash and an honest eval — the portfolio centerpiece of the AI-robotics phase.

---

## Why the gate is a separate, heavily-tested module

You *could* fold the gate logic into the policy node. Don't. `gate.py` is the safety-relevant code — it's what stands between a hallucinating 7B model and your actuators — so it must be (a) independently unit-testable without a GPU or a robot, and (b) auditable in a safety case as one file a reviewer reads. The agreement logic, the confidence threshold, the K-rejection counter, and the clamps are pure functions of their inputs; test them exhaustively with synthetic detections and actions (no model needed), exactly as Exercise 3's stub path demonstrates. The VLA can change (OpenVLA → π0); the gate's contract — "given a proposed action and an instruction, accept/reject" — does not.

---

## Package layout

```
crunch_vla/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_vla
├── crunch_vla/
│   ├── __init__.py
│   ├── policy_node.py        # the integration node (observe→query→gate→dispatch)
│   ├── vla_backend.py        # the VLA wrapper (OpenVLA/π0) behind one interface
│   ├── grounding.py          # the open-vocab detector wrapper (OWL-ViT)
│   ├── gate.py               # the verification gate + clamps + fallback trigger
│   └── fallback.py           # the classical grasp at the grounded location
├── eval/
│   ├── suite.py              # the instruction suite (scenes, criteria, N trials)
│   └── run_eval.py           # runs the suite, prints the success-rate table
└── test/
    ├── test_gate.py          # accept/reject/clamp/fallback-trigger logic (no GPU)
    └── test_grounding.py     # phrase extraction; absent-object -> None
```

If you build a `crunch_vla_msgs` interfaces package, define the instruction and the per-decision log as real `.msg` types. A `std_msgs/String` instruction + a JSON status string is an acceptable minimum.

---

## Deliverable 1 — the gate (`gate.py`)

The heart of the safety story. It must:

- Extract the target phrase from the instruction (Exercise 2's `extract_target_phrase`).
- Run the explicit open-vocab grounding (`grounding.py` / OWL-ViT). If the phrase's object is not confidently in the scene (`score < GROUND_CONF_MIN`), **reject before any action** ("not in scene").
- Given a VLA-proposed action, project its target into the image (via depth + tf2), and compute agreement (IoU / center distance) with the grounded box. Reject if `agreement < AGREEMENT_MIN`.
- Apply **velocity / acceleration / workspace clamps** (week 32): reject any action exceeding bounds, regardless of grounding — the dumb, reliable last line.
- Track **consecutive rejections**; expose `should_fall_back()` true after K (default 3).
- Return a structured verdict (`ACCEPT` / `REJECT(reason)` / `FALLBACK`) and log it.

Every public function is a pure function of (action, instruction, grounding, counters) so `test_gate.py` can cover it without a model. Test, at minimum: an agreeing action accepts; a disagreeing action rejects; an absent object rejects pre-action; an out-of-workspace action rejects via the clamp; three rejections trigger fallback; a clamp rejection still increments the counter.

---

## Deliverable 2 — the policy node (`policy_node.py`)

The integration loop (Lecture 2 §1):

1. On a new instruction, latch it. On each camera frame (or a fixed query rate), capture image + depth (stamped at acquisition).
2. Query `vla_backend` for an action chunk. (`vla_backend` wraps OpenVLA or π0 behind a single `propose(image, instruction) -> Action` interface, so the node doesn't care which VLA.)
3. De-tokenize / un-normalize with the checkpoint's dataset stats; transform the action into the controller's frame (tf2). **Verify the frame once** with a pure +x test before trusting outputs.
4. Run `gate.check(action, instruction, image, depth)`.
5. On `ACCEPT`, dispatch through the BT: a grasp to MoveIt2, base motion to Nav2, gripper to the gripper. On `REJECT`, increment, re-query. On `FALLBACK`, run `fallback.classical_grasp(grounded_location)`.
6. Execute a *prefix* of the chunk, then re-query (receding horizon).
7. Publish `/vla/status` and log every decision (instruction, proposed target, grounded target, verdict, outcome).

Run the VLA query and the grounding in parallel where you can (Lecture 2 §6) so the gate's latency hides behind the VLA's. **Measure and log per-instruction end-to-end latency** — the capstone needs this number.

---

## Deliverable 3 — the instruction-suite eval (`eval/`)

A repeatable evaluation:

- Define the three syllabus instructions, each with: a **scene** (object placement; for sim, a spawn config; for real, marked positions), a **success criterion** (a checkable predicate: cup grasped + lifted; block moved ≥ X cm to the image-left; tool grasped by the handle), and **N ≥ 10 trials**.
- The runner resets the scene the same way each trial, runs the full gated loop, records the outcome and the failure mode if it failed, and prints:

```
INSTRUCTION              TRIALS  GROUNDED  EXECUTED  SUCCESS%  DOMINANT FAILURE   INTERVENTION%
bring the red cup          15       14        12       80%      place slip            7%
move blue block left       15       13         7       47%      spatial (went right)  0%
pick up the tool           15       11         9       60%      grounding (grabbed pen) 20%
------------------------------------------------------------------------------------------------
overall                    45       38        28       62%      -                     9%
```

The **intervention rate** (how often the fallback fired) is a first-class column — it's the mode-4 distribution-shift signal. Report it honestly; a near-zero rate on a hard suite means your gate isn't working.

### A note on 3D targeting

The gate compares the VLA's target against the grounding's *box*, but both must end up in a common space (Lecture 1 §5.5). Your node needs a small piece of geometry: project the VLA's 3D grasp target into the image (intrinsics + tf2) to compare with the OWL-ViT box, and back-project the box center through depth to a 3D point for the fallback's grasp. Get the frames right (Lecture 1 §4); a frame bug here makes the gate compare targets in mismatched frames and reject good actions for no visible reason. Verify the projection on a known object before trusting any gate verdict — the same "known input, known output" discipline as the VLA frame check.

### What "good" looks like

A graded submission is one where a reviewer can run your eval, see a per-instruction table with honest numbers (including a sub-60% instruction, because every real VLA has one), find a logged trace of a caught hallucination, and read a `gate.py` whose accept/reject logic they can audit without a GPU. The anti-pattern — a polished demo of "bring the red cup" working once, with no eval, no caught failure, and the gate folded into the policy node where it can't be inspected — gets a low grade no matter how slick the demo, because it's the exact overconfidence the week warns against. The deliverable is not "the VLA works"; it's "the VLA is *gated*, *evaluated*, and *honest about its failures*."

---

## Rules

- **You may** use OpenVLA / π0 / Octo, OWL-ViT / Grounding-DINO, SAM, PyTorch, `transformers`, and the ROS2 Jazzy + MoveIt2 + Nav2 stack you already have.
- **You must not** dispatch a VLA action to the actuators without it passing the gate. The whole project's reason to exist is that the VLA never reaches the motors unaccompanied.
- **You must not** report only an aggregate success rate. Per-instruction rates and a failure-mode breakdown are required — aggregate hides where it fails.
- **You must** measure and report per-instruction end-to-end latency and the intervention rate.
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy. GPU required for the real VLA; the gate and grounding tests must pass on CPU.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-37-crunch-vla-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_vla` succeeds with no warnings.
- [ ] `gate.py` implements grounding-agreement, the absent-object pre-reject, the workspace clamp, and the K-rejection fallback trigger.
- [ ] `policy_node.py` runs the full loop: VLA → de-tokenize/frame → gate → BT dispatch → re-query, dispatching grasps through MoveIt2.
- [ ] The instruction suite covers the three syllabus instructions and prints a **per-instruction** success-rate table with grounded/executed split, dominant failure, and intervention rate.
- [ ] A hallucination is demonstrably caught: at least one logged trace where the gate REJECTs a wrong-object action and the fallback fires.
- [ ] `colcon test --packages-select crunch_vla` passes, with at least:
  - `test_gate.py`: accept on agreement; reject on disagreement; reject absent-object pre-action; reject out-of-workspace; fallback after 3.
  - `test_grounding.py`: phrase extraction on the three instructions; absent-object returns None.
- [ ] A `README.md` with the architecture diagram, the eval table (with real numbers), the failure analysis, and the measured latency.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **VLA integration** | 20 | Action correctly de-tokenized/un-normalized and frame-transformed; dispatched through MoveIt2/Nav2, not raw motors; receding-horizon re-query. |
| **The gate** | 25 | Grounding-agreement + absent-object reject + clamp + K-rejection fallback; safety-relevant logic isolated in `gate.py` and unit-tested without a GPU. |
| **Fallback** | 10 | Classical grasp at the grounded location fires after K rejections; demonstrated in a trace. |
| **Evaluation** | 25 | Per-instruction success rates with grounded/executed split, dominant failure, intervention rate; honest (no aggregate-only). |
| **Failure analysis** | 10 | Names the modes observed, which signal caught each, and at least one mode the gate can't catch pre-execution. |
| **Docs, tests & hygiene** | 10 | Clear README, passing tests, measured latency, sensible commits, no weights checked in. |

**90+** is portfolio-grade and ready to be the capstone's policy layer. **70–89** works but has a soft gate or aggregate-only eval. **Below 70** means the VLA can reach the actuators un-gated, or the eval is dishonest — fix the gate and the per-instruction reporting first.

---

## Stretch goals

- **Backend swap.** Implement `vla_backend` for both OpenVLA and π0/OpenPI behind the same interface and run the suite on both. Report success rate and latency per backend — a real comparison the field cares about.
- **Two-grounder gate.** Require OWL-ViT *and* Grounding-DINO to agree with the VLA. Measure the change in caught hallucinations and the latency cost.
- **Spatial post-check.** Add the mode-2 mitigation: after a "move X to the left of Y" place, verify X actually ended up left of Y; if not, undo/retry/abort. Report how much it lifts the "move blue block left" success rate.
- **Foxglove overlay.** Stream the VLA target and the grounded box to a Foxglove image panel so an operator *sees* the agreement (or disagreement) live — a direct preview of the Week 43 dashboard's "policy actions" panel.

---

## A debugging note for when it doesn't work

When (not if) the integration misbehaves, walk the failure list from Lecture 1 §7.1 before blaming the model: did you un-normalize with the right `unnorm_key`? Is the action delta in the frame your controller expects (the +x sanity check)? Is the observation stamped at acquisition? Are you trusting the VLA's confidence instead of the gate's? Five of the six common failures are integration/config bugs, not model bugs, and the symptom — "the VLA grasps the wrong place" — is identical for a frame bug and a genuine grounding error. Distinguish them: a *frame* bug makes the gate reject *every* action consistently (the VLA's target is always offset the same way); a *grounding* error rejects intermittently (only when the VLA actually mis-grounds). If the gate rejects everything, suspect the frame; if it rejects sometimes, suspect the model. This decision tree saves the day a reviewer would otherwise spend debugging the wrong layer, and it's exactly the "cheap common causes before expensive rare ones" instinct from Week 5's QoS decision tree.

## How this connects to the rest of C24

- **Week 38 (grounded planners)** replaces the single VLA query with an LLM that emits a *sequence of skills*; your gate and fallback wrap each skill the planner calls. This node's `dispatch` is what the planner's skills bind to.
- **Week 40 (Phase 5 milestone)** you run a language-conditioned pick-and-place end-to-end; this node is the policy in that run.
- **Week 41 (safety case)** the failure analysis here is a section; the gate is a documented mitigation.
- **Week 44 (capstone eval tuning)** the three-instruction suite grows into the twenty-instruction capstone eval. You built the harness four weeks early. Push it, keep the repo, extend it in the capstone.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
