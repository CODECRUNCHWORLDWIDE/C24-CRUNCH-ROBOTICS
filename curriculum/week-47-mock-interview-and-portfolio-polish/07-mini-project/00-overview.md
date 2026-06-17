# Mini-Project — The Polished Three-Project Portfolio + the Full-Loop Debrief

> **Phase 6 / Week 47 deliverable.** This mini-project produces the polished portfolio the **Week 48 panel reads first** and the loop debrief that drives your final week of prep. The three flagship projects, made legible, are what a recruiter opens before they ever talk to you — and for many graduates, the artifact that gets the first interview at all.

## What you're building

Not new robot code. A **portfolio a stranger can follow** and the **evidence you can defend it across a table.** Think of it as two parallel tracks all week: the *artifact* track (make the work legible — READMEs, diagrams, videos) and the *performance* track (make yourself able to defend it — the mock, the pitch). They feed each other: polishing a README forces you to articulate what each project does, which is the same articulation the deep-dive demands; running the mock surfaces the questions your READMEs should pre-answer.

By the end you will have:

1. The **three flagship projects** — the Week 16 perception cycle (with Week 39 profiling), the Week 32 learned-policy + classical-fallback stack, and the capstone — each with a senior-bar README, a Mermaid architecture diagram (source + PNG), and a sub-three-minute walkthrough video.
2. A top-level **`portfolio.md`** that states the *progression* — perception → safely-shipped policy → integrated robot — so the three read as one trajectory, not three demos.
3. The **full-loop debrief** — the five-round mock scored by you and a reviewer, the gap, and the two weakest rounds turned into a scheduled fix.
4. Each README **passing the scorer** (Exercise 2) and each video passing the **1.5x test** (Lecture 2 §3).

The deliverable is a portfolio repo (or the `portfolio.md` + three project READMEs in the capstone repo) that a Week 48 reviewer — or a real recruiter — can open and immediately understand what you built, why it's good, and how to run it.

## Why this is the mini-project (and not more robot code)

You have forty-six weeks of robot code. What you do not yet have is *legibility* — the property that a tired stranger, in ninety seconds, can tell what your work is and that it's good. Legibility is the gate: a recruiter screening fifty candidates does not run your robot; they read your README and watch fifteen seconds of video, and that decides whether you advance. Work quality and presentation quality *multiply*, not add (Lecture 2 §5.1) — so this week, spent entirely on presentation, has more leverage on your outcome than another week of robot work would.

This mini-project is the dress rehearsal for being *read* and *heard*, and like the Week 45 mocks, its value is entirely in how seriously you take it. A portfolio that "looks fine to me" is exactly the one that loses, in a recruiter's queue, to a clearer one attached to a weaker robot. The whole point of the week is to make sure your robot — which is genuinely strong — is not the one that loses to a clearer presentation of a weaker one.

## Honoring the compounding chain

This portfolio *is* the chain, made visible:

- **Week 16** is project 1 — the perception cycle. **Week 39** gave it the latency report that turns "it's fast" into "44 ms p95, here's why."
- **Week 32** is project 2 — the learned policy with its safety wrapper and classical fallback. The judgment piece.
- **Weeks 41–46** are project 3 — the capstone, with the **Week 41 safety case**, the **Week 43 dashboard**, the **Week 44 eval suite**, and the **Week 46 postmortems** as its supporting artifacts.
- **Week 45** gave you the interview ramp; this week's loop is the full version, and your **Week 46 postmortems** are the "tell me about a failure" ammunition.

Every README's results section and every pitch should reach into that chain for a *number*. That traceability is what makes the portfolio defensible instead of decorative.

Concretely, the chain populates each artifact:

- Your **latency report (Week 39)** is the results section of project 1's README and the "how do you know it's fast" answer in the deep-dive.
- Your **eval suite (Week 44)** is the results section of project 2 and 3 and the "how good is the policy" answer.
- Your **chaos postmortems (Week 46)** are the "tell me about a failure" answer in the behavioral round and a linked artifact in the capstone README.
- Your **safety case (Week 41)** is the safety section of the capstone README and the "is it safe" answer.

