# Week 45 — Capstone Build Sprint 4 + Interview-Prep Ramp

Welcome to Week 45. You are three weeks from the capstone defense, and this is the week the work splits cleanly into two tracks that run in parallel. Track one is the last *quiet* build sprint on your mobile manipulator — the polish sprint, the one where you stop adding features and start hardening the ones you have. Track two is new, and it is the reason this week exists: you start building **interview muscle**.

Here is the thing nobody tells you. You have spent forty-four weeks becoming a robotics engineer who can architect a perception-to-policy stack. None of that matters in a forty-five-minute interview if you cannot **say it out loud, under pressure, at a whiteboard, while a skeptical staff engineer asks "why" four times in a row.** The capstone is the artifact. This week is about learning to *defend* it. The two are not the same skill, and the second one is the one that gets you the offer.

We are not going to teach you tricks. There are no tricks. We are going to put you through two graded mock interviews — one system-design ("design the autonomy stack for a warehouse AMR"), one technical ("explain how an EKF works and write the predict step on the board") — make you grade yourself honestly against a rubric, and then turn your weakest topics into a targeted study plan for the Week 47 full-loop mock. By Friday you will have defended your own stack against three layers of follow-up questioning and lived to tell about it.

This is the week you stop being someone who *has* built a robot and become someone who can *prove* it across a table.

## Learning objectives

By the end of this week, you will be able to:

- **Whiteboard** a complete robotics-startup system-design answer — requirements, constraints, sensor budget, compute budget, the autonomy stack box diagram, failure modes, and the safety story — in forty-five minutes without freezing.
- **Drive** a system-design interview as the candidate: clarify the prompt, state assumptions out loud, scope to fit the time, and steer the interviewer toward the parts of the design you know cold.
- **Explain** an Extended Kalman Filter end to end at a whiteboard — the predict step, the update step, the Jacobians, the covariance flow — and write the predict equations from memory without notes.
- **Answer** the core robotics technical-interview categories: kinematics (forward/inverse, SE(3), Jacobians), controls (PID vs LQR vs MPC, stability), sensor fusion (EKF/UKF/factor graphs), and a clean coding question under a timer.
- **Run** the "five technical projects" résumé conversation — pick a project, tell the STAR-shaped story in two minutes, then survive the deep-dive follow-ups without overclaiming.
- **Defend** a real design decision from your own capstone (why PID/MPC for the base, why OpenVLA for the policy, why an EKF instead of a factor graph) through at least three layers of "why" without collapsing into "it's what the tutorial used."
- **Grade** a mock interview honestly against a rubric, identify your two weakest topics, and convert them into a concrete, time-boxed study plan.
- **Ship** the Sprint-4 polish on the capstone: kill the last two warnings in your launch graph, tighten one latency hotspot, and write the one-paragraph architecture summary you will read aloud in the defense.

## Prerequisites

This week assumes you have completed Weeks 1–44 of C24, and specifically that:

- You have a **working capstone** — at minimum a simulated mobile manipulator that takes a language instruction and runs a perception → planner → controller → policy stack. Weeks 41–44 built and hardened it; this week you defend it, so it has to run.
- You completed the **Week 41 safety case**, the **Week 43 telemetry dashboard**, and the **Week 44 twenty-instruction eval suite**. You will reference all three in your mock interviews.
- You can derive an **EKF predict/update** on paper. Week 11 taught it; if it is rusty, re-read your Week 11 notes *before* Monday, because the technical mock assumes it.
- You can state, from memory, **why you picked every major component** of your stack. If you cannot, that is exactly the gap this week closes.
- You have a **peer** (another C24 learner, or a senior engineer willing to sit on the other side of the table) to run the two mocks with. Solo-path learners: instructions for self-running both mocks with a recording are in the mini-project.

You do **not** need new hardware or new libraries this week. Everything here runs on the stack you already have. The only new "tool" is a whiteboard (a real one, a tablet, or `excalidraw.com`) and a timer.

## Topics covered

