# Week 48 — Resources

Every resource here is **free**. The safety-standard summaries, the SRE/postmortem material, the Mermaid and presentation references, and your own prior-week artifacts are all open. This is a defense week, not a build week, so the most important "resources" are the artifacts *you already wrote* — re-read them as source material. No paywalled books are linked.

## Required reading (work it into your week)

- **The C24 capstone specification (in this repo's SYLLABUS.md)** — the acceptance criteria and required deliverables you are defending. Read it like a contract; the panel grades against it exactly:
  `../../SYLLABUS.md` (the "Capstone specification" and "Acceptance criteria" sections)
- **The C24 `safety-case-template/`** — the ISO 13482 / ISO 10218 scaffold your Week 41 safety case was built on; re-read the residual-risk-acceptance form before you present:
  `../../safety-case-template/`
- **Google SRE Book — Postmortem Culture** — re-read; the panel will probe your chaos-drill postmortems, and this is the bar they hold them to:
  <https://sre.google/sre-book/postmortem-culture/>
- **Your own prior-week artifacts** — these *are* the defense. Re-read them as the panel will:
  - Week 39 latency report · Week 41 safety case · Week 43 telemetry · Week 44 eval suite · Week 46 postmortems · Week 47 portfolio + pitch.

## Safety standards (read the free summaries)

The standards themselves are paywalled, but the freely available summaries are enough to frame and defend your safety case.

- **ISO 13482 (personal-care robots)** — the framing for a robot operating near people; hazard categories and safety functions:
  <https://en.wikipedia.org/wiki/ISO_13482>
- **ISO 10218 (industrial robots and robot systems)** — the manipulator-safety framing for your arm:
  <https://en.wikipedia.org/wiki/ISO_10218>
- **FMEA (Failure Mode and Effects Analysis) — method overview** — the structure of the FMEA table in your safety case:
  <https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis>
- **The Swiss-cheese model of accident causation** — the mental model behind layered mitigations (no single defense is perfect; the layers catch what the others miss):
  <https://en.wikipedia.org/wiki/Swiss_cheese_model>

## Presenting and defending (the mindset)

- **"How to present technical work to a panel"** — search for thesis-defense and technical-review guidance; the core lesson transfers: state the claim, show the evidence, invite the hard question.
- **The C24 Week 45 + Week 47 lecture notes (in this repo)** — the system-design method, the three-layer "why" defense, and the five-minute pitch. The Q&A this week *is* those drills under the highest stakes:
  `../week-45-capstone-build-sprint-4-and-interview-prep-ramp/lecture-notes/`
  `../week-47-mock-interview-and-portfolio-polish/lecture-notes/`

## Repo, diagram, and video (free tools)

- **Mermaid — flowchart syntax** — the required architecture-diagram format for the integrated repo:
  <https://mermaid.js.org/syntax/flowchart.html>
- **GitHub — repository READMEs and releases** — the integrated repo needs a top-level README and a tagged release for the defense:
  <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>
- **OBS Studio** — for the two videos and the operator-dashboard recording (both capstone deliverables):
  <https://obsproject.com/>
- **Foxglove** — record the operator-dashboard segment here; it is a required deliverable.

## Tools you'll use this week

- A **panel** (instructor + peer reviewer) — the most important resource of the week.
- A **timer** — the defense is 90 minutes; rehearse to fit it.
- The **acceptance-criteria checklist** (Exercise 2) — know where you stand before the panel does.
- **`ros2 bag`** recordings of your eval runs and chaos drills — your evidence is data, not recollection.
- A **clean checkout** of the integrated repo on a fresh machine — the cold-boot-and-run test the panel may ask for.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Defense** | The 90-minute live panel session that decides whether you graduate. |
| **Defense package** | The seven required deliverables: repo, diagram, two videos, safety case, two postmortems, dashboard recording, portfolio. |
| **Acceptance criteria** | The pass/fail bar from the capstone spec (15/20, < 0.5 m drift, < 60 s boot, etc.). |
| **Safety case** | The document arguing the robot is acceptably safe: hazards, FMEA, mitigations, validation, residual risk. |
| **FMEA** | Failure Mode and Effects Analysis — a table of what can fail, the effect, and the mitigation. |
| **Residual risk** | The risk that remains after mitigations; you must state and accept it explicitly. |
| **Hazard log** | The running list of identified hazards and their mitigations. |
| **The retro** | The honest one-page "what I'd do differently," written at the end. |
| **Three-layer why** | Defending a decision through three recursive "why?" follow-ups without a non-answer. |
| **Safety-relevant defect** | A defect that could cause harm; an unaddressed one fails the capstone regardless of demo quality. |
| **Cold-boot** | Bringing the robot from power-off to operational; the spec requires < 60 s. |
| **Fleet heartbeat** | The `/fleet/heartbeat` topic reporting identity/capabilities/health at 1 Hz. |

---

*If a link 404s, please open an issue so we can replace it.*
