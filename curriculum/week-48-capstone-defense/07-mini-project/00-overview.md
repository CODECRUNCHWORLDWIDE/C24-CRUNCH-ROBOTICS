# Mini-Project — The Complete Defense Package, the Mock Defense, and the Public Retro

> **Phase 6 / Week 48 — the final deliverable of C24.** This mini-project is the capstone defense itself: the assembled package, the safety case document, the slide deck, the live-demo plan with fallbacks, the mock-then-real defense, and the public retro that closes the year. When the panel signs the rubric off the back of this work, you are a Crunch Robotics graduate.

## What you're building

The complete, defense-ready capstone — not new robot capability, but the *assembly, presentation, and defense* of everything you built. By the end you will have:

1. The **complete defense package** — the seven required deliverables (integrated repo with top-level README, Mermaid architecture diagram, two videos, signed safety case, two chaos-drill postmortems, operator-dashboard recording, polished portfolio) plus the public retro, all committed and navigable (Part 1).
2. The **defense slide deck** — the ~18-slide spine that carries the ninety minutes, structured so the panel can follow the argument and so you never improvise the parts that matter (Part 2).
3. The **safety case document, presentation-ready** — the Week 41 artifact finalized into a structured argument (CAE/GSN spine), with the hazard log, FMEA, layered mitigations, validation evidence, and a quantified, accepted residual-risk register (Part 3).
4. The **measured acceptance-criteria table** — your robot mapped against the spec, every number evidenced, every gap honest (Part 4).
5. The **live-demo plan with fallbacks** — the rehearsed demo, the fallback ladder, and the cold-boot run, planned so a hung terminal never becomes a death spiral (Part 5).
6. The **mock defense debrief** — the full ninety-minute mock run against the real rubric, scored, with its gaps closed (the challenge, folded in here as Part 6).
7. The **public retro** — the honest one-page "what I'd do differently" (Lecture 2 §12, Part 7).
8. The **real defense** — presented to the panel, who sign the rubric (Part 8).

The deliverable is the thing that goes at the top of your résumé and wins your second-round interviews: a public, defended, integrated mobile manipulator with a signed safety case and two chaos-drill postmortems.

## Why this is the mini-project

There is no "more code" alternative this week, because the work of the final week is not building — it is *proving*. You have a robot; the question the panel answers is whether they would trust you on it near people. That trust is assembled from the package (the evidence), the slide deck (the legibility), the safety case (the maturity), the acceptance table (the honesty), and the defense (the understanding). This mini-project is all of them, and like every capstone-era deliverable its value is in how honestly you do it. A defense package with a hidden gap is a package the panel finds the gap in; a defense rehearsed against a soft mock is a defense that meets its first hard question live. Do it for real.

## Honoring the compounding chain

This is the whole chain, assembled and defended:

- **Weeks 1–16** are the foundation and perception — the first flagship project and the substrate of the stack.
- **Weeks 17–32** are planning, control, manipulation, and the learned policy — the second flagship project and the heart of the capstone.
- **Weeks 33–40** are sim2real, multi-robot, VLA, and the **Week 39 edge optimization** that makes the graph fit the robot.
- **Week 41** is the safety case you now present. **Week 43** is the dashboard you now record. **Week 44** is the eval suite behind your 17/20. **Week 46** is the two postmortems you now present as validation evidence. **Week 47** is the portfolio and the pitch you now open with.

Every segment of the defense reaches into a different part of the year. The defense is the moment all forty-seven prior weeks become one coherent argument: *I can architect, ship, and operate this robot, safely, and prove it.*

---

## Part 1 — Assemble and audit the package

Run Exercise 1's checklist. Assemble the seven deliverables + retro into the integrated repo with a top-level README that routes a reader to each. Fix every gap the audit finds, prioritizing any missing safety deliverable above polish.

The repository map the README must contain (Lecture 1 §3):

