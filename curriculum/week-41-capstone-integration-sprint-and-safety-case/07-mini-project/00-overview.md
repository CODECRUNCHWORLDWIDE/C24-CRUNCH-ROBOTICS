# Mini-Project — The Capstone Safety Case

> Author the portfolio-quality safety case for your capstone robot: intended use, foreseeable misuse, hazard list, risk assessment, mitigations (software E-stop, hardware E-stop, software watchdog, perception confidence gates), residual risk, and validation plan — framed against ISO 13482 / ISO 10218. **This is the graded Week 41 artifact** (5% of the track) and it becomes the safety appendix of your capstone portfolio.

This is not a writing exercise you do to satisfy a rubric. It is the document a panel reads before they let you defend the capstone, and it is the document an interviewer at a robotics startup will ask to see. We grade it as if a person will stand next to the robot it describes — because in Weeks 42–48, one will (you, on Path A; the simulated public on Path B).

**Estimated time:** ~10 hours, spread across Thursday → Sunday in the suggested schedule. Most of it is *thinking*, not typing. The hazards you find on Saturday afternoon are the whole point.

---

## What you will produce

A single, coherent safety case in your capstone repository under `safety-case/`, assembled from the week's work plus new sections written this weekend. It is *living*: the hazard log and FMEA tables regenerate from YAML (exercise 3), so the document never goes stale.

```
safety-case/
├── README.md                      # the assembled safety case (the deliverable)
├── 01-intended-use-and-misuse.md  # from exercise 1, verbatim
├── 02-hazard-log.md               # GENERATED from safety.yaml (exercise 3)
├── 03-fmea.md                     # GENERATED from safety.yaml (exercise 3)
├── 04-mitigations.md              # the four-layer stack, with independence argument
├── 05-residual-risk.md            # quantified, ALARP, SIGNED
├── 06-validation-plan.md          # each top hazard -> a runnable test
├── safety.yaml                    # the single source of truth for hazards + FMEA
├── gen.sh                         # regenerates 02 and 03 from safety.yaml
├── mitigations/                   # the runnable mitigation code (watchdog, gate, mux)
├── evidence/                      # validation results: bags, plots, logs
├── preflight-checklist.md         # Path A hardware OR Path B sim-production-grade
└── architecture.md                # a Mermaid diagram of the mitigation architecture
```

---

## Path A vs Path B

The *method* is identical; the *content* differs. Pick your path (the same path you carry to Week 48) and instantiate accordingly.

- **Path A (hardware).** Your hazards include real kinetic/potential energy, a real battery, real pinch points, a real arm that can fall. Your pre-flight is the hardware bring-up checklist. Your hardware E-stop is a real contactor you measure. Your validation includes real force/speed measurement.
- **Path B (sim-production-grade).** Your hazards are framed around the *intended* hardware the sim represents (you are arguing about the robot you would deploy), plus the production-software hazards (deadlock, stale data, OOD policy actions). Your pre-flight is the sim-production-grade checklist. Your "hardware E-stop" is documented as the design you would build, and your validation is fault-injection in sim with measured detection/latch behavior.

Path B is **not** an easier path — it trades physical-measurement validation for production-hardening rigor, and a reviewer holds you to the same standard of honest residual risk.

---

## Rules

- **You may** reuse exercise 1 (intended use/misuse), exercise 2 (watchdog + gate code), and exercise 3 (the FMEA tool) directly. That is the design — the week builds the mini-project incrementally.
- **You must** frame the case against the correct standard(s) — ISO 13482, ISO 10218-1/-2, or both, with ISO/TS 15066 if your arm is collaborative — and state which and why in §1.
- **You must** generate the hazard log (`02`) and FMEA (`03`) from `safety.yaml` via `gen.sh`. Hand-edited tables that drift from the YAML are an automatic deduction. The whole point is a living document.
- **You must** end the residual-risk section (`05`) with a real, named acceptance signature on a stated basis with a date and an ALARP judgment. No signature = not done.
- **You must NOT** down-rate severities to make the tables look calmer, and you must NOT omit an obvious hazard (the arm pinches; the base runs over a foot; the lithium battery is a fire source). Reviewers find the hazard you hid.
- Target environment: **ROS2 Jazzy on Ubuntu 24.04**. Code in `mitigations/` must run in that environment.

---

## Acceptance criteria

