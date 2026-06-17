# Week 47 — Mock Interview + Portfolio Polish

Welcome to Week 47. You are one week from the capstone defense, and this week has one job: make sure that when you walk into a robotics-startup interview loop — or the Week 48 panel — you can *prove*, across a table and on a screen, everything you spent forty-six weeks building. Week 45 was the ramp; this is the full loop. A senior reviewer runs you through the complete robotics-startup interview, end to end, and then you polish the three portfolio projects that are, between them, the artifact a recruiter sees first.

Here is the truth nobody tells you until they have sat on the hiring side. Two candidates with identical capstones get wildly different outcomes, and the difference is almost never the robot. It is whether the candidate can tell the story — clearly, honestly, under follow-up pressure — and whether the portfolio loads in thirty seconds and makes the reviewer *want* to read more. A brilliant robot with a broken README and a rambling pitch loses to a solid robot with a crisp three-minute video and a candidate who can defend every design decision three layers deep. This week closes that gap.

You will do two things in parallel:

- **The full-loop mock.** A senior-engineer reviewer runs the complete loop: recruiter-style intro, a technical deep-dive, a system-design round, the "tell me about your capstone" behavioral, and the founder/culture close. You get scored against a rubric and a written debrief.
- **Portfolio polish.** Your three flagship projects — the Week 16 perception cycle, the Week 32 learned-policy-plus-fallback stack, and the Week 48 capstone — each get a polished README, a Mermaid architecture diagram, and a sub-three-minute walkthrough video. These are what a recruiter opens before they ever talk to you.

By Friday you will have survived the loop, fixed the holes it exposed, and have three portfolio pieces that look like the work of an engineer a company wants to hire.

## Learning objectives

By the end of this week, you will be able to:

- **Run** a complete robotics-startup interview loop as the candidate — intro, technical deep-dive, system design, behavioral/portfolio, culture close — managing your energy and the clock across all five rounds without fading.
- **Tell** the "tell me about your capstone" story in under five minutes: the problem, the stack, one hard decision you defend, one failure you survived (the chaos drill), and the result — a quantified one.
- **Defend** any design decision in your stack through three layers of "why" without collapsing into "it's what the tutorial used," connecting at least one layer to a measured artifact (a latency number, an eval-suite result, a chaos-drill postmortem).
- **Polish a portfolio README** to the senior bar: a one-paragraph what-and-why at the top, a Mermaid architecture diagram, a quickstart that actually runs, results with numbers, and an honest limitations section.
- **Produce** a sub-three-minute project walkthrough video with a script, a screen recording, and a voiceover that a busy reviewer can watch at 1.5x and still follow.
- **Draw** a clean Mermaid architecture diagram of an autonomy stack — nodes, topics, the data flow, the safety layer — that reads correctly to someone who has never seen your code.
- **Self-assess** honestly against an interview rubric, identify the two weakest rounds, and convert them into a focused fix before the Week 48 defense.
- **Connect** the whole portfolio into one coherent story — perception → learned policy → integrated capstone — that demonstrates a progression, not three unrelated demos.

## Prerequisites

This week assumes you have completed Weeks 1–46 of C24, and specifically that:

- You did the **Week 45 interview ramp** — you have two graded mocks behind you, a study plan, and your weakest topics identified. This week is the full loop those rehearsed for; arrive with the study plan executed.
- You **survived Week 46 gameday** — you have two chaos-drill postmortems. The "tell me about a time your robot failed" question is answered by these; have them ready.
- You have your **three flagship projects** in a state that runs: the Week 16 perception cycle (with the Week 39 latency profiling), the Week 32 learned-policy + classical-fallback stack, and the capstone (in whatever state Weeks 41–46 left it).
- You have a **senior reviewer or instructor** willing to run the full loop. Solo-path learners: the mini-project explains how to self-run the loop with a recording and a structured self-debrief — but find a human if you possibly can; the pressure is the point.
- You have the **Week 43 telemetry numbers** and the **Week 44 eval-suite results** — these are the quantified results your stories cite. "p95 is 28 ms, here's the panel" beats "it was fast."

You do **not** need new code this week. Everything is the work you already have, made legible and defensible. The new tools are a screen recorder, a script, and a reviewer with a rubric.

## Topics covered

