# Exercise 1 — Prompt and Ground: Watch a VLM Succeed and Hallucinate

**Goal:** Run a vision-language model (or your week-31 VLA) on real images and instructions, and develop the single most important instinct of the week: **a VLM grounds language to the scene confidently whether or not it's right, and it will not tell you when it's wrong.** You will produce a small gallery of grounding successes *and* deliberate failures, and learn to read the difference.

**Estimated time:** 45 minutes. Guided. Needs a model you can run a forward pass on (your OpenVLA, an open VLM like a Llava/Qwen-VL checkpoint, or a hosted VLM for the grounding-observation part).

---

## Setup

You need *a* vision-language model that can take an image + a text query and return a grounded answer (a box, a point, or a described location). Options, in order of preference:

1. **Your week-31 fine-tuned OpenVLA** — best, because it's the model you'll deploy. Run its forward pass on (image, "where is the red cup?") and inspect the action target.
2. **OWL-ViT** (the open-vocab detector you'll use in Exercise 2) — returns boxes + scores for text queries. Cleanest for *observing* grounding.
3. **An open generative VLM** (Llava / Qwen-VL class) prompted "Describe the location of the red cup in this image (give a bounding box)."

Capture 4–6 images of a tabletop scene with several objects (a red cup, a blue block, a tool/pen, a distractor or two). Real photos from your robot's camera are ideal; rendered Gz Sim frames are fine.

---

## Step 1 — Easy grounding (it works)

Run the model on three *unambiguous* instructions against a clear scene:

- "Where is the red cup?"
- "Where is the blue block?"
- "Where is the tool?"

For each, record the grounded location (box/point) and overlay it on the image. These should be *correct*. Note the model's confidence if it reports one (OWL-ViT does; a generative VLM usually doesn't — note that absence, it matters).

**Record:** a table of instruction → grounded location → correct? (yes) → reported confidence (if any).

---

## Step 2 — Make it hallucinate (engineer the failures)

Now engineer scenes/instructions that make the model confidently wrong. Try each and record what happens:

1. **Absent object.** Ask "where is the green bottle?" when there is no green bottle. A *robust* model says "not present" or returns a low score; a *typical* VLM confidently points at the nearest greenish or bottle-ish thing. Record which yours does.
2. **Attribute confusion.** Put an orange object next to the red cup under warm lighting and ask for "the red cup." Does it ever point at the orange thing? Warm light shifts colors; this is the classic grounding error (Lecture 2 §4, mode 1).
3. **Ambiguity.** Two cups (one red, one dark red). Ask for "the red cup." Which does it pick, and is it consistent across runs?
4. **Spatial relation.** Ask "what is to the left of the blue block?" Check if the model's notion of "left" matches yours (image-left vs. object-left vs. robot-left). Spatial grounding is a known weak spot (mode 2).

**Record:** for each, the instruction, what the model returned, whether it was right, and — critically — **whether the model gave any signal that it was uncertain.** The headline finding of this exercise is almost always: *it did not.*

---

## Step 3 — The confidence question

Look at your two tables. Answer in writing:

- When the model was **wrong** (Step 2), did its confidence (if any) drop? For OWL-ViT, did the score on an absent object come out low (good) or did it confidently box a wrong object (bad)?
- For a generative VLM with no confidence output, how would you *ever* know it was wrong from the model alone? (Answer: you wouldn't — which is the entire argument for the explicit-grounding gate in Exercise 2.)

This is the realization the week is built on: **the model's confidence is not a reliable safety signal, and a generative VLA gives you no confidence at all.** The gate you build next is the *external* signal.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] A `grounding-gallery.md` with the Step 1 table (≥ 3 correct groundings, overlaid) and the Step 2 table (≥ 3 engineered failures, overlaid).
- [ ] At least one failure where the model was **confidently wrong** — a wrong grounding with high or no-signal confidence.
- [ ] A written answer to Step 3 explaining why the model's own confidence cannot be trusted as a safety signal.
- [ ] One sentence naming which Lecture 2 §4 failure mode each engineered failure corresponds to.

---

## Stretch

- **Same scene, two lightings.** Re-shoot one scene under cool and warm light and re-run "the red cup." Quantify how much the warm light degrades grounding — a concrete distribution-shift (mode 4) measurement.
- **OWL-ViT score sweep.** If you used OWL-ViT, sweep the detection threshold and find the score below which "red cup" returns garbage. That threshold is the `GROUND_CONF_MIN` you'll set in the gate.
- **Two models, one scene.** Run the same instructions on two different VLMs and note where they disagree. Disagreement between two models is itself a (crude) hallucination signal — a preview of the gate's "second opinion" logic.

---

When this feels comfortable, move to [Exercise 2 — Open-vocab grounding](exercise-02-open-vocab-grounding.py).
