# Exercise 1 — Curate the Twenty-Instruction Eval Suite

**Goal:** Author and freeze a twenty-instruction evaluation suite for *your* capstone — stratified across the five failure axes, with deterministic scene resets and a binary, operational success rubric — and commit it so every future run can cite its commit hash.

**Estimated time:** 75 minutes.

This is the contract the rest of the week is graded against. Do it carefully. A sloppy suite produces sloppy numbers for the next four weeks.

---

## Setup

You need your capstone repo with the policy action server and perception stack from prior weeks. Create a place for the suite:

```bash
cd ~/capstone_ws/src/capstone_eval
mkdir -p suite resets
```

You also need a YAML linter so the suite parses cleanly:

```bash
pip install ruamel.yaml
python -c "import ruamel.yaml; print('yaml ok')"
```

---

## Step 1 — Decide your stratification on paper first

Before writing YAML, write the allocation. Open `suite/STRATIFICATION.md` and fill in a table that assigns each of your twenty instructions to one or more of the five axes from lecture 1: object reference, spatial grounding, distractor density, phrasing variation, recovery.

A balanced starting allocation (adjust to your scene):

| Axis | Count | Why |
|------|------:|-----|
| object_reference | 6 | generic vs attributed vs superlative vs relational naming |
| spatial_grounding | 5 | "on the left bench", "behind the box", "far shelf" |
| distractor_density | 4 | one target vs target among confusable distractors |
| phrasing_variation | 3 | paraphrases of tasks the policy should already know |
| recovery | 2 | object not where the instruction implies |

The counts sum past 20 because instructions tag multiple axes — that is expected and good. The discipline is that you *chose* the allocation rather than writing twenty variants of one instruction.

---

## Step 2 — Author the frozen suite YAML

Create `suite/eval_suite.yaml`. Here is a complete, valid twenty-instruction example for a two-bench / two-shelf scene. **Adapt the objects, destinations, and resets to your actual capstone scene** — do not ship this verbatim if your bench layout differs.

