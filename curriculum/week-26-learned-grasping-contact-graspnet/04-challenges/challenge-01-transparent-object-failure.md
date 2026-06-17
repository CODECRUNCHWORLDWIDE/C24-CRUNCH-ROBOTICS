# Challenge 1 — The Transparent-Object Failure

**Time estimate:** ~90 minutes.

## Problem statement

Your pick stack works beautifully on a ceramic mug and a cardboard box. Then a teammate puts a **clear plastic cup** on the table and the whole thing falls over: Contact-GraspNet returns *zero* grasps above threshold, the arm does nothing, and the fallback antipodal sampler also produces garbage. Someone says "the network can't handle transparent objects, we need to retrain it." They are **wrong**, and proving why — and fixing it the right way — is this challenge.

You will reproduce the failure, prove with the **depth image** that it is a *perception* (sensor) failure and not a *prediction* (network) failure, then mitigate it with **depth completion** and confirm the grasp returns.

This mirrors the real skill: a learned component fails, the easy story is "the model is bad," and the senior engineer's job is to find that the model never had valid input.

## The harness

Save this as `transparent_scene.py`. It builds two versions of the same scene — one with a normal (opaque) object and one where the object is transparent (the depth sensor returns *zero* over the object's pixels, which is exactly what a real RealSense does on clear plastic). Run it and diagnose from the outputs.

```python
#!/usr/bin/env python3
"""Simulate the transparent-object failure: same object, but the transparent
version has NO depth return over the object's pixels (holes). Do NOT 'fix' this
by lowering the confidence threshold — that is the wrong fix. Find the real one."""
import numpy as np


def make_scene(transparent: bool, H=240, W=320):
    """Return (depth_m, object_mask). Transparent => depth is 0 over the object."""
    fx = fy = 300.0
    depth = np.full((H, W), 0.80, dtype=np.float32)          # table at 0.80 m
    depth += np.random.randn(H, W).astype(np.float32) * 0.002

    # An object: a 60x60 px region raised to 0.60 m (closer to camera).
    oy, ox, oh, ow = 90, 130, 60, 60
    obj_mask = np.zeros((H, W), dtype=bool)
    obj_mask[oy:oy + oh, ox:ox + ow] = True

    if transparent:
        # The IR passes through clear plastic: NO depth return over the object.
        depth[obj_mask] = 0.0                                 # holes!
    else:
        depth[obj_mask] = 0.60                                # solid return

    K = np.array([[fx, 0, W / 2], [0, fy, H / 2], [0, 0, 1]], dtype=np.float32)
    return depth, obj_mask, K


def deproject(depth_m, mask, K):
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    ys, xs = np.nonzero(mask & (depth_m > 0.0))               # valid + in-mask
    z = depth_m[ys, xs]
    x = (xs - cx) * z / fx
    y = (ys - cy) * z / fy
    return np.stack([x, y, z], axis=-1).astype(np.float32)


if __name__ == "__main__":
    for transparent in (False, True):
        depth, mask, K = make_scene(transparent)
        cloud = deproject(depth, mask, K)
        valid_in_mask = int((mask & (depth > 0)).sum())
        print(f"transparent={transparent}: object pixels={int(mask.sum())}, "
              f"valid-depth-in-mask={valid_in_mask}, cloud points={cloud.shape[0]}")
```

```bash
python3 transparent_scene.py
```

You will see the opaque object yields a few thousand object-cloud points; the transparent object yields **zero**. That zero is the whole story.

## Your task

Produce a file `challenge-01-diagnosis.md` with four sections:

1. **Reproduce.** Run the harness (and, if your sim is up, place a transparent object in Gz Sim — or set a material that the depth plugin renders as no-return). Show the grasp node returning zero confident grasps on the transparent object and a normal shortlist on the opaque one.

2. **Diagnose — which bucket?** Prove it is a **perception** failure, not a **prediction** failure (Lecture 2 §4). The proof is the depth image: *there are no valid points over the object.* Quote the harness numbers (`valid-depth-in-mask = 0`) and explain why a network that honestly predicts "no grasp where I have no points" is behaving **correctly**. Explicitly rebut the "retrain the network" proposal.

3. **Mitigate — depth completion.** Fill the holes *before* building the cloud. Two acceptable approaches:
   - A learned completion model (ClearGrasp-style, or Depth-Anything-v2 inpainting from week 13) that predicts plausible depth over the masked holes.
   - For the harness specifically (no real model needed): a **plane/neighborhood inpaint** — estimate the object's surface depth from the *boundary* of the hole (the object is closer than the table, and its rim returns *some* depth at grazing angles), or fall back to interpolating from valid neighbors. Implement `complete_depth(depth, mask)` that fills the zeros so the cloud is non-empty.

4. **Confirm.** Re-run the grasp pipeline on the *completed* depth and show a non-empty grasp shortlist returns. Report how many grasps you recover and whether they cluster on the object.

## Acceptance criteria

- [ ] `challenge-01-diagnosis.md` with all four sections.
- [ ] You correctly classify the failure as **perception** and explicitly state that lowering the confidence threshold is the *wrong* fix (it would only surface low-confidence grasps on the table, not on the object that has no points).
- [ ] A `complete_depth(depth, mask, K)` function that fills the holes; running the pipeline on the completed depth yields a **non-empty** cloud and a **non-empty** grasp shortlist where there were zero before.
- [ ] You name at least one production-grade completion method (ClearGrasp or Depth-Anything-v2) and one multi-view alternative, and say which you'd ship and why.
- [ ] Committed to your Week 26 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The tempting "fix" is to **lower the confidence threshold** from 0.75 to 0.3 so *something* comes back. Do not write this. On the transparent object there are **no points over the object at all**, so there is nothing to lower the threshold *on* — you would only surface marginal grasps on the table and the object's shadow, and the arm would grasp empty air or the table edge. The threshold is not the problem; the missing input is. Prescribing a threshold change here is the exact misdiagnosis the challenge is built to catch.

## Stretch

- **Multi-view recovery.** Instead of completing depth, capture the transparent object from a second viewpoint where specular/refraction geometry happens to return *some* depth, fuse with ICP (week 15), and re-grasp. Compare the recovered grasps to the depth-completion result.
- **Confidence calibration.** On the *opaque* object, sweep the threshold from 0.5 to 0.9 and plot grasp count vs. threshold. This is the curve you tune in deployment — and the curve that does *nothing* for the transparent case, which is the point.
- **Reflective objects.** Modify the harness so the transparent region returns *noisy garbage* depth (random values) instead of zeros — the mirror-finish failure. Show that this is *worse* than holes for the network, because garbage points produce confident-but-wrong grasps, and explain why a validity/confidence mask on the depth is now mandatory.

## Why this matters

In the Phase 4 midterm (Week 32) you defend a learned-policy stack, and the panel *will* ask about its failure envelope. "It fails on transparent objects" is a junior answer. "It fails on transparent objects because the depth sensor returns no points there, which is a perception failure I mitigate with depth completion or multi-view, not a network failure I retrain for" is the answer that gets you hired. Every robotics deployment eventually meets the object that breaks the sensor; the engineer who can name *which layer* failed is the one who fixes it before the demo.
