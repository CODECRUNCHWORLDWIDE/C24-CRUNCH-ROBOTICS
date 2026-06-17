# Week 47 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 48. Answer key is at the bottom — don't peek.

---

**Q1.** Two candidates have identical capstones but get very different interview outcomes. What most often explains the difference?

- A) The robot's hardware cost.
- B) Whether they can tell the story clearly and defend it honestly under follow-up pressure — communication, not the robot.
- C) The number of GitHub stars.
- D) Which ROS2 distro they used.

---

**Q2.** The technical deep-dive is the round where overclaiming dies. What is the *fatal* move in it?

- A) Hitting the edge of your knowledge.
- B) Bluffing past your knowledge edge with a confident wrong answer instead of saying "I didn't go deeper than X; here's how I'd find out."
- C) Bringing a number to a claim.
- D) Naming a rejected alternative.

---

**Q3.** In the system-design round, what do candidates most commonly fail to reach because they rat-hole earlier?

- A) The introduction.
- B) Failure-mode enumeration and the safety one-liner — they spend all their time on the box diagram.
- C) The clarifying questions.
- D) The compute budget.

---

**Q4.** Which is a *depth* answer (deep-dive) rather than a *breadth* answer?

- A) "The detector is fast."
- B) "The detector is 11.6 ms p95 in INT8, costing 1.4 mAP points; here's the latency report."
- C) "We use perception, planning, and control."
- D) "It works well in our tests."

---

**Q5.** What is the right structure for the five-minute capstone pitch?

- A) Install steps → dependencies → code tour.
- B) Problem → stack → one hard decision → one failure survived → quantified result.
- C) A live demo with no narration.
- D) A list of every library you used.

---

**Q6.** Why include "one failure survived" (your chaos drill) in the five-minute pitch?

- A) To fill time.
- B) It pre-answers the inevitable "tell me about a time it failed" and signals operational maturity, and you control which failure you tell.
- C) Because the rubric forbids talking about successes.
- D) To make the robot sound broken.

---

**Q7.** A reviewer opens your portfolio and spends ninety seconds. What must the *top* of your README do?

- A) List the installation prerequisites.
- B) Answer what-the-project-is and why-it-exists in one paragraph, before any install step.
- C) Show the full dependency tree.
- D) Thank your contributors.

---

**Q8.** What single section most clearly signals a *senior* README?

- A) A long installation guide.
- B) An honest limitations section — juniors hide limitations, seniors document them (and it defuses the interview catch).
- C) A list of badges.
- D) A table of contents.

---

**Q9.** In a Mermaid architecture diagram of an autonomy stack, what do most candidate diagrams omit that you should include?

- A) The sensors.
- B) The safety layer (E-stop, clamps, fallback) drawn as a layer guarding the autonomy.
- C) The arrows.
- D) The title.

---

**Q10.** What is the cardinal rule of the walkthrough video?

- A) Make it as long as needed to cover everything.
- B) Show the result first (in the first ~15 seconds), then how — never two minutes of setup before anything works.
- C) Use no voiceover.
- D) Record it at 0.5x so it's slow enough.

---

**Q11.** Why frame your three flagship projects as a *progression* rather than three separate demos?

- A) It uses less repo space.
- B) A reviewer who sees the trajectory — perception → safely-shipped policy → integrated robot — reads you as an engineer who grew, which is more compelling than three disconnected artifacts.
- C) GitHub requires it.
- D) It's faster to write one README.

---

**Q12.** What is the highest-leverage thirty minutes in the portfolio polish?

- A) Adding more badges.
- B) Cloning each project to a fresh machine and running the quickstart cold — a broken quickstart makes the reviewer close the tab.
- C) Rewriting the license.
- D) Adding a table of contents.

---

**Q13.** Your self-grade on the system-design round is 5 points above your interviewer's. How should you treat that gap?

- A) Trust your own score; you know your work best.
- B) As a finding: you overrated yourself on system design, so that's a round to fix before Week 48 — the panel won't go easy.
- C) Average the two.
- D) Ignore it.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The difference is almost never the robot; it's whether you can tell and defend the story. (Lecture 1 §1.)
2. **B** — Hitting your edge is fine; bluffing past it is the only fatal move. (Lecture 1 §2.)
3. **B** — Candidates rat-hole on the box diagram and never reach failure modes + the safety one-liner. (Lecture 1 §3.)
4. **B** — A number from a real artifact is depth; "fast"/"works well" is breadth. (Lecture 1 §2.)
5. **B** — Problem → stack → one hard decision → one failure survived → quantified result. (Lecture 1 §5.)
6. **B** — It pre-answers the failure question on your terms and signals maturity. (Lecture 1 §5.)
7. **B** — The what-and-why paragraph, before any install step. (Lecture 2 §1.1.)
8. **B** — The limitations section; its presence signals seniority and defuses the catch. (Lecture 2 §1.5.)
9. **B** — The safety layer, drawn as guarding the autonomy. (Lecture 2 §2.2.)
10. **B** — Result first, then how; never bury the working result. (Lecture 2 §3.1.)
11. **B** — The trajectory reads as growth, more compelling than disconnected demos. (Lecture 2 §4.)
12. **B** — Clone-and-run cold; a broken quickstart closes the tab. (Lecture 2 §5.)
13. **B** — Overrating yourself is a finding to fix before Week 48, not a score to trust. (Lecture 1 §2; Exercise 3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