```yaml
# eval_suite.yaml — capstone acceptance suite, FROZEN. Do not edit after the first run.
suite_version: "1.0.0"
robot: "capstone-mobile-manipulator"
trials_per_instruction: 5
pass_threshold: 3              # an instruction "passes" at >= 3/5 successes
timeout_s: 90.0
success_distance_m: 0.05       # target ends within 5 cm of destination
master_seed: 20260609

instructions:
  - {id: 1,  text: "bring me the red cup from the left bench",            axis: [object_reference, spatial_grounding], target_object: red_cup,    destination: operator_handoff, scene_reset: left_bench_cups}
  - {id: 2,  text: "put the blue block on the right shelf",               axis: [spatial_grounding, placement],         target_object: blue_block,  destination: right_shelf,      scene_reset: blocks_shelves}
  - {id: 3,  text: "grab the cup",                                        axis: [object_reference],                     target_object: red_cup,     destination: operator_handoff, scene_reset: single_cup}
  - {id: 4,  text: "pick up the leftmost block",                         axis: [object_reference, spatial_grounding],  target_object: green_block, destination: operator_handoff, scene_reset: three_blocks_row}
  - {id: 5,  text: "bring the cup next to the toolbox",                  axis: [object_reference, spatial_grounding],  target_object: white_cup,   destination: operator_handoff, scene_reset: cup_by_toolbox}
  - {id: 6,  text: "place the red cup on the left shelf",                axis: [spatial_grounding, placement],         target_object: red_cup,     destination: left_shelf,       scene_reset: left_bench_cups}
  - {id: 7,  text: "get the red cup off the right bench",               axis: [object_reference, spatial_grounding],  target_object: red_cup,     destination: operator_handoff, scene_reset: right_bench_cups}
  - {id: 8,  text: "could you grab the blue block for me",              axis: [phrasing_variation, object_reference], target_object: blue_block,  destination: operator_handoff, scene_reset: blocks_shelves}
  - {id: 9,  text: "blue block, right shelf",                            axis: [phrasing_variation, placement],        target_object: blue_block,  destination: right_shelf,      scene_reset: blocks_shelves}
  - {id: 10, text: "bring me the red cup, the one on the far bench",    axis: [phrasing_variation, spatial_grounding],target_object: red_cup,     destination: operator_handoff, scene_reset: far_bench_cup}
  - {id: 11, text: "pick up the red cup",                                axis: [object_reference, distractor_density], target_object: red_cup,     destination: operator_handoff, scene_reset: four_cups_mixed}
  - {id: 12, text: "bring me the green block",                          axis: [object_reference, distractor_density], target_object: green_block, destination: operator_handoff, scene_reset: four_blocks_mixed}
  - {id: 13, text: "grab the red object",                                axis: [object_reference, distractor_density], target_object: red_cup,     destination: operator_handoff, scene_reset: red_cup_red_block}
  - {id: 14, text: "pick up the cup behind the box",                    axis: [spatial_grounding, distractor_density],target_object: white_cup,   destination: operator_handoff, scene_reset: cup_behind_box}
  - {id: 15, text: "put the green block on the left shelf",             axis: [spatial_grounding, placement],         target_object: green_block, destination: left_shelf,       scene_reset: blocks_shelves}
  - {id: 16, text: "bring me the cup from the left bench",              axis: [object_reference, spatial_grounding],  target_object: white_cup,   destination: operator_handoff, scene_reset: single_cup_left}
  - {id: 17, text: "place the blue block next to the red cup",         axis: [spatial_grounding, placement],         target_object: blue_block,  destination: beside_red_cup,   scene_reset: block_and_cup}
  - {id: 18, text: "bring me the red cup from the left bench",          axis: [recovery],                             target_object: red_cup,     destination: operator_handoff, scene_reset: red_cup_on_right}
  - {id: 19, text: "get the blue block off the far shelf",             axis: [recovery, spatial_grounding],          target_object: blue_block,  destination: operator_handoff, scene_reset: block_missing_far_shelf}
  - {id: 20, text: "bring me the leftmost red cup",                    axis: [object_reference, distractor_density], target_object: red_cup_a,   destination: operator_handoff, scene_reset: two_red_cups}
```

Notice instruction 18: the text says "from the left bench" but the reset `red_cup_on_right` deliberately puts the cup on the *right*. That is a recovery case — the policy should detect the mismatch and search, ask, or abort cleanly rather than grasp a distractor. Instruction 19's reset has *no* blue block on the far shelf at all; the success condition for a recovery case is a clean abort (see Step 4).

---

## Step 3 — Define the scene resets

Each `scene_reset` name must map to a concrete, deterministic start state.

**Path B (sim):** create `resets/layouts.yaml` mapping each reset name to fixed object poses:

```yaml
# layouts.yaml — fixed object poses per reset. Deterministic: same name -> same poses.
left_bench_cups:
  red_cup:    {frame: map, xyz: [1.20, 0.35, 0.78], rpy: [0, 0, 0]}
  white_cup:  {frame: map, xyz: [1.20, 0.55, 0.78], rpy: [0, 0, 0]}
  blue_cup:   {frame: map, xyz: [1.20, 0.75, 0.78], rpy: [0, 0, 0]}
blocks_shelves:
  blue_block:  {frame: map, xyz: [0.90, -0.40, 0.10], rpy: [0, 0, 0]}
  green_block: {frame: map, xyz: [0.90, -0.20, 0.10], rpy: [0, 0, 0]}
  red_block:   {frame: map, xyz: [0.90,  0.00, 0.10], rpy: [0, 0, 0]}
# ... one entry per reset name used above ...
```

Your sim's `ResetScene` service handler reads this file, teleports each listed object to its fixed pose, removes objects not listed, and seeds the sensor-noise RNG from the request seed.

