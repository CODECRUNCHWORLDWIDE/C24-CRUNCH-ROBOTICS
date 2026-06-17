# Week 48 — Quiz

Thirteen questions. The last quiz in C24. Take it with your lecture notes closed. Aim for 11/13. Answer key is at the bottom — don't peek.

---

**Q1.** What is the panel ultimately deciding when they sign (or don't sign) your capstone rubric?

- A) Whether your code is elegant.
- B) Whether they would trust you on a robot that operates near people — built from a working robot, a real safety case, and a defense you can hold without bluffing.
- C) Whether you used the most recent ROS2 distro.
- D) How many weeks the project took.

---

**Q2.** Which is the **one unforgivable** failure that fails the capstone regardless of how well the robot demos?

- A) A missing PNG export of the diagram.
- B) A safety-relevant defect left unaddressed in the safety case.
- C) Cold-boot at 61 seconds.
- D) 14 of 20 instructions.

---

**Q3.** In the ninety-minute defense, which segment is where you most pass or fail?

- A) The opening pitch.
- B) The live Q&A — a flawless walkthrough with a weak Q&A loses to a solid walkthrough with a strong Q&A.
- C) Playing the videos.
- D) The acceptance-criteria mapping.

---

**Q4.** Your robot clears 14/20 instructions, one short. What's the strongest move in the defense?

- A) Fudge it to 15 and hope they don't rerun the eval.
- B) State 14/20 honestly, name the two failing instruction classes, and present the failure analysis and fix plan.
- C) Don't mention the instruction count.
- D) Claim the eval suite was unfair.

---

**Q5.** What is the central thesis of a strong safety-case presentation?

- A) "My robot is safe because the policy is good."
- B) "Safety does not depend on the smart parts — the safety layer sits underneath and doesn't trust them."
- C) "My robot has never failed in testing."
- D) "The hardware is high quality."

---

**Q6.** A panelist asks "what if the software E-stop fails?" What framing answers this well?

- A) "It never fails."
- B) The Swiss-cheese model: no single mitigation is perfect, so layers (software E-stop, velocity clamp, hardware E-stop, operator) are arranged so their holes don't line up — all must fail at once for harm.
- C) "Then the robot stops anyway, somehow."
- D) "I didn't consider that."

---

**Q7.** How should you present your residual risk?

- A) Claim there is none.
- B) Name it precisely, quantify it, frame it against a standard, and point to the validation that confirms the bound.
- C) Say "it's probably fine."
- D) Omit the residual-risk section.

---

**Q8.** How do your two chaos-drill postmortems function in the defense?

- A) As a separate, unrelated topic.
- B) As validation evidence in the safety case — proof that the robot fails well, each drill validating a specific mitigation.
- C) As filler if you have time.
- D) As a list of bugs you didn't fix.

---

**Q9.** The panel asks "what else could break that you didn't drill?" What's the strong answer?

- A) "Nothing — I covered everything."
- B) A specific un-drilled failure, why it matters (which mitigation it stresses), and how you'd drill it next.
- C) "I'm not sure."
- D) Repeat the two drills you already did.

---

**Q10.** A panelist asserts "an EKF is exact for nonlinear systems, right?" What should you do?

- A) Agree, to be agreeable.
- B) Catch and correct it — the EKF linearizes, so it's not exact; that approximation error is what you tune Q to absorb. Catching a false premise scores big.
- C) Change the subject.
- D) Say "I think so."

---

**Q11.** You reach the genuine edge of your knowledge during the Q&A. What's the pass?

- A) Bluff a confident answer.
- B) Say "I didn't go deeper than X; here's how I'd find out" — naming your knowledge boundary is itself senior.
- C) Make something up that sounds plausible.
- D) Stay silent.

---

**Q12.** Why is the public retro a stronger artifact than a list of wins?

- A) It's shorter.
- B) It demonstrates the ability to learn from your own work — specific regrets with transferable lessons — which is what employers most want and most struggle to assess.
- C) GitHub requires it.
- D) Wins are forbidden in a retro.

---

**Q13.** What is the highest-value thing you do *this week* to prepare?

- A) Add more features to the robot.
- B) Run the full ninety-minute mock defense against the real rubric before the real one — it finds the gaps while they're cheap to fix.
- C) Rewrite the code style.
- D) Add more badges to the README.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Trust on a robot near people, built from a working robot, a real safety case, and a bluff-free defense. (Lecture 1 §intro.)
2. **B** — An unaddressed safety-relevant defect fails the capstone regardless of demo quality (per the spec). (Lecture 1 §4.)
3. **B** — The live Q&A is the largest block and where you pass or fail. (Lecture 1 §2.)
4. **B** — Honest 14/20 with a failure analysis beats a fudged 15 the panel reruns. (Lecture 1 §4; honesty note.)
5. **B** — Safety doesn't depend on the smart parts; the safety layer bounds any component. (Lecture 2 §1.)
6. **B** — The Swiss-cheese model: layered mitigations whose holes don't line up. (Lecture 2 §2.)
7. **B** — Name, quantify, standard-frame, and point to the validation. "No residual risk" is the flinch. (Lecture 2 §3.)
8. **B** — They're validation evidence; each drill validates a specific mitigation. (Lecture 2 §4.)
9. **B** — A specific un-drilled failure + why it matters + how you'd drill it shows continuous failure-mode thinking. (Lecture 2 §4.)
10. **B** — Catch and correct the false premise; agreeing is a quiet fail, catching scores big. (Lecture 2 §5.3.)
11. **B** — Name your knowledge boundary and how you'd find out; bluffing is the only fatal answer. (Lecture 2 §5.2.)
12. **B** — It shows you learn from your work — the hardest thing for employers to assess. (Lecture 2 §6.)
13. **B** — The full mock against the real rubric finds the gaps while they're cheap. (Lecture 1 §6.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md) — and the defense.