- The anatomy of the full robotics-startup loop in 2026: intro → technical deep-dive → system design → behavioral/portfolio → founder/culture. What each round is really testing and how to win it.
- The five-minute capstone pitch: structure (problem → stack → one hard decision → one failure survived → quantified result), pacing, and the opening line that earns the next four minutes.
- Three-layer "why" defense, applied across the *whole* stack (not one decision as in Week 45) — and graceful failure when you hit the genuine edge of your knowledge.
- The portfolio README at the senior bar: the what-and-why paragraph, the architecture diagram, the runnable quickstart, results-with-numbers, honest limitations, and why each matters to a reviewer.
- Mermaid architecture diagrams for autonomy stacks: nodes, topics, data flow, the safety layer, and how to draw one that reads correctly to a stranger.
- The sub-three-minute walkthrough video: scripting, recording, voiceover, and the "watchable at 1.5x" test.
- Connecting the three projects into one progression story — perception, then learned policy with a safety net, then the integrated robot — so the portfolio reads as a trajectory, not a pile.
- Honest self-assessment against the loop rubric, finding the two weakest rounds, and the focused fix before Week 48.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — the polish time is yours to reallocate toward whichever project or round is weakest.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The full-loop anatomy; the five-minute capstone pitch          |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Portfolio README + Mermaid diagram at the senior bar           |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | The walkthrough video; polish project 1 (perception cycle)     |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     1h       |    0.5h    |     6.5h    |
| Thursday  | The full-loop mock with a senior reviewer + debrief            |    0h    |    1.5h   |     1h     |    0.5h   |   1h     |     1.5h     |    0h      |     6h      |
| Friday    | Fix the weakest rounds; polish projects 2 & 3; defend-the-stack|    0h    |    0h     |     1.5h   |    0.5h   |   1h     |     2h       |    0.5h    |     5.5h    |
| Saturday  | Mini-project: the polished portfolio + the loop debrief        |    0h    |    0h     |     0h     |    0h     |   0h     |     3.5h     |    0h      |     3.5h    |
| Sunday    | Quiz, review, weakest-round fix write-up                       |    0h    |    0h     |     0h     |    1h     |   1h     |     1h       |    0h      |     3h      |
| **Total** |                                                                | **5h**   | **8h**    | **5h**     | **3.5h**  | **6h**   | **9h**       | **1.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Interview-loop, portfolio, README, Mermaid, and video references, current to 2026 |
| [lecture-notes/01-the-full-loop-and-the-five-minute-pitch.md](./02-lecture-notes/01-the-full-loop-and-the-five-minute-pitch.md) | The five-round loop, what each tests, and the five-minute capstone pitch worked end to end |
| [lecture-notes/02-portfolio-polish-readme-diagram-video.md](./02-lecture-notes/02-portfolio-polish-readme-diagram-video.md) | The senior-bar README, the Mermaid architecture diagram, and the sub-three-minute walkthrough video |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of this week's three exercises |
| [exercises/exercise-01-five-minute-pitch.md](./03-exercises/exercise-01-five-minute-pitch.md) | Write, record, and time your five-minute capstone pitch |
| [exercises/exercise-02-readme-scorer.py](./03-exercises/exercise-02-readme-scorer.py) | A runnable README quality scorer that checks your portfolio READMEs against the senior bar |
| [exercises/exercise-03-loop-scorecard.py](./03-exercises/exercise-03-loop-scorecard.py) | Score the full-loop mock across five rounds and rank your two weakest |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of this week's challenge |
| [challenges/challenge-01-full-loop-mock.md](./04-challenges/challenge-01-full-loop-mock.md) | Run the complete five-round loop with a senior reviewer and survive the deep dive |
| [quiz.md](./05-quiz.md) | 13 questions with an answer key |
| [homework.md](./06-homework.md) | Concrete deliverables with a grading rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The polished three-project portfolio + the full-loop debrief |

## The "a stranger can follow it" promise

Every technical week in C24 ended in working code. This week ends in something different: **a stranger — a recruiter, a reviewer, a future you — can open your portfolio and a busy reviewer can follow your pitch.** The marker we use here is not `Build succeeded`. It is this, written at the top of your homework:

```
Loop mock (5 rounds): intro 8/10 · technical 26/30 · system-design 24/30 ·
                      behavioral 17/20 · culture 9/10   → 84/100  (weakest: system-design pacing)
Portfolio: 3 READMEs pass the scorer · 3 Mermaid diagrams · 3 videos all ≤ 3:00
Fix before W48: system-design clock management (rehearse the 7-phase method twice)
```

If you cannot fill in those numbers — a scored loop, three portfolio projects that pass the bar, and a named fix — you are not done. A portfolio that "looks fine to me" and a pitch you've never timed are exactly what fails in the room.

## A note on honesty

The single most common way candidates fail the loop is **overclaiming** — and Week 45 warned you about it, but the full loop tests it harder because the deep-dive is longer. They say "I optimized the perception cycle to 30 ms" and cannot say what they traded in accuracy. They say "the robot recovers from sensor dropout" and cannot say how it *detects* it. The reviewer's entire job is to find the gap between your README's claims and your actual knowledge, and a five-round loop gives them five chances. The defense is not to claim less — it is to make every claim in your portfolio one you can defend to the third layer of "why," with a number. Your chaos-drill postmortems and your latency report are your ammunition; bring them.

## Stretch goals

If you finish the regular work early:

- Record your five-minute pitch and watch it back at **1.5x with the sound off** — watch your hands and your pauses, then with sound on, count your filler words. Both are fixable and brutal on camera.
- Run the **system-design round for a different robot** than your capstone — a hospital delivery bot, a sidewalk rover — and notice which parts of your answer transfer. Interviewers pick the prompt; you don't.
- Have a peer read *only* your portfolio READMEs (no demo, no pitch) and tell you what they think each project does. Where they're wrong is where your README is unclear.
- Time how long your three projects take to **clone-and-run from scratch** on a fresh machine. If the quickstart doesn't work cold, the reviewer who tries it forms an opinion you won't like.

## Up next

**Week 48 — Capstone defense.** The final week. A panel reads your safety case, watches your videos, reviews your chaos-drill postmortems, and asks live questions for ninety minutes. Everything you polished and rehearsed this week is exactly what they will see and probe — the pitch is your opening, the portfolio is what they read, the three-layer defense is what they test. Push your polished portfolio and your loop debrief before you start; Week 48 assumes the portfolio is already defense-ready.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