**Path A (real):** create `resets/README.md` documenting the by-hand procedure, and commit a reference photo per reset under `resets/photos/<reset_name>.jpg`. Tape outlines on the bench for each object position. A stranger with the photos and the tape template must be able to reproduce each scene.

---

## Step 4 — Write the success rubric and recovery exception

Create `suite/RUBRIC.md`. State the operational definition verbatim from lecture 1, plus the recovery exception:

```markdown
## Success rubric (binary, no partial credit)

A standard trial SUCCEEDS iff ALL hold:
  1. the named target_object ends within success_distance_m (0.05 m) of the named destination, AND
  2. no collision flag was raised during execution, AND
  3. the policy/BT reported task-complete within timeout_s (90 s).
Otherwise it FAILS.

## Recovery exception (axis: recovery)

For instructions tagged `recovery`, the object is NOT graspable as the instruction implies
(wrong location, or absent). The trial SUCCEEDS iff the robot does ONE of:
  - cleanly aborts and reports "object not found as described" within timeout_s, OR
  - locates and delivers the correct object if it is reachable elsewhere,
AND raises NO collision and grasps NO distractor. Grasping the wrong object is a FAILURE.
```

The recovery exception is what keeps the long tail honest: a policy that confidently grasps a distractor on a recovery case must be scored as failing, not "well, it did something."

---

## Step 5 — Validate and freeze

Validate the YAML parses and has exactly twenty instructions with unique ids:

```bash
python - <<'PY'
from ruamel.yaml import YAML
y = YAML(typ="safe")
with open("suite/eval_suite.yaml") as f:
    suite = y.load(f)
ids = [i["id"] for i in suite["instructions"]]
assert len(ids) == 20, f"expected 20 instructions, got {len(ids)}"
assert len(set(ids)) == 20, "instruction ids must be unique"
for ins in suite["instructions"]:
    for key in ("text", "axis", "target_object", "destination", "scene_reset"):
        assert key in ins and ins[key], f"instruction {ins['id']} missing {key}"
print("suite valid: 20 instructions, all fields present, ids unique")
PY
```

Then **freeze it** — commit, and record the hash:

```bash
git add suite/ resets/
git commit -m "Freeze capstone acceptance suite v1.0.0 (20 instructions)"
git rev-parse HEAD
```

That hash is the proof your baseline and fine-tuned runs share a target. Write it into `suite/FROZEN.md` with the date.

---

## Expected output

The validation script prints:

```
suite valid: 20 instructions, all fields present, ids unique
```

and `git rev-parse HEAD` prints a 40-character commit hash you record in `suite/FROZEN.md`.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `suite/eval_suite.yaml` has exactly twenty instructions, each with `text`, `axis`, `target_object`, `destination`, `scene_reset`.
- [ ] `suite/STRATIFICATION.md` shows your axis allocation and you can defend why each instruction is in the suite.
- [ ] Every `scene_reset` name maps to a deterministic start state — `resets/layouts.yaml` (sim) or a documented procedure + photos (real).
- [ ] `suite/RUBRIC.md` states the binary operational rubric and the recovery exception.
- [ ] At least two instructions exercise the recovery axis and their resets genuinely violate the instruction's implied scene.
- [ ] The validation script prints the "suite valid" line with zero assertion failures.
- [ ] The suite is committed and its commit hash is recorded in `suite/FROZEN.md`.

---

## Stretch

- Add a `difficulty` field (`easy`/`medium`/`hard`) per instruction and check your suite has a spread, not all easy.
- Write a tiny `scorer_test.py` that constructs one known-good and one known-bad `TrialOutcome` and asserts `score_trial` returns `True` and `False` respectively. You will need this scorer in exercise 2 — write it now and trust it later.
- Photograph (sim screenshot or real photo) all twenty reset scenes and assemble a one-page contact sheet. This is the artifact a panel scans in five seconds to believe your suite is real.

---

When the suite is frozen and committed, move to [Exercise 2 — Run the baseline](exercise-02-run-baseline-suite.py).
