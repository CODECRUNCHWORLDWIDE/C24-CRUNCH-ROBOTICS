# Week 47 — Resources

Every resource here is **free**. The interview-prep, README, Mermaid, and video references are all public. This week is about communication, not new tooling, so the list is short and curated — read fewer things, more carefully. No paywalled books are linked.

## Required reading (work it into your week)

- **Mermaid — flowchart and architecture diagram syntax** — the in-repo diagram format the syllabus requires; learn `flowchart` and `subgraph`:
  <https://mermaid.js.org/syntax/flowchart.html>
- **GitHub — Mermaid in Markdown** — how the diagram renders directly in your README on GitHub (no image export needed, though the syllabus wants a PNG too):
  <https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams>
- **"Make a README" / standard README structure** — the section order a reviewer expects; you will exceed it, but start from the convention:
  <https://www.makeareadme.com/>
- **The STAR method** — the structure for the behavioral round and the capstone story (Situation, Task, Action, Result):
  <https://en.wikipedia.org/wiki/Situation,_task,_action,_result>
- **Week 45 lecture notes (in this repo)** — the system-design seven-phase method and the EKF-on-the-board material. This week's mock *uses* them; re-read before Thursday:
  `../week-45-capstone-build-sprint-4-and-interview-prep-ramp/lecture-notes/`

## Interview prep (skim, take what's useful)

- **Pramp / interviewing.io (free peer mock interviews)** — practice loops with strangers; the unfamiliar interviewer is closer to the real thing than a friend:
  <https://www.pramp.com/>
- **Tech Interview Handbook — behavioral and system design** — general but well-organized; adapt the system-design framing to robotics:
  <https://www.techinterviewhandbook.org/>
- **Robotics-company engineering blogs** — read one and reverse-engineer the system-design question it implicitly answers. Good 2026 sources include the engineering blogs of warehouse-robotics, AMR, and humanoid companies (search "<company> engineering blog robotics autonomy"):
  Examples to search: Boston Dynamics, Covariant, Physical Intelligence, Skild AI, Figure, Agility Robotics.

## Portfolio and README craft (read the good ones)

- **Awesome READMEs** — a curated list of exemplary project READMEs; study three before you write yours:
  <https://github.com/matiassingers/awesome-readme>
- **The Documentation System (Divio) — the four kinds of docs** — why a README is not a tutorial is not a reference; pick the right register for each section:
  <https://documentation.divio.com/>
- **Nav2 / MoveIt2 / Isaac ROS READMEs** — production robotics-stack READMEs; note how they open with what-and-why and a diagram, not an install dump:
  <https://github.com/ros-navigation/navigation2>

## Video and recording (free tools)

- **OBS Studio (free, cross-platform)** — the standard screen+voice recorder for a walkthrough video:
  <https://obsproject.com/>
- **Asciinema** — if part of your walkthrough is a terminal session, record it as replayable text rather than a heavy video:
  <https://asciinema.org/>
- **Foxglove** — record the dashboard/telemetry segment of your capstone video here; it is also a capstone deliverable.

## On telling the story (the mindset)

- **"How to give a good demo"** — search talks on demoing technical work; the core lesson is "show the result first, then how, never the reverse."
- **Your own Week 46 postmortems and Week 39 latency report** — these *are* your interview ammunition. The numbers in them are what turn "it was fast" into "p95 is 28 ms, here's the panel." Re-read them as source material for your stories.

## Tools you'll use this week

- A **screen recorder** (OBS) and a quiet room.
- A **timer** — for the five-minute pitch and the timed mock rounds. Pacing is graded.
- **Mermaid Live Editor** (<https://mermaid.live/>) — draft the diagram, then paste the source into your README.
- A **senior reviewer** with the loop rubric — the most important "tool" of the week.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **The loop** | The full sequence of interview rounds a company runs: intro, technical, system design, behavioral, culture. |
| **System-design round** | An open-ended "design the autonomy stack for X" whiteboard question; tests breadth and judgment. |
| **Deep-dive** | A round where the interviewer digs into one thing you claimed until they find the edge of your knowledge. |
| **STAR** | Situation, Task, Action, Result — the structure for behavioral answers and the capstone story. |
| **Three-layer why** | Defending a decision through three recursive "why?" follow-ups without a non-answer. |
| **Overclaiming** | Saying you did/understand more than you can defend — the #1 way candidates fail. |
| **What-and-why paragraph** | The opening of a senior README: what the project is and why it exists, before any install steps. |
| **Mermaid** | A text-based diagram syntax that renders in Markdown/GitHub; the required architecture-diagram format. |
| **Quickstart** | The minimal commands to clone and run the project; if it doesn't work cold, the reviewer notices. |
| **Limitations section** | The honest "what this doesn't do / where it fails" — its presence signals a senior engineer. |
| **Walkthrough video** | A ≤ 3-minute screen recording with voiceover that shows the project working. |
| **The progression** | The story that ties the three portfolio projects into one trajectory, not three demos. |

---

*If a link 404s, please open an issue so we can replace it.*
