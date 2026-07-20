# Week 41 — Quiz

Fourteen questions. Take it with your lecture notes closed. Aim for 12/14 before you start the mini-project — this is the conceptual scaffolding you'll lean on all weekend. Answer key at the bottom; don't peek.

---

**Q1.** Which best describes what a safety case *is*?

- A) A folder of compliance PDFs you show an auditor.
- B) A structured, evidence-backed argument that a specific robot is acceptably safe for a specific use in a specific environment.
- C) A guarantee that the robot has zero risk of harm.
- D) The set of unit tests that pass in CI.

---

**Q2.** Your capstone is a mobile manipulator (wheeled base + small arm) operating near untrained people indoors. Which framing is correct?

- A) ISO 13482 only — it's a mobile robot.
- B) ISO 10218-1 only — it has an arm.
- C) Both ISO 13482 (base, near people) and ISO 10218-2 (the arm + its application), with ISO/TS 15066 for arm-contact force limits.
- D) None — ISO standards don't apply to capstones.

---

**Q3.** ISO 12100 mandates a *hierarchy* of risk reduction. What is the correct order, highest priority first?

- A) Warning labels → safeguarding → inherently safe design.
- B) Inherently safe design → safeguarding/protective measures → information for use.
- C) Operator training → E-stop → redesign.
- D) Software E-stop → hardware E-stop → confidence gates.

---

**Q4.** Why does the safety case open with an *intended use / ODD* section?

- A) Because regulators require a title page.
- B) Because every later argument is bounded by what the robot is for and where; an unbounded safety claim cannot be evaluated.
- C) Because it's the easiest section to write.
- D) It doesn't — the hazard log comes first.

---

**Q5.** A junior writes a hazard log where every mitigation column says "E-stop." What's wrong with it?

- A) Nothing — the E-stop is the only mitigation that matters.
- B) It proves the author has one hammer and did not think about each hazard's specific mitigation (a speed gate for impact, a force limit for crush, a confidence gate for misperception).
- C) E-stops are not allowed in safety cases.
- D) It's fine as long as the E-stop is hardware.

---

**Q6.** In the energy-source method for hazard identification, which "energy source" is the autonomy-specific one that classical machine safety underweights?

- A) Kinetic energy of the base.
- B) Electrical energy of the battery.
- C) Information "energy" — a wrong perception, plan, or policy action that *directs* physical energy at a person.
- D) Thermal energy of the motors.

---

**Q7.** In an FMEA, the Detection (D) score is **inverted**. What does a high D (e.g. 10) mean?

- A) The failure is very easy to detect before harm.
- B) The failure is essentially undetectable before harm — which is bad.
- C) Detection is irrelevant to the RPN.
- D) The failure has already been detected.

---

**Q8.** Your FMEA has a row: "Arm brake fails on power loss," with S=9, O=2, D=2 → RPN=36, which is below your RPN cutoff of 100. Should it be flagged critical?

- A) No — RPN 36 is below the cutoff.
- B) Yes — the dual criticality rule flags any row with severity ≥ 9 regardless of RPN; you can't multiply your way out of a near-fatal failure with a low occurrence guess.
- C) Only if it has happened before.
- D) Only on Path A.

---

**Q9.** What is the defining property of a **hardware** E-stop that a software E-stop lacks?

- A) It is faster to press.
- B) It works even if the entire software stack is wedged and the Linux box has kernel-panicked, because it physically removes motor power independent of any topic.
- C) It can stop only the arm, not the base.
- D) It re-arms automatically.

---

**Q10.** You list four mitigations: hardware E-stop, software E-stop, software watchdog, perception confidence gate. A reviewer asks about independence. What's the honest answer?

- A) "All four are fully independent — that's defense in depth."
- B) "Against most failures we have four layers, but a full computer hang defeats three of them at once (a common cause); only the hardware E-stop survives it."
- C) "Independence doesn't matter for software."
- D) "The software watchdog makes the others independent."

---

**Q11.** Why must a software E-stop be **latching** (stay tripped until a deliberate re-arm)?