A portfolio assembled from this chain is not a marketing exercise — it is a faithful index of forty-six weeks of real, measured work, made findable. That faithfulness is exactly why it holds up under the deep-dive's probing.

---

## The shape of the deliverable

By the end, your portfolio repo (or the relevant slice of your capstone repo) looks like:

```text
portfolio/
├── portfolio.md                 # the progression: 3 projects, 1 trajectory
├── 01-perception-cycle/
│   ├── README.md                # senior bar, passes the scorer
│   ├── architecture.png         # Mermaid export
│   └── walkthrough.mp4          # <= 3:00, result-first
├── 02-policy-fallback-stack/
│   ├── README.md
│   ├── architecture.png
│   └── walkthrough.mp4
├── 03-capstone/
│   ├── README.md
│   ├── architecture.png
│   └── walkthrough.mp4
├── loop-debrief.md              # the 5-round mock, scored, gap named
└── self-grade.txt               # exercise-03 output
```

A recruiter who lands on `portfolio.md` reads the trajectory in thirty seconds, clicks into the project that matches their company, reads a README that answers their questions in order, and watches a fifteen-second clip that proves it works. That path — landing, orienting, drilling in, believing — is what you are engineering.

## Part 1 — Polish the three READMEs

For each project, write the senior-bar README (Lecture 2 §1): what-and-why paragraph → architecture diagram → quickstart → results-with-numbers → limitations. Run Exercise 2's scorer on each until it passes.

**Acceptance:** all three READMEs score a pass on the scorer; the what-and-why paragraph is before any install step; results cite real numbers from the compounding chain; each has an honest limitations section.

Write each README for the tired stranger (Lecture 2 §1): the what-and-why paragraph at the very top, the diagram next, then quickstart, results-with-numbers, and limitations — in that order, because that is the order the reviewer's questions arrive. The limitations section is the one learners skip and the one that most signals seniority; write a real one for each project, naming what it doesn't do and where it would fail.

For each project, the numbers to pull from the chain:

- **Project 1 (perception cycle):** the 44 ms p95 end-to-end, the per-stage breakdown, the INT8 mAP delta — all from your Week 39 latency report.
- **Project 2 (policy + fallback):** the per-instruction success rate, the intervention rate (how often the classical fallback fired), the eval-set size — from Weeks 29–32 and 44.
- **Project 3 (capstone):** the full acceptance-criteria table (17/20, 0.38 m drift, 52 s boot), the two chaos-drill recovery times — from Weeks 44 and 46.

A README whose results section is "works well" fails the scorer and, more importantly, fails the reviewer. You have the numbers; this is purely a matter of surfacing them.

## Part 2 — Three Mermaid diagrams

Draw a Mermaid architecture diagram for each project (Lecture 2 §2): grouped with subgraphs, data-flow direction shown, the safety layer included. Source in the README (renders on GitHub) plus a PNG export.

**Acceptance:** each diagram reads correctly to a peer who has not seen your code (test it — Lecture 2 §2.2); each includes the safety layer.

The three diagrams differ in scope:

- **Project 1** is a *pipeline* diagram: sensors → fusion/detector → fused-objects output, with the latency budget annotated. The reader should see the data flowing through the cycle.
- **Project 2** is a *control-flow* diagram: observation → policy → safety filter → action, with the classical-fallback branch shown. The reader should see how the learned component is wrapped.
- **Project 3** is a *full-stack* diagram: all layers, with the safety layer guarding the actuators. The reader should see the whole robot.

Each is a map at the right scope for its project — not too detailed (a hairball), not too vague (boxes with no flow). The safety layer appears in all three, because thinking about safety at every scope is exactly the maturity a reviewer is looking for.

## Part 3 — Three walkthrough videos

Record a ≤ 3-minute walkthrough per project (Lecture 2 §3): result first, then the stack over the diagram, then one memorable moment, then results + a limitation. Script it, voice it, pass the 1.5x test.