```markdown
## Repository map
| What | Where |
|------|-------|
| Autonomy stack (perception → policy) | `src/crunchbot_*/` |
| Architecture diagram | `docs/architecture.md` (+ `.png`) |
| Safety case (signed) | `docs/safety-case.pdf` |
| Latency report | `docs/latency-report.md` |
| Chaos-drill postmortems | `docs/postmortems/` |
| Videos (sim + real) | `docs/videos/` |
| Operator-dashboard recording | `docs/dashboard-demo.mp4` |
| Portfolio (3 projects) | `portfolio.md` |
| Public retro | `RETRO.md` |
| Defense deck | `docs/defense-deck.pdf` |
```

**Acceptance:** all seven deliverables + retro committed and navigable; the README routes a stranger to each in under a minute; the PNG diagram export exists; videos are labelled unambiguously; the repo is public, GPL-3.0, and tagged `v1.0-defense`.

---

## Part 2 — The defense slide deck

The deck carries the ninety minutes. Its job is not decoration — it is to keep the *argument* legible and to make sure the high-stakes segments (safety case, acceptance table) are presented in a fixed order you never improvise. Build it to the structure below, one idea per slide, readable from across a room.

### The slide spine (~18 slides for the 65 minutes you control)

| # | Slide | What's on it |
|---:|-------|--------------|
| 1 | **Title** | Robot name, one-line what-it-does, your name, the `v1.0-defense` tag, the date. |
| 2 | **The pitch** | Problem → stack → one hard decision → one failure survived → quantified result. Your rehearsed five-minute opener. |
| 3 | **Acceptance scorecard** | The marker block up front: instructions, drift, cold-boot, chaos drills, safety-case status. Frames the honesty narrative immediately. |
| 4 | **Architecture diagram** | The Mermaid stack — sensors → perception → estimation → planning → control → policy → safety — readable, safety layer drawn in. |
| 5–6 | **Stack walkthrough** | Two slides max; name every layer, explain the two or three you most want probed. |
| 7 | **Videos** | The sim and real (or sim-hardened) runs, labelled, with a "watch for X" caption. |
| 8 | **Acceptance-criteria table** | The full evidenced table (Part 4). One row per criterion, measured number, evidence link, status. |
| 9 | **Safety thesis** | "Safety does not depend on the smart parts." One slide, one sentence, the architecture picture under it. |
| 10 | **Safety argument (CAE/GSN)** | The claim tree: top claim → sub-claims by hazard → evidence. The structure the panel audits. |
| 11 | **Hazard log + FMEA highlights** | The top hazards by severity×likelihood, each with its mitigation. Not every row — the load-bearing ones. |
| 12 | **The layered mitigations** | The Swiss-cheese diagram with the independence/fault-domains annotated. |
| 13 | **Residual-risk register** | The quantified, standard-framed, signed residuals. The honest remainder. |
| 14–15 | **Chaos drills** | One slide each: the hazard it validates, the timeline from the bag, the gap it surfaced and closed. |
| 16 | **System properties** | The eight one-liners (perception, planning, control, policy, safety, telemetry, fleet, OTA), each evidenced. |
| 17 | **Honest gaps + roadmap** | Where the robot falls short, the analysis, and the "another month" next steps. Read as ownership. |
| 18 | **Close** | The thesis restated, the `v1.0-defense` repo link, "questions." Hands the floor to the 25-minute Q&A. |

### Deck discipline

- **One idea per slide.** A slide the panel has to *read* is a slide that competes with you talking. Bullets are pointers, not paragraphs.
- **The safety slides (9–13) are the spine you rehearse hardest** — they're where trust is earned and where you must not improvise the order.
- **No slide is load-bearing for a number** — every number on a slide also lives in the repo with a citation, because the panel may ask "show me." The deck points at evidence; it is not the evidence.
- **Export to PDF and commit it** (`docs/defense-deck.pdf`) so it renders on the defense machine and survives a presentation-software failure.