- A) To use less CPU.
- B) Because a stop that auto-clears the moment the triggering condition passes will chatter the robot on and off, which is worse than no stop; re-arm must be a deliberate human decision.
- C) Because ROS2 requires it.
- D) It shouldn't be latching — auto-recovery is safer.

---

**Q12.** Your watchdog deadline on `/scan` is 200 ms and the base does 0.5 m/s. What number belongs in your safety case?

- A) "The watchdog trips eventually."
- B) "The watchdog trips within 200 ms, during which the base can travel up to 10 cm on stale data — inside the 30 cm inflation radius, so acceptable."
- C) "The LiDAR runs at 10 Hz."
- D) "200 ms is the ROS2 default."

---

**Q13.** A complete residual-risk statement must include all of these EXCEPT:

- A) A quantified remainder, tied to a standard (e.g. ≤ 25 N vs the ISO/TS 15066 threshold).
- B) An ALARP argument.
- C) A named person accepting it on a stated basis and date.
- D) A claim that the residual risk has been reduced to zero.

---

**Q14.** Why is classical FMEA *necessary but not sufficient* for a software-heavy autonomy stack, and what complements it?

- A) FMEA is sufficient; nothing complements it.
- B) FMEA assumes failures are *component* failures, but many autonomy hazards arise when every component works *as specified* in an unintended combination; STPA (control-structure analysis) catches these "everything worked and it still hurt someone" cases.
- C) FMEA is too slow; use a spreadsheet instead.
- D) FMEA only works on hardware; software needs no analysis.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — A safety case is an argument (claim + reasoning + evidence) about a specific robot, specific use, specific place. Not PDFs, not zero-risk, not "tests pass."
2. **C** — A mobile manipulator has the hazards of *both* a mobile base near people (13482) and a manipulator + application (10218-2), plus 15066 for collaborative arm-contact force. You can't pick one half of the machine.
3. **B** — The ISO 12100 hierarchy: inherently safe design first (remove the hazard), then safeguarding, then information for use. "Train the human" is the last resort, never the first.
4. **B** — Intended use / ODD bounds every downstream argument. You can't argue a robot is safe in general — only for a stated use in a stated environment.
5. **B** — All-E-stop means the author didn't think per-hazard. Real mitigations are hazard-specific: speed gate (impact), force limit (crush), confidence gate (misperception), watchdog (silent failure).
6. **C** — Information "energy": a wrong perception/plan/policy action directs the physical energy. This is the category classical machine safety underweights and the one the EU Machinery Regulation 2023/1230 now requires you to address.
7. **B** — Detection is inverted: D=1 means always caught, D=10 means undetectable. High D is bad and drives RPN up.
8. **B** — The dual cutoff: critical if RPN ≥ cut OR severity ≥ 9. A near-fatal failure stays on the watch list regardless of an optimistic occurrence guess.
9. **B** — The hardware E-stop physically removes motor power independent of software, so it works even when the whole stack is dead. That independence is its entire value.
10. **B** — Honest independence: three of the four share the "computer hang" common cause; only the hardware E-stop (and an automatic safety-scanner-triggered contactor) survives it. A case that claims four independent software-ish layers is lying.
11. **B** — A non-latching stop chatters. Latch it; re-arm is a deliberate human decision. Auto-recovery is *not* safer here.
12. **B** — State the distance-on-stale-data and compare it to the inflation radius. A number tied to a consequence is an argument; "trips eventually" is not.
13. **D** — Residual risk is *never* zero. A statement claiming zero residual risk is the failure mode of the section. The other three (quantified, ALARP, signed) are required.
14. **B** — FMEA is component-failure-centric; STPA analyzes the control structure and unsafe interactions, catching hazards where no single component "failed." Use FMEA for components, STPA-style reasoning for perception/planning/policy interactions.

</details>

---

If you scored under 10, re-read the lecture for the questions you missed before starting the mini-project — the case you write this weekend rests on exactly these concepts. If you scored 12+, you're ready for the [homework](./homework.md) and the [mini-project](./mini-project/README.md).
