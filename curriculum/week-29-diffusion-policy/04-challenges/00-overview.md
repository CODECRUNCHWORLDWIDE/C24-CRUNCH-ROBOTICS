# Week 29 — Challenges

The exercises drill the diffusion machinery. **The challenge makes you prove the thesis** — that Diffusion Policy beats behavior cloning *specifically because* it handles multimodality, not for some incidental reason like more parameters or more training. You'll build a task where the difference is unambiguous and measure it.

## Index

1. **[Challenge 1 — The multimodal showdown](./challenge-01-multimodal-showdown.md)** — design a task that is *provably* multimodal, collect demonstrations that contain both modes, train a matched-capacity BC policy and a Diffusion Policy on the *same* data, and show — with a success-rate table and an action-distribution scatter — that BC collapses to the invalid mean while Diffusion Policy keeps both modes. Then defeat the obvious objection ("BC just needs more capacity") by scaling BC up and showing it *still* collapses. (~90 min)

Challenges are optional for passing the week, but this one is the best possible preparation for the Phase 4 midterm (Week 32), where the panel asks "why did you choose Diffusion Policy over plain BC?" — and the only convincing answer is a controlled experiment, not a citation. This challenge *is* that experiment. The engineer who can demonstrate the multimodal failure on demand, and show their architecture choice fixes it, is the one whose design reviews go well.