- The anatomy of a robotics-startup interview loop in 2026: recruiter screen → technical phone → system-design → technical-deep-dive → résumé/behavioral → founder/culture. Where each one is won and lost.
- System design on the whiteboard: the requirements-first method, the sensor budget, the compute budget, the latency budget, the box diagram, failure-mode enumeration, and the safety-case one-liner.
- The warehouse-AMR design prompt, end to end — the single most common robotics system-design question, fully worked.
- The robotics technical interview, by category: kinematics (FK/IK, SE(3), the manipulator Jacobian), controls (PID, LQR, MPC, when each, stability arguments), state estimation (EKF, UKF, factor graphs, when each), perception, and a timed coding question.
- The Extended Kalman Filter as an interview centerpiece: the predict step, the update step, the Jacobians `F` and `H`, the covariance propagation, and the three follow-ups that always come (linearization error, tuning `Q`/`R`, divergence).
- The "five technical projects" résumé conversation: how to pick the five, how to tell each in two minutes (STAR), and how to survive the deep dive without overclaiming or getting caught not knowing your own code.
- Defending a design decision under recursive "why" questioning — the three-layer drill, and how to fail gracefully when you hit the edge of your knowledge.
- Self-grading with a rubric: scoring system-design and technical mocks, finding your two weakest topics, and writing a study plan that actually closes them before Week 47.
- Sprint-4 capstone polish: warning triage in the launch graph, a single latency-hotspot tightening, and the architecture-summary paragraph.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — the build-sprint time is yours to reallocate toward whichever capstone polish your stack needs.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Robotics-startup system design on the whiteboard            |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The technical interview: kinematics, controls, sensor fusion |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | System-design mock #1 + self-grade; capstone polish         |    0h    |    2h     |     1h     |    0.5h   |   1h     |     1h       |    0.5h    |     6h      |
| Thursday  | Technical mock #2 (EKF predict on the board) + self-grade   |    0h    |    1.5h   |     1h     |    0.5h   |   1h     |     1.5h     |    0h      |     6h      |
| Friday    | The résumé conversation; defend-your-stack challenge        |    0h    |    0h     |     1.5h   |    0.5h   |   1h     |     2h       |    0.5h    |     6h      |
| Saturday  | Mini-project: graded mocks + study plan; capstone polish    |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0.5h    |     4.5h    |
| Sunday    | Quiz, review, weakest-topic study-plan writeup              |    0h    |    0h     |     0h     |    1h     |   1h     |     0.5h     |    0h      |     2.5h    |
| **Total** |                                                             | **6h**   | **7h**    | **4.5h**   | **3.5h**  | **6h**   | **9h**       | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Curated, current (2026) interview-prep and system-design references |
| [lecture-notes/01-robotics-startup-system-design-on-the-whiteboard.md](./02-lecture-notes/01-robotics-startup-system-design-on-the-whiteboard.md) | The requirements-first method, the budgets, the box diagram, and the warehouse-AMR prompt worked end to end |
| [lecture-notes/02-the-robotics-technical-interview.md](./02-lecture-notes/02-the-robotics-technical-interview.md) | Kinematics, controls, sensor fusion, the EKF on the board, and the five-projects résumé conversation |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of this week's three exercises |
| [exercises/exercise-01-system-design-mock.md](./03-exercises/exercise-01-system-design-mock.md) | Run a system-design mock with a peer (design a warehouse-AMR autonomy stack) |
| [exercises/exercise-02-ekf-predict-on-the-board.py](./03-exercises/exercise-02-ekf-predict-on-the-board.py) | Write and verify the EKF predict step you will reproduce on the whiteboard |
| [exercises/exercise-03-self-grade-mocks.py](./03-exercises/exercise-03-self-grade-mocks.py) | Score both mocks against the rubric and rank your weakest topics |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of this week's challenge |
| [challenges/challenge-01-defend-your-stack.md](./04-challenges/challenge-01-defend-your-stack.md) | Defend a probed capstone decision through three layers of "why" |
| [quiz.md](./05-quiz.md) | 13 questions with an answer key |
| [homework.md](./06-homework.md) | Concrete deliverables with a grading rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Two graded mock interviews + a targeted study plan for Week 47 |

## The "say it out loud" promise

Every other week in C24 ends in working code. This week ends in something different and harder to fake: **you can explain your robot to a stranger who is trying to find the holes.** The marker we use here is not `Build succeeded`. It is this, written at the top of your homework:

```
Mock 1 (system design): 31/40 · weakest: latency budgeting, failure-mode coverage
Mock 2 (technical):     27/40 · weakest: EKF update Jacobian, MPC stability argument
Study plan: 4 topics, 6.5 hours, scheduled before Week 47.
```

If you cannot fill in those numbers honestly, you are not done. A mock you "passed" because you went easy on yourself is worth nothing. The whole point is to find the holes *now*, with a peer, instead of in Week 47 in front of a reviewer or — worse — in a real loop with an offer on the line.

## A note on honesty

The single most common way candidates fail robotics interviews is **overclaiming**. They say "I built a Kalman filter" and cannot write the predict step. They say "I used MPC" and cannot say what the cost function penalized. They say "my policy was OpenVLA" and cannot explain why they did not just use a scripted grasp. The interviewer's entire job is to find the gap between what you claim and what you know, and they are very good at it.

The defense against overclaiming is not to claim less. It is to **know your own stack to the third layer of "why."** That is what the challenge this week trains, and it is the difference between a candidate who sounds senior and one who *is* senior. Do not skip the challenge.

## Stretch goals

If you finish the regular work early:

- Record one of your mocks on video and watch it back with the sound off. Watch your hands, your pauses, where you look. The non-verbal tells are brutal and fixable.
- Take the warehouse-AMR design and re-do it for a **different** robot: a hospital delivery bot, an orchard-scouting drone, a sidewalk last-mile rover. Notice which parts of your stack answer transfer and which do not.
- Write the EKF predict *and* update steps for your own capstone's specific state vector and sensor set. Most learners can do the textbook version; far fewer can instantiate it for their own robot.
- Read one published robotics-company engineering blog post (see `resources.md`) and reverse-engineer the system-design question that post implicitly answers.

## Up next

**Week 46 — Gameday: the chaos drill.** Two intentional failures injected live (LiDAR dropout mid-task; planner deadlock at a doorway), two postmortems, and a hard look at whether your robot degrades gracefully. The interview muscle you build this week is exactly what you will need when a reviewer asks "and what happened when the sensor died?" — so make this week count.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
