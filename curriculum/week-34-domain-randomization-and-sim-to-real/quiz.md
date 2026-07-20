# Week 34 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 35. Answer key is at the bottom — don't peek.

---

**Q1.** What is the core idea of domain randomization?

- A) Make one simulator perfectly realistic so reality matches it.
- B) Train over a *distribution* of deliberately-corrupted simulators wide enough that the real world is just another sample from it — so the policy was never overfit to one sim.
- C) Add random noise to the policy's weights during training.
- D) Train on real data only, never in sim.

---

**Q2.** Which set names the four parts of the sim-to-real gap?

- A) Cost, speed, memory, accuracy.
- B) Visual, dynamics, sensor, latency.
- C) Reliability, durability, history, depth.
- D) Perception, grounding, control, planning.

---

**Q3.** Why is chasing fidelity (pure system ID toward one perfect sim) a losing strategy?

- A) It's illegal under most simulator licenses.
- B) It never finishes (reality has infinite detail), it overfits to one operating point, and the resulting knife-edge policy shatters when reality is slightly off.
- C) It's actually the best strategy and always wins.
- D) Because simulators cannot model friction at all.

---

**Q4.** Which paper is the canonical visual-domain-randomization recipe (textures, lighting, camera pose, distractors)?

- A) OpenAI Dactyl.
- B) Tobin et al., 2017.
- C) AlphaGo.
- D) The Diffusion Policy paper.

---

**Q5.** Which families of randomization matter most for (i) a vision-based grasp policy and (ii) a state-based RL controller?

- A) (i) dynamics only; (ii) visual only.
- B) (i) visual + dynamics (it reads images *and* makes contact); (ii) dynamics (it reads state and produces actions) — match the family to the policy's exposure.
- C) Both need only sensor-noise randomization.
- D) Neither needs randomization.

---

**Q6.** What did OpenAI's Dactyl primarily randomize, and what curriculum technique did it introduce?

- A) Only textures; no curriculum.
- B) Dynamics (mass, friction, motor gains, latency) plus Automatic Domain Randomization (ADR) — widening ranges as the policy improves.
- C) Only the reward function.
- D) Network architecture, via neural architecture search.

---

**Q7.** In a randomization config, why must you sample fresh, independently, per episode/environment?

- A) To save memory.
- B) If you fix the world per run and only vary across runs, you have *domains*, not randomization — the policy still overfits within the run. Fresh per-episode sampling is what prevents overfitting to any single world.
- C) Because seeds are illegal in RL.
- D) Per-episode sampling makes training faster.

---

**Q8.** What is the over-randomization failure mode?

- A) The policy trains too fast and overfits.
- B) Ranges so wide that no single policy can succeed everywhere, so the policy learns maximal conservatism — it barely acts and solves nothing; reward flatlines low.
- C) The simulator crashes from too many parameters.
- D) The policy becomes too aggressive and unsafe.

---

**Q9.** What makes randomizing over a thousand worlds *affordable*, and how does this connect to last week?

- A) Nothing; it's always cheap.
- B) GPU-parallel simulation (Isaac Lab steps many cheap worlds at once) — exactly the throughput vs. fidelity lesson from Week 33; thousand-world randomization needs the parallel throughput.
- C) It requires Gazebo Classic.
- D) Buying more CPUs always suffices.

---

**Q10.** What is the rule for a held-out "real-style" evaluation world?

- A) Reuse the training textures and frictions for consistency.
- B) Its parameters must NOT be drawable from the training distribution — they must be genuinely unseen — or the gap number is contaminated.
- C) It must be photorealistic.
- D) It must use a different physics engine.

---

**Q11.** Define the gap-closure metric.

- A) The randomized policy's nominal-world success.
- B) success_rate(randomized, held-out) − success_rate(nominal, held-out): how much randomization improved performance on the unseen world.
- C) The total training time saved.
- D) The number of randomized parameters.

---

**Q12.** Your randomized policy beats the nominal policy on BOTH the nominal world and the held-out world by a clear margin. What does this most likely indicate?

- A) A perfect result — ship it.
- B) The held-out world is probably contaminated (reuses a trained parameter) or the nominal policy under-fit — the healthy pattern is randomized slightly *worse* on the easy nominal world (the robustness trade) and much better on held-out.
- C) That randomization always helps everywhere.
- D) That the simulator is broken.

---

**Q13.** A teammate says "domain randomization solved sim-to-real; we don't need the safety filter anymore." What's the correct response?

- A) Agreed — randomization is a transfer guarantee.
- B) No: randomization *narrows* the gap probabilistically (only for gaps it sampled), the held-out world is a proxy not reality, and a transferred policy still needs the Week 32 safety wrapper, workspace clamps, and classical fallback.
- C) Agreed — remove the safety filter to reduce latency.
- D) Only if we use Isaac Sim instead of Gz Sim.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Train over a wide distribution of corrupted sims so reality is one more sample. (Lecture 1 §1.3.)
2. **B** — Visual, dynamics, sensor, latency. (Lecture 1 §1.1.)
3. **B** — Never finishes, overfits one operating point, knife-edge shatters. (Lecture 1 §1.2.)
4. **B** — Tobin et al., 2017 — the textbook visual recipe. (Lecture 1 §2.2.)
5. **B** — Match the family to the policy's exposure; a vision grasp needs visual + dynamics, a state controller needs dynamics. (Lecture 1 §2.4, Lecture 2 §3.)
6. **B** — Dynamics randomization + ADR (widening curriculum). (Lecture 1 §2.3, Lecture 2 §2.2.)
7. **B** — Fix the world and you have domains, not randomization; fresh per-episode prevents overfitting. (Lecture 2 §1.1.)
8. **B** — Ranges too wide → maximal conservatism → solves nothing → flatlined low reward. (Lecture 2 §2.3.)
9. **B** — GPU-parallel sim (Isaac Lab) is what makes thousand-world randomization affordable — Week 33's throughput lesson. (Lecture 2 §2.1, Week 33.)
10. **B** — Held-out parameters must be genuinely unseen, or the gap is contaminated. (Lecture 2 §4.1.)
11. **B** — randomized minus nominal success on the held-out world. (Lecture 2 §4.2.)
12. **B** — Likely a leaky held-out world or under-fit nominal; healthy pattern is the robustness trade. (Lecture 2 §4.2, Exercise 3.)
13. **B** — Randomization narrows (doesn't erase) the gap; the safety wrapper still applies. (Lecture 1 §2.5, Lecture 2 §4.3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