- [ ] A `safety-case/` directory in your capstone repo with the structure above.
- [ ] **§1 Intended use + misuse:** intended use, ODD (all six axes bounded with numbers), ≥ 3 enforced out-of-scope items, ≥ 8 foreseeable-misuse scenarios each tagged to a hazard ID. The standard chosen (13482 / 10218 / both) is stated *with a reason*.
- [ ] **§2 Hazard log:** ≥ 15 hazards found via the energy-source method, generated from `safety.yaml`. Spans base kinetics, arm kinetics/potential, electrical, thermal, pinch/shear, *and* autonomy-information hazards (misperception, mis-grounded instruction, planner deadlock). Risk rated S×P×E and banded. At least one hazard bands HIGH or INTOLERABLE pre-mitigation (if everything is "low," you didn't rate honestly).
- [ ] **§3 FMEA:** ≥ 12 failure modes across ≥ 6 subsystems, generated from `safety.yaml`, sorted by RPN, dual criticality cutoff applied (RPN ≥ 100 OR severity ≥ 9). The "safety filter fails to engage" row (or your equivalent worst mode) is present and flagged.
- [ ] **§4 Mitigations:** the four-layer stack documented — hardware E-stop, software E-stop, software watchdog, perception confidence gates — each with its independence and its failure mode. The **common-cause** (full computer hang defeats three of four) is named explicitly. The runnable watchdog + gate (exercise 2) live in `mitigations/` and are wired (or, Path B, demonstrated in sim).
- [ ] **§5 Residual risk:** quantified (numbers tied to a standard, e.g. contact ≤ 0.25 m/s, ≤ 25 N vs the ISO/TS 15066 threshold), ALARP argued, and **SIGNED** with the C24 marker line.
- [ ] **§6 Validation plan:** every hazard with a post-mitigation band ≥ Medium, and every critical FMEA row, maps to a concrete test with a measured pass criterion. At least 3 of these tests are actually *run* with results in `evidence/`.
- [ ] **Pre-flight checklist:** the path-appropriate checklist, filled and green for at least one real run (Path A) or one cold-boot session (Path B).
- [ ] **`architecture.md`:** a Mermaid diagram showing the four mitigation layers, what each protects against, and the common-cause boundary.
- [ ] `gen.sh` regenerates `02` and `03` cleanly; the exercise-3 `--selftest` passes on your tool.

---

## Suggested order of operations

Build it in the same order the week taught it. Do not try to write the whole thing Sunday night.

### Phase 1 — Framing and bounding (~1.5h, Thursday)

1. Decide your standard (13482 / 10218 / both) and write one paragraph justifying it against your robot type.
2. Drop in `01-intended-use-and-misuse.md` from exercise 1. Re-read it cold — is the ODD specific enough that your real demo lives inside it? Tighten or widen honestly.
3. List your assumptions and dependencies (what the claim rests on that you don't control).

### Phase 2 — The hazard log (~2h, Friday)

1. Walk the **energy sources** of your robot (base kinetic, arm kinetic + potential, stored mechanical, electrical/battery, thermal, pinch/shear, information). For each, enumerate hazards. Aim for breadth before depth — get to 15+ rows.
2. Cross-reference your misuse scenarios: every `→ HZ-NN` tag from exercise 1 must have a real row now.
3. Write each row into `safety.yaml` (hazards section). Rate S/P/E honestly. Run the exercise-3 tool: `python3 exercise-03-hazard-log-fmea.py safety.yaml`. Confirm at least one row bands HIGH or INTOLERABLE — if not, you under-rated.

### Phase 3 — The FMEA (~2h, Friday/Saturday)

1. For each subsystem (perception, localization, planning, control, policy, safety filter, compute, power, network, MCU), enumerate failure modes into `safety.yaml` (fmea section). At least 12 rows, 6+ subsystems.
2. Score S/O/D. Remember Detection is inverted (10 = undetectable). Find your worst mode (highest severity).
3. Generate `03-fmea.md`. Confirm the critical flags land where you expect. Cross-reference: high-RPN rows whose effect is person-harm should map to a hazard-log row.

### Phase 4 — Mitigations and architecture (~2h, Saturday)

1. Document the four layers in `04-mitigations.md`. For each: what it is, what it protects against, its independence, its failure mode.
2. Wire the exercise-2 watchdog + confidence gate into `mitigations/`. Path A: demonstrate the watchdog latches on a killed sensor. Path B: demonstrate it in sim with fault injection.
3. Lay the four layers against their common causes (the table from Lecture 2 §5). Name the full-computer-hang common cause explicitly. Draw the Mermaid diagram in `architecture.md`.

### Phase 5 — Residual risk and validation (~2h, Saturday/Sunday)

1. For your top hazards, state the residual risk quantitatively. Compute at least one number against a standard (e.g. the ISO/TS 15066 force threshold for the body region your arm can contact).
2. Argue ALARP: what further mitigation did you consider, and why is the remainder reasonably practicable?
3. Write the signature line. If *you* are the accepting authority, sign it — and mean it.
4. Build `06-validation-plan.md`: each ≥ Medium hazard → a test with a measured pass criterion. Run at least 3; put results in `evidence/`.

### Phase 6 — Pre-flight + polish (~0.5h, Sunday)

1. Fill the path-appropriate pre-flight checklist; run it once for real; mark it green.
2. Assemble `safety-case/README.md` that links all sections in order and states the top-level claim.
3. Peer review: trade with a cohort member. They look for the hidden hazard, the software-only "defense in depth," the unsigned residual. Fix what they find.

---

## A worked fragment of the assembled case

The top of your `safety-case/README.md` should read like a real safety case opens — claim first:

```markdown
# CrunchBot-41 — Safety Case

## Claim
CrunchBot-41 is acceptably safe to operate autonomously within its stated ODD
(indoor, flat finished floor, ≤ 0.5 m/s, shared with untrained adults and
supervised children), framed against ISO 13482 (mobile servant robot) for the
base and ISO 10218-2 + ISO/TS 15066 for the arm. "Acceptably safe" means every
hazard with a post-mitigation rating of Medium or above has been reduced ALARP
and the residual risk has been accepted by a named authority (§5).

## Argument (at a glance)
Intended use (§1) bounds the claim. The hazard log (§2, energy-source method)
and FMEA (§3) enumerate the ways harm can occur. A four-layer defence-in-depth
stack (§4) reduces each. Residual risk (§5) is quantified, ALARP, and signed.
The validation plan (§6) provides the evidence for each top hazard.

## Top-level risk picture
- Hazards identified: 17 (4 HIGH/INTOLERABLE pre-mitigation, 0 above Medium post-mitigation)
- FMEA failure modes: 14 (3 critical: safety-filter-non-engage, EKF divergence, brake-on-power-loss)
- Worst credible residual harm: low-speed contact ≤ 0.25 m/s, ≤ 25 N forearm (below 15066 threshold)
```

And the bottom of `05-residual-risk.md` must carry the marker:

```
Residual risk: ACCEPTED by <your name> on 2026-06-14
  basis: validation plan §6 — all post-mitigation Medium+ hazards tested and passed;
         worst credible contact ≤ 0.25 m/s, ≤ 25 N forearm, below ISO/TS 15066 quasi-static threshold
  ALARP: yes — full enclosure considered and judged disproportionate for an indoor assistive use
  conditions: ODD enforced via geofence + payload check; HW E-stop verified each pre-flight; quarterly re-validation
```

---

## Rubric

| Criterion | Weight | What "great" looks like |
|-----------|-------:|-------------------------|
| Framing & intended use | 15% | Correct standard chosen *and justified*; ODD bounds every axis with numbers; misuse section designs for real humans, hides nothing |
| Hazard log | 20% | ≥ 15 hazards from the energy-source walk including the autonomy-information ones; honest, consistent S/P/E; generated from YAML |
| FMEA | 20% | ≥ 12 modes, ≥ 6 subsystems, correct RPN + dual cutoff; cross-referenced to the hazard log; the worst mode is present and not hidden |
| Mitigations & independence | 20% | Four layers documented with failure modes; the common-cause (computer hang) named honestly; watchdog + gate runnable and wired |
| Residual risk | 15% | Quantified against a standard; ALARP argued; **signed** on a stated basis. The single most-weighted honesty test in the week |
| Validation & polish | 10% | Each top hazard → a reproducible test; ≥ 3 run with evidence; pre-flight green; architecture diagram present; living document regenerates |

A safety case that is beautifully formatted but ends without a signed residual-risk line, or whose hazard log omits the obvious arm-pinch hazard, fails the honesty test regardless of polish. We would rather grade an ugly, honest case than a pretty, dishonest one.

---

## What this prepares you for

- **Week 42 (Build Sprint 1)** — your pre-flight checklist gates the first integration day; your hazard log tells you what to watch for when the robot moves for real.
- **Week 46 (Chaos drill)** — the two intentional failures (sensor dropout mid-task, planner deadlock at a doorway) are *already in your FMEA and hazard log*. Your watchdog and confidence gate are what survive the drill. You are pre-writing your own gameday.
- **Week 47 (Portfolio polish)** — this safety case becomes the safety appendix; the architecture diagram becomes part of your capstone's Mermaid diagram set.
- **Week 48 (Capstone defense)** — the panel *reads this document* and asks live questions. Every weak sentence you leave in today is a question you cannot answer in June. Write it now so you can defend it then.

---

## Submission

When done:

1. Push your capstone repo with the `safety-case/` directory public.
2. Confirm `gen.sh` regenerates `02-hazard-log.md` and `03-fmea.md` from `safety.yaml` on a fresh clone, and that the exercise-3 tool's `--selftest` passes.
3. Confirm `05-residual-risk.md` ends with a signed residual-risk marker line.
4. Confirm `preflight-checklist.md` is filled and green for at least one run.
5. Post the repo URL in your cohort tracker, and tag a peer for the honesty review. You wrote the document that says a person can stand next to your robot. Make sure it's true.
