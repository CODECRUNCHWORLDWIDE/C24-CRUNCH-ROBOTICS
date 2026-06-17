# Week 38 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 39. Answer key is at the bottom — don't peek.

---

**Q1.** Why use an LLM as a *planner* (emitting a skill sequence) rather than as a *controller* (emitting motor commands)?

- A) LLMs are faster than controllers.
- B) LLMs are good at task decomposition (a language task they've seen millions of) and bad at low-level real-time control; the skills you already built handle the control.
- C) LLMs cannot output text.
- D) Controllers can't use language.

---

**Q2.** SayCan combines two factors. What are they, and why is neither enough alone?

- A) Speed and accuracy; both are needed for real-time.
- B) Say (LLM language-likelihood — what's *useful*) and Can (affordance — what's *possible* now); Say-alone proposes useful-but-impossible actions, Can-alone proposes possible-but-aimless ones. Act on the product.
- C) Vision and language; you need both modalities.
- D) Prompt and temperature; tuning both improves plans.

---

**Q3.** A skill in the skill library has four parts. Which set is correct?

- A) Name, color, weight, price.
- B) A typed signature, a precondition, an effect, and an implementation (that calls the real stack).
- C) A neural network, a dataset, a loss, an optimizer.
- D) A topic, a QoS, a frame, a stamp.

---

**Q4.** The skill library is described as "the C23 bridge." What's the analogy?

- A) Skills are ROS2 topics; C23 used services.
- B) A skill library is an LLM tool/function API; the planner loop is the agent tool-use loop from C23 — with physical grounding and irreversibility as the new concerns.
- C) C23 had no LLMs.
- D) There is no analogy; they're unrelated.

---

**Q5.** What does constrained-grammar / JSON-schema decoding *guarantee* about the planner's output?

- A) That the plan is correct and safe to run.
- B) That the output is well-*formed*: valid structure, only library skills, right argument shape — but NOT that referenced objects exist or the ordering is valid.
- C) That the LLM never hallucinates anything.
- D) That the plan completes the task.

---

**Q6.** "Constrained ≠ grounded." What does grounding add that the grammar cannot?

- A) Faster decoding.
- B) Checking the plan against the real world: referenced objects/locations exist, preconditions hold in sequence — well-*founded*, not just well-formed.
- C) A nicer prompt.
- D) Lower latency.

---

**Q7.** A plan contains `place(cup_1, bin_1)` *before* `grasp(cup_1)`. Both calls are individually valid (real skill, real objects). What catches this, and how?

- A) The grammar — it's malformed.
- B) Static per-call validation — the args are wrong.
- C) Symbolic simulation — applying preconditions/effects in order, `place`'s precondition `holding(cup_1)` is false because `grasp` hasn't run yet.
- D) Nothing catches it; ordering can't be checked.

---

**Q8.** When grounding fails, the recommended response is plan *repair*. What makes repair work?

- A) Re-running the LLM with a higher temperature.
- B) Feeding the *specific* validation errors back ("location 'shelf_top' doesn't exist; valid locations are [bin_1, table_1]") so the LLM fixes exactly that, capped at N retries with a safe-stop fallback.
- C) Asking the LLM to "try again" with no detail.
- D) Switching to a bigger model.

---

**Q9.** Why must the executor be *closed-loop* (re-observe after each skill) even when the plan was perfectly grounded at planning time?

- A) Grounding is unreliable.
- B) The *world* can defy a perfectly-grounded plan at execution time — a grasp slips, a person moves the bin — so the executor must check the expected effect actually happened and re-plan from the real state if not.
- C) The LLM needs to see each step.
- D) ROS2 requires it.

---

**Q10.** The syllabus specifies a *local small* LLM (Llama 3.1 8B). Why local and why small for a robot planner?

- A) Small models are always more accurate.
- B) Local works offline (no cloud dependency/latency/privacy issue); small is enough because planning over a constrained skill library isn't a frontier task (the control was solved by the skills); and seconds-scale latency is fine because planning is infrequent and off the control path.
- C) Large models can't be constrained.
- D) Local models don't need grounding.

---

**Q11.** The safety case is "half-prompt, half-runtime." What can the *prompt* half do, and what can it *not* do?

- A) The prompt guarantees safety; the runtime is optional.
- B) The prompt (skill signatures, forbidden-action statement, few-shots) *reduces* the rate of bad plans but cannot *prevent* a hallucination — a prompt is a suggestion with high compliance, not a hard contract.
- C) The prompt can prevent all bad actions if written carefully.
- D) The prompt half is irrelevant.

---

**Q12.** Which half of the safety case *actually prevents* a bad action from reaching the actuators, and via what mechanisms?

- A) The prompt half, via better wording.
- B) The runtime half: constrained decoding (can't emit a non-library skill), runtime grounding (ungrounded plans can't reach the executor), precondition gates, and human-confirmation gates for irreversible skills — hard checks the model can't talk past.
- C) Neither; safety is best-effort.
- D) The LLM's own confidence score.

---

**Q13.** An object exists in the world but is across the room and unreachable; the plan calls `grasp(it)`. A symbol-only checker (skill exists, object exists) passes it. What's missing, and which SayCan factor does it correspond to?

- A) Nothing's missing; it's fine.
- B) The affordance/reachability check (the "Can" of SayCan) — `grasp`'s precondition includes `reachable(o)`, which the symbol-only checker without affordance data would miss.
- C) The grammar should have caught it.
- D) The temperature was too high.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — LLMs decompose tasks well (language) and control poorly (real-time); the skills handle control. The TAMP split. (Lecture 1 §1.)
2. **B** — Say (useful) × Can (possible); neither alone suffices; act on the product. (Lecture 1 §2.)
3. **B** — Signature, precondition, effect, implementation. (Lecture 1 §3.1.)
4. **B** — A skill library is the LLM tool API; the planner loop is the C23 agent loop, plus physical grounding and irreversibility. (Lecture 1 §3.2.)
5. **B** — Constrained decoding guarantees well-formedness (structure, library skills, arg shape), not correctness. (Lecture 2 §1.3.)
6. **B** — Grounding checks the plan against the real world (objects exist, preconditions hold) — well-founded. (Lecture 2 §2.)
7. **C** — Symbolic simulation applies preconditions/effects in order and catches the violated `holding` precondition. (Lecture 2 §2.2.)
8. **B** — Specific errors fed back, capped retries, safe-stop fallback. Vague "try again" doesn't work. (Lecture 2 §2.3.)
9. **B** — Reality can defy a grounded plan at execution; re-observe, check the effect, re-plan from the real state. (Lecture 2 §3.)
10. **B** — Local = offline/low-latency/private; small = enough (control is in the skills); seconds latency = fine off the control path. (Lecture 2 §4.)
11. **B** — The prompt reduces but cannot prevent bad plans; it's a suggestion, not a hard contract. (Lecture 2 §5.1.)
12. **B** — The runtime half (constrained decoding, grounding, precondition/confirmation gates) is the hard, load-bearing layer. (Lecture 2 §5.2.)
13. **B** — The affordance/reachability check, the "Can" of SayCan, which a symbol-only checker misses. (Lecture 1 §2; Lecture 2 §2; Challenge 1 class 4.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