**Acceptance:** all three videos ≤ 3:00, scripted with voiceover, result shown in the first 15 seconds, followable at 1.5x.

The recording workflow that keeps this from eating your week:

1. **Write the voiceover script first** (~360 words for 3 minutes) and time it by reading aloud. Cut to fit before you record anything.
2. **Capture the screen segments** (OBS): the result clip, the diagram walk, the dashboard/chaos segment, the results card. Close noisy tabs; use a readable font.
3. **Record the voiceover** in a quiet room, re-recording any segment where you stumble. Don't try to nail it in one take.
4. **Assemble and watch at 1.5x.** If it's a blur, cut; if it's followable, ship.

Reuse the capstone video's chaos-drill and dashboard footage where it fits the other projects — you don't need to re-shoot the dashboard three times.

## Part 3.5 — Run the README scorer on each

Before declaring the READMEs done, run `exercises/exercise-02-readme-scorer.py` on each one and fix anything it flags. The scorer checks the senior-bar structure (what-and-why first, diagram, quickstart, numeric results, limitations) so you don't have to guess whether a reviewer would find each section. A README that scores a pass has, demonstrably, the structure that answers a reviewer's questions in order.

**Acceptance:** all three READMEs pass the scorer; the scores are pasted into your debrief or commit message.

## Part 3.6 — Clone-and-run the capstone cold

Before Saturday, clone the capstone repo to a fresh machine (or a clean container) and run the quickstart exactly as written. Fix every break — the missing dependency, the hardcoded path, the undocumented model file, the distro assumption (Lecture 2 §5). This is 30 minutes that prevents the worst possible Week 48 moment: a broken quickstart in front of the panel.

**Acceptance:** `clone-and-run.md` records what broke and what you fixed; the capstone quickstart runs cold on a fresh environment.

## Part 4 — The progression and the debrief

- Write `portfolio.md` stating the three-project progression as one trajectory.
- Run the full-loop mock (the challenge), score it with Exercise 3, and write `loop-debrief.md` with the gap and the two-weakest-rounds fix.

**Acceptance:** `portfolio.md` makes the trajectory explicit; the debrief has both graders' scores, the honest gap, and a scheduled fix before Week 48.

The `loop-debrief.md` should capture, per round: your self-score, the interviewer's score, the gap, and one specific note ("system-design: ran long, never reached failure modes"). Then the two weakest rounds, each with a concrete fix scheduled before Week 48 ("system-design pacing: run the 7-phase method twice on a new prompt, Tue + Wed"). The gap column is the most valuable: a round where you rated yourself well above your interviewer is a blind spot, and naming it is worth more than the score itself. Run `exercise-03` to compute the weighted total and rank the weakest rounds for you.

---

## A note on sequencing

Do this in an order that front-loads the highest-value work:

1. **Run the full-loop mock first** (Thursday), because the debrief tells you which round to spend your remaining prep on. Saving the mock for last wastes its entire diagnostic value.
2. **Polish the capstone README + video next**, because it's what the Week 48 panel reads and a recruiter most wants.
3. **Then projects 1 and 2**, which compound the story.
4. **Then `portfolio.md`** to tie them together.
5. **Clone-and-run the capstone last**, on a fresh machine, so you catch a broken quickstart before Saturday rather than in front of the panel.

The exercises support each step: the pitch-timer (Exercise 1) for the mock prep, the README scorer (Exercise 2) so you don't guess whether each README clears the bar, and the loop scorecard (Exercise 3) so the mock is graded honestly with the interviewer's numbers, not your own optimism.

## Grading rubric (100 points)

| Component | Points | Full marks |
|---|---:|---|
| Three senior-bar READMEs | 24 | All pass the scorer; what-and-why first; numeric results; honest limitations |
| Three Mermaid diagrams | 16 | Grouped, directional, safety layer included; read correctly to a stranger |
| Three walkthrough videos | 20 | ≤ 3:00, result-first, scripted voiceover, pass the 1.5x test |
| The progression (`portfolio.md`) | 12 | Three projects framed as one trajectory, not three demos |
| Full-loop debrief | 22 | Both graders' scores, honest self-vs-interviewer gap, two weakest rounds + scheduled fix |
| Clone-and-run | 6 | At least one project's quickstart verified cold on a fresh machine |

