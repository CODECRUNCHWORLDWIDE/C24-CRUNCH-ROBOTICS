# Challenge 1 — The Multimodal Showdown

**Time estimate:** ~90 minutes.

## Problem statement

You will run the experiment that *proves* the week's thesis: that Diffusion Policy beats behavior cloning **because** it represents multimodal action distributions, and that this is a representational advantage no amount of BC capacity can close.

The shape of the experiment:

1. Design a task that is **provably multimodal** — at some state, two or more *distinct, equally-good* action sequences solve it, and the *mean* of them fails.
2. Collect demonstrations that contain **both** modes (a roughly 50/50 split).
3. Train, on the *exact same demonstrations*, three policies:
   - **BC-small** — a Gaussian-MLP behavior-cloning policy (your Week 27 baseline).
   - **BC-large** — the same architecture scaled up 4–8× in width/depth (to kill the "it just needs more capacity" objection).
   - **Diffusion Policy** — your Exercise 3 / mini-project architecture.
4. Evaluate all three on a *fixed* protocol and produce a success-rate table **and** an action-distribution scatter at the multimodal state.

This is a controlled experiment, not a demo. The control is "same data, same eval"; the variable is the policy class. That's what makes the result *evidence*.

## The task

Use the go-around-an-obstacle task from Exercise 3 (or a manipulation analogue: a block that can be pushed to a goal from either the left or right face). The multimodal state is the start, where left and right are both demonstrated and "straight" hits the obstacle. If you prefer a manipulation task, the canonical one is **push-T**: a T-shaped block reachable from two faces — the original Diffusion Policy task.

Whatever you pick, you must be able to **name the multimodal state** and **state what the mean action does there** (fail, and how).

## Your task

1. **Demonstrations.** Generate or collect ≥ 200 demos with a ~50/50 mode split. Save them. Document the split (count per mode) — if it's lopsided, the BC mean drifts toward the majority mode and your experiment is confounded.
2. **Three policies, same data.** Train BC-small, BC-large, and Diffusion Policy on the identical demo set. Match training budget (epochs/steps) as closely as is fair; note any difference. BC-large must have *clearly* more capacity than BC-small (4–8× parameters).
3. **Fixed eval protocol.** Define it *before* training: N evaluation episodes, fixed seeds, an explicit success criterion (reached goal, didn't hit obstacle). Run all three through it.
4. **The scatter.** At the multimodal state, sample each policy's first action ~512 times (BC is deterministic, so its "samples" are one point plus its Gaussian spread; Diffusion Policy samples vary with the noise seed). Overlay them.
5. **Defeat the capacity objection.** Show BC-large *still* collapses to the mean — more parameters do not fix a representational mismatch. This is the crux; if BC-large suddenly succeeds, you have a *bug* (your task isn't actually multimodal, or BC-large is secretly memorizing), and you must find it.

## Acceptance criteria

- [ ] A file `challenge-01-showdown.md` containing:
  - The task description, the named multimodal state, and what the mean action does there.
  - The demo-set mode split (counts).
  - A success-rate table: BC-small, BC-large, Diffusion Policy, each with N and the success criterion.
  - The action-distribution scatter (figure) at the multimodal state, with all three overlaid.
  - A paragraph interpreting the result: Diffusion Policy shows ≥ 2 clusters and the highest success; both BC variants show a single blob in the invalid middle and lower success; BC-large ≈ BC-small (capacity didn't help).
- [ ] Diffusion Policy's success rate is **meaningfully higher** than both BC variants (on a genuinely multimodal task the gap is large — often 20+ points).
- [ ] BC-large does **not** rescue BC — you've shown the failure is representational, not capacity.
- [ ] The eval protocol was fixed *before* training (state this explicitly; it's an integrity claim).
- [ ] Committed to your Week 29 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The seductive way to "win" this challenge dishonestly is to make the task *unimodal* — e.g., demonstrations that always go left except for noise. Then BC does fine and you've proven nothing. **Verify your task is actually multimodal** before drawing conclusions: the scatter of *demonstrated* (ground-truth) first actions at the multimodal state must itself show two clusters. If the *data* is unimodal, no policy comparison means anything. Check the data first, the policies second.

A subtler trap: if your BC uses a **mixture density network** or a **discretized action head**, it *can* represent multimodality and the comparison is no longer "diffusion vs unimodal BC." That's a legitimate different experiment (and a good stretch), but for the headline result, BC must be the plain Gaussian-MLP — the thing whose limitation the whole week is about.

## Stretch

- Add **BC-MDN** (a mixture-density-network BC with K=2 Gaussians) as a fourth policy. It *should* handle two modes — show it does, then show it gets brittle when you bump the task to *three* modes (you have to re-guess K), while Diffusion Policy handles three modes with no change. This is the "why diffusion over MDN" argument, demonstrated.
- Sweep the **mode split** from 50/50 to 80/20 to 95/5 and plot BC's success vs the split. As the split skews, BC's mean drifts toward the majority and its success *rises* — because the task became *less* multimodal. Diffusion Policy is flat across the sweep. This graph is the cleanest possible statement of the thesis.
- Show the **failure trajectory**: render a BC rollout from the multimodal state and watch it drive straight into the obstacle (the mean action). One video is worth a thousand success-rate cells.

## Why this matters

In Week 32 and in every real design review, "why this architecture?" is the question. Citing the paper is a junior answer; running the controlled experiment that reproduces the paper's claim *on your task* is the senior one. This challenge builds the reflex: when you choose a fancier method, you owe an experiment showing the simpler one actually fails — and you owe the *controlled* version of that experiment, where the only thing that changed is the thing you're arguing about. That discipline is what separates an engineer who follows trends from one who makes defensible choices.