**Acceptance:** the deck exists, follows the spine, is committed as a PDF, and the safety slides present the CAE/GSN argument, not a flat list. Each number on a slide traces to a repo artifact.

---

## Part 3 — The safety case document, presentation-ready

Finalize the Week 41 safety case into the artifact the panel scrutinizes most (Lecture 2 §1–4). It is a structured *argument*, not a document dump, and it must be signed by your peer reviewer before the defense.

### The required structure

1. **Intended use + the ODD.** What the robot is for, the conditions it's rated for, and — explicitly — what's outside the operating design domain.
2. **Foreseeable misuse.** The reasonably-foreseeable ways it's misused or surprised (ISO 12100 framing).
3. **Hazard log.** Every identified hazard, each with a stable ID, severity, and likelihood.
4. **FMEA.** Per failure mode: cause, effect, severity, likelihood, detectability, mitigation. The table the panel reads most carefully.
5. **The argument spine (CAE or GSN).** The top claim ("acceptably safe in the ODD") decomposed by hazard into sub-claims, each grounded in evidence. Name the **context** (the ODD, the standard, the definition of "acceptable") and the **assumptions** the argument rests on (e.g., "the hardware E-stop meets its rated cutoff").
6. **Layered mitigations.** Software E-stop (200 ms latch), velocity/workspace clamps, perception-confidence gates, classical fallback, hardware E-stop — each mapped to the hazard(s) it covers, with the **fault-domain independence** stated (which layers share a substrate, which don't).
7. **Validation plan + evidence.** How each mitigation was tested, with bagged, dated, citable evidence — including the two chaos drills as validation of the degraded-mode and recovery mitigations.
8. **Residual-risk register.** Each residual named, quantified, framed against a standard (ISO 13482 / ISO/TS 15066 contact limits), and **accepted by a named person on a date** (you + your peer reviewer).

### The quality bars

- **Non-empty residual section.** A safety case claiming zero residual risk reads as one that didn't think hard enough. Every residual is named, quantified, and accepted (Lecture 2 §4).
- **Bidirectional hazard↔mitigation mapping.** Every hazard has a mitigation; every mitigation maps back to its hazard(s). No orphans on either side.
- **No unaddressed safety-relevant defect.** The one unforgivable failure: a real defect parked unmitigated. If the audit or the mock finds one, fixing it is the highest-priority work this week, ahead of all polish.
- **Signed.** Peer reviewer signs before the defense; the panel signs live.

**Acceptance:** the safety case is committed (`docs/safety-case.pdf`), peer-signed, has the CAE/GSN argument spine with named context and assumptions, a complete bidirectional hazard↔mitigation map, a non-empty quantified residual register, and no unaddressed safety-relevant defect.

---

## Part 4 — Map and verify the acceptance criteria

Run Exercise 2 with your real measured numbers. Build the honest acceptance-criteria table with evidence links. If any criterion fails — especially a safety-relevant defect — that fix is your highest priority this week.

The table the panel reads in the first minute (Lecture 1 §4):

| Criterion (from the spec) | Bar | Your measured result | Evidence | Status |
|---|---|---|---|---|
| Language-conditioned instructions | ≥ 15/20 | 17/20 | Week 44 eval bag + per-instruction table | PASS |
| Fused-estimate drift | < 0.5 m / 20 m | 0.38 m | `/odometry/filtered` vs ground truth, bagged | PASS |
| Cold-boot to operational | < 60 s | 52 s | timed launch, logged | PASS |
| Two chaos drills recovered | both, operator-detectable, < 60 s | 2/2 | Week 46 postmortems + dashboard recording | PASS |
| Safety case signed | peer + panel | peer-signed; panel pending | the safety-case PDF | PASS (pending panel) |
| No unaddressed safety-relevant defect | none | none | the hazard log | PASS |

Every number is measured and evidenced; you present it yourself rather than waiting to be asked; a partial miss gets a structured honest answer (state the number, characterize the gap, show the analysis, state the fix), never a fudge.

**Acceptance:** the table is in the repo with measured, evidenced numbers; every status is honest; no unaddressed safety-relevant defect.

---

## Part 5 — The live-demo plan with fallbacks

Write `docs/demo-plan.md` and rehearse it. The live demo is the highest-variance part of the defense; manage it like an engineer (Lecture 2 §7).

### The plan must specify

- **The headline demo** — the *most reliable* thing you do, not the most impressive. Never demo live what you can only do sometimes. If you demo one thing, consider making it a chaos drill (kill the LiDAR, watch the robot safe-abort) — a safe failure is the thesis made visible and the most convincing thirty seconds in the defense.
- **The fallback ladder** — from best to worst, with the threshold for dropping to each rung:

```text
Rung 1 (best):  Live on the real robot / live in sim on the defense machine.
Rung 2:         Live run hangs > 30 s → recorded run of the SAME task.
Rung 3:         Recording won't play on the setup → screen-share the bag replay.
Rung 4 (floor): Total AV failure → walk the diagram + the per-instruction table;
                the numbers stand without the video.
```

- **The cold-boot run** — the one command that takes the robot power-off to operational in < 60 s, ready to run live because the panel may ask. Tested on the *actual defense machine* the day before.
- **The logistics checklist** — every video/bag plays on the presentation setup; the repo is public and the README renders; the package is backed up on a second machine; the E-stop is reachable and tested if you demo the real robot near people.

**Acceptance:** `docs/demo-plan.md` specifies the headline demo, the four-rung fallback ladder with thresholds, the tested cold-boot command, and the logistics checklist; the cold-boot has been run on the defense machine; a recorded fallback exists for every live element.

---

## Part 6 — The mock defense and the gap-closing sprint

Run the full ninety-minute mock (the challenge) against the real rubric with a mock panel. Capture the debrief, the two weakest segments, and the gap list. Close the gaps before the real defense.

Treat the mock as the real thing — a sandbagged mock (easy panel, softball questions) teaches you nothing and sets you up to find the gaps live. The mock reliably surfaces: an overrun (the walkthrough ate the Q&A), an unevidenced number, a hand-waved safety hazard, a weak three-layer defense, and a bluff at the edge. Each is cheap to fix Thursday and expensive to discover live.

**Acceptance:** the mock ran on the clock; the debrief has rubric scores and a dated gap-closing plan; the gaps are closed (or honestly carried with a plan, for non-safety items); any safety-relevant gap is closed, not carried.

---

## Part 7 — The public retro

Write the one-page `RETRO.md`: specific, technical regrets with transferable lessons, plus what you'd keep and why (Lecture 2 §12). Include the safety-process regret — the line a robotics employer reads closest (e.g., "I treated the safety case as a Week-41 deliverable instead of a Week-1 design constraint"). Commit it publicly.

**Acceptance:** real, specific regrets (not platitudes); each ends in a transferable principle; one safety-process reflection; one decision you're proud of and why it held.

---

## Part 8 — The real defense

Present the ninety-minute defense to the panel. They sign the rubric.

**Acceptance:** the panel signs the rubric; the marker block (below) is filled with the live-graded numbers and the signature date.

---

## Grading rubric (100 points)

| Component | Points | Full marks |
|---|---:|---|
| Complete defense package | 14 | All seven deliverables + retro + deck, committed, navigable from a top-level README |
| Defense slide deck | 8 | Follows the spine; safety slides present the CAE/GSN argument; committed as PDF |
| Safety-case document | 12 | CAE/GSN spine with context + assumptions; bidirectional hazard↔mitigation map; quantified, signed residual register |
| Acceptance-criteria mapping | 16 | Honest, measured, evidenced table; no unaddressed safety-relevant defect |
| Live-demo plan | 6 | Headline demo + four-rung fallback ladder + tested cold-boot + logistics checklist |
| Mock defense + gap closing | 14 | Full ninety-minute mock run; debrief; gaps closed before the real defense |
| Safety-case presentation | 12 | "Doesn't depend on the smart parts" thesis; Swiss-cheese + independence answer; quantified residual risk |
| Live Q&A (real defense) | 16 | Three-layer "why" across the stack; knowledge-edge honesty; caught false premise |
| Public retro | 12 | Specific technical regrets incl. safety-process; transferable lessons; what you'd keep and why |

**Pass threshold (this mini-project): 75/100.** The *capstone itself* passes per the spec's acceptance criteria, live-graded by the panel — that is the binding gate. Note the weighting: the live Q&A (16) and the acceptance mapping (16) carry the most, because the Q&A is where the panel decides whether you understand your robot and the mapping is where you prove it works. A package that hides a gap, or a Q&A where you bluff past your knowledge edge, fails those components regardless of the rest.

## The marker block

```text
Capstone acceptance (live-graded):
  Instructions:  17/20      (≥ 15 required)            → PASS
  Drift:         0.38 m / 20 m  (< 0.5 m required)     → PASS
  Cold-boot:     52 s       (< 60 s required)          → PASS
  Chaos drills:  2/2 recovered, operator-detectable    → PASS
  Safety case:   signed by peer reviewer + panel        → PASS
  --> DEFENSE PASSED. Panel signed 2026-XX-XX.
```

## Final deliverable structure

```text
capstone-repo/
├── README.md                  ← what-and-why, diagram, repo map, acceptance table, cold-boot quickstart
├── RETRO.md                   ← the public one-page retro
├── portfolio.md               ← three projects, one progression
├── src/crunchbot_*/           ← the autonomy stack
└── docs/
    ├── architecture.md (+.png) ← the Mermaid stack diagram + export
    ├── defense-deck.pdf        ← the ~18-slide spine (Part 2)
    ├── safety-case.pdf         ← signed; CAE/GSN argument, FMEA, residual register (Part 3)
    ├── acceptance-table.md     ← the measured, evidenced criteria table (Part 4)
    ├── demo-plan.md            ← headline demo + fallback ladder + cold-boot + logistics (Part 5)
    ├── mock-debrief.md         ← rubric scores + dated gap-closing plan (Part 6)
    ├── latency-report.md       ← the Week 39 proof the graph fits the robot
    ├── postmortems/            ← the two chaos-drill postmortems
    ├── videos/                 ← the two labelled runs
    └── dashboard-demo.mp4      ← the operator-dashboard recording
```

## A note on honesty

The defense rewards the engineer who knows exactly where their robot stands — including where it falls short — over the one who hides a gap. A 14/20 with a clear failure analysis beats a fudged 15 the panel reruns. A residual risk you've quantified beats "nothing bad can happen." A knowledge edge you name beats a bluff. And the one unforgivable failure is a safety-relevant defect unaddressed in the safety case — that fails the capstone regardless of how well the robot demos, so if you find one this week, fixing it is the only thing that matters until it's fixed. Surface every gap. Then defend the robot you actually built, honestly, and let the work speak.

## Stretch goals

- **Run the mock twice** with two panels; the delta in what each finds is your true readiness.
- **The "another month" roadmap** — a two-minute honest next-steps slide (slide 17); panels read it as ownership.
- **Defend your weakest part on purpose** — invite the attack; surviving it is more convincing than a tour of your strongest.
- **Demo a safe failure live** — trigger the sensor-dropout drill in front of the panel and let them watch the robot detect, alert, and safe-abort. The thesis, made visible.
- **Write the retro as advice to a week-1 learner** — teaching is the deepest proof of understanding, and a strong final coda for the portfolio.

---

*This is the end of C24 · Crunch Robotics. When the panel signs, you are a graduate. Go build robots that make the world more capable and a lot safer.*