**Pass threshold: 75/100.** Note the weighting: the three READMEs (24) and the loop debrief (22) carry the most, because legibility and an honest self-assessment are the two things that decide whether your forty-six weeks of work gets *seen* and whether you walk into Week 48 prepared. A portfolio with impressive code but a README a reviewer can't parse, or a debrief you inflated, fails those components regardless of the rest.

## How this compounds into Week 48

Nothing here is throwaway. The capstone README and diagram you polish *are* the integrated-repo README and architecture diagram the Week 48 panel requires. The capstone walkthrough video *is* one of the two required videos. The five-minute pitch you rehearse *is* your defense opening line. The loop debrief's weakest-round fix *is* your final-week prep plan. This week is not a detour before the defense — it is the defense's dress rehearsal and the production of half its deliverables. Treat every artifact here as a Week 48 artifact, because that is what it becomes.

## A note on honesty

Two ways this goes wrong, both about honesty. First, a README that overclaims — "real-time 30 ms perception" with no mention of the accuracy you traded — which the deep-dive then exposes. State the limitation; it defuses the catch and signals seniority (Lecture 2 §1.5). Second, a loop debrief you sandbagged in your own favor — rating yourself 5 above your interviewer and calling it a 90. The Week 48 panel will not go easy; a mock you went easy on taught you nothing. Score the loop with the interviewer's numbers, name the round where you overrated yourself, and fix it now while it's cheap.

The throughline of both: the portfolio and the debrief are *instruments*, not trophies. Their job is to find the holes — the unclear README, the weak round, the broken quickstart — while there is still a week to fix them. A learner who uses them honestly arrives at Week 48 with no surprises; a learner who uses them to feel good arrives with the same holes, now in front of a panel. Use them to find the holes. That is the whole point.

## Common failure modes of this mini-project

So you can avoid them:

- **A polished portfolio paired with an inflated debrief.** The artifacts look great but you rated yourself 5 above your interviewer and called the mock a 90. The Week 48 panel won't be as generous; score with the interviewer's numbers (Lecture 1 §2; Exercise 3).
- **A README that overclaims.** "Real-time 30 ms perception" with no mention of the accuracy traded. The deep-dive exposes it. Fix: the limitations section pre-empts the catch (Lecture 2 §1.5).
- **A diagram that's a hairball or missing the safety layer.** Test it on a peer; if they can't read it, the reviewer won't either (Lecture 2 §2.3).
- **A video that buries the result.** Two minutes of setup before anything works; the reviewer bails at 1.5x. Fix: result in the first 15 seconds (Lecture 2 §3.1).
- **A broken cold quickstart.** The single fastest way to lose a reviewer. Fix: clone-and-run on a fresh machine before Saturday (Lecture 2 §5).
- **Three disconnected demos instead of one progression.** The whole is worth less than the parts when you don't connect them. Fix: `portfolio.md` states the trajectory (Lecture 2 §4).

## Stretch goals

- **The cold-reader test:** have a peer read only your three READMEs (no demo) and tell you what each project does. Where they're wrong is where your README is unclear — fix exactly those sentences.
- **The clone-and-run on all three:** time how long each project takes to clone-and-run from scratch on a fresh machine or container. Fix every broken quickstart; a reviewer who hits one closes the tab (Lecture 2 §5).
- **One-page resume version:** compress the three-project progression into the three resume bullets you'd actually use, each with a number. If you can't get each to one quantified line, your project framing is still fuzzy.
- **The recruiter skim test:** give a non-robotics friend 90 seconds with `portfolio.md` and ask them to tell you, afterward, what you built and which project is strongest. If they can't, your top-level framing isn't landing in the window a recruiter actually spends.
- **The tailored cover:** write the one-paragraph "why me, why you" for a specific robotics company, leading with the project that matches their domain (§4.1). It's the email that gets your portfolio opened in the first place.
