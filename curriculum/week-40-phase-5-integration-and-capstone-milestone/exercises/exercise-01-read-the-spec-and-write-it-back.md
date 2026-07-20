# Exercise 1 — Read the Capstone Spec and Write It Back

**Type:** Guided (Markdown deliverable). **Estimated time:** 90 minutes.

This is the most important 90 minutes of the week, and it does not involve a line of robot code. You are going to read the capstone specification as a contract (Lecture 1) and produce the two artifacts that defend your entire milestone: a **requirements-traceability table** and a one-page **"what I heard" restatement** with explicit non-goals. Half of capstone failures are reading failures. This exercise is the insurance against being one of them.

The deliverable is a single Markdown file, `what-i-heard.md`, committed to your Week 40 repo. A peer reviews it against the spec. Where your restatement diverges from the spec, you fix the restatement; where the spec is genuinely ambiguous, you state the reading you chose and why.

---

## Step 0 — Open the contract

Open [`SYLLABUS.md`](../../../SYLLABUS.md) to the section "Capstone specification — Autonomous Mobile Manipulator with Language-Conditioned Pick-and-Place." Read it once, end to end, without taking notes. Then read it again, slowly, this time as the Week 48 panel will read it: looking for the clause you are quietly hoping nobody enforces.

You are reading for three things, in this order:

1. **The required system properties** (the spec lists eight).
2. **The acceptance criteria** (the spec lists five, joined by "if and only if").
3. **The ambiguities** — phrases that could be read more than one way and that you must pin down before you build.

---

## Step 1 — Build the requirements-traceability table

Create `what-i-heard.md`. Its centerpiece is a table with exactly four columns:

| Column | What goes in it |
|---|---|
| **Requirement** | The spec clause, verbatim or near-verbatim. Quote the number if there is one. |
| **What I heard** | Your restatement in your own words, *adding the precision the spec left implicit* (which endpoints? mean or p95? which frame?). |
| **Owning artifact** | The concrete node, topic, or file in your system that delivers this. If you cannot name one, you have a gap. |
| **Acceptance test** | The runnable command or measurement that proves it. If you cannot name one, the requirement is unmeasurable. |

You owe **one row per required property (8) and one row per acceptance criterion (5)** — thirteen rows minimum. Here are two rows filled in, one of each kind, as the worked example. Match this level of precision.

A **property** row:

| Requirement | What I heard | Owning artifact | Acceptance test |
|---|---|---|---|
| P5 — "Software E-stop topic with 200 ms latch" | When `/safety/estop` (`std_msgs/Bool`) latches `true`, `cmd_vel` must reach zero and the arm trajectory must halt within 200 ms, measured from the latch timestamp to the first zero `cmd_vel` | `safety_wrapper` node; `/safety/estop` topic; `/cmd_vel` output | `python3 measure_estop_latency.py` latches the topic, timestamps it, and reports the time to zero `cmd_vel`; assert p95 ≤ 200 ms over 10 trials |

An **acceptance-criterion** row:

| Requirement | What I heard | Owning artifact | Acceptance test |
|---|---|---|---|
| AC — "fused state estimate drifts < 0.5 m over a 20-meter trajectory" | Driving a measured 20 m path, the Euclidean distance between my `/odometry/filtered` final pose and the sim ground-truth final pose must be < 0.5 m | `ekf_node` (`robot_localization`); `/odometry/filtered`; sim ground-truth pose | `python3 measure_drift.py` drives the path, logs both poses, reports final Euclidean error; assert < 0.5 m |

Fill in all thirteen rows. For the eight properties, work straight down the spec's list. For the five acceptance criteria, work straight down the "if and only if" list. **Every cell must be filled.** An empty "owning artifact" cell is a finding: a requirement nothing in your system owns. An empty "acceptance test" cell is a finding: a requirement you cannot prove you met. Findings are good — better you find them now than the panel finds them at the defense. Note each finding in a "Gaps" subsection below the table.

---

## Step 2 — Write the non-goals paragraph

Below the table, add a section titled **"Non-goals (what the contract does not require, that I am deliberately not building this milestone)."** Write a paragraph that names, explicitly, the things you are choosing not to do because the spec does not require them. At minimum, address:

- **The MPC base controller.** The spec says "PID at minimum for the base; MPC bonus." State whether you are shipping PID and skipping MPC, and why (time budget).
- **The 3D obstacle costmap, if you are not building one.** If the spec does not require it, say so.
- **Anything else you considered building and decided against** on contract-reading grounds.

A stated non-goal is a decision you can defend. An unstated one looks, to a reviewer, like something you forgot. The non-goals paragraph is how you protect your time budget against both your own perfectionism and a reviewer's assumption.

---

## Step 3 — Resolve the ambiguities

Add a section titled **"Ambiguities resolved."** The spec has at least four phrases that can be read more than one way. For each, state the reading you chose:

1. **"The red cup" when two cups match.** How does your system resolve a referring expression with a spatial disambiguator ("from the left bench")? What does it do if two objects match all cues — ask, or abort? State your choice.
2. **"End-to-end latency" endpoints.** Which two timestamps bound the ≤ 50 ms perception latency? (The standard reading: sensor stamp to `/perception/objects` publish, p95.)
3. **"Operational state" for the < 60 s cold boot.** Define "operational" precisely — what condition, observable, marks the boot complete?
4. **"No manual intervention" for this week's milestone.** Define the boundary: what counts as intervention during a run, and what (pre-positioning the object, issuing the instruction) does not?

For each, write one or two sentences. Where the spec genuinely leaves a choice, your choice plus your reasoning *is* the correct answer — the reviewer's job is to agree or correct, and either way the disagreement surfaces cheaply now.

---

## Step 4 — Peer review

Hand `what-i-heard.md` and the spec to a peer (or post both in your cohort channel). The reviewer reads your restatement against the spec and flags every divergence:

- A "what I heard" cell that says more or less than the spec.
- An owning artifact that does not actually deliver the requirement.
- An acceptance test that does not actually test the requirement.
- A non-goal that is actually required (a misread of a floor as a ceiling).

You fix every divergence. The reviewer signs off when your restatement matches the spec and your gaps are honestly listed.

---

## Expected output

A committed `what-i-heard.md` containing:

```
# Capstone — What I Heard (requirements restatement)

## Requirements-traceability table
| Requirement | What I heard | Owning artifact | Acceptance test |
|---|---|---|---|
| P1 — fused estimate, latency <= 50 ms | EKF fuses IMU+LiDAR+RGB-D; sensor stamp -> /perception/objects p95 <= 50 ms | fused_perception_node | measure_perception_latency.py p95 <= 50 ms |
(13+ rows total, every cell filled — see Lecture 1, section 1.8 for the full worked table)

## Gaps
- P8 (OTA): no owning artifact yet; action item: write OTA-PROCEDURE.md this week.

## Non-goals (deliberately not building this milestone)
- PID base controller shipped; MPC (marked "bonus") deferred to a stretch goal because the spec marks it optional and my hours go to unmet requirements.
- No 3D obstacle costmap this milestone: the spec does not require one and 2D suffices for the tabletop task.

## Ambiguities resolved
1. Referring expressions: resolved by attribute + spatial cue; on tie, the robot aborts and alerts, because a wrong-object grasp is a safety hazard, not a UX miss.
2. Perception latency endpoints: sensor stamp -> /perception/objects publish, p95, because "end-to-end" without endpoints is unmeasurable.
3. Operational state: lifecycle manager reports all nodes active AND preflight passes AND an instruction is accepted, because that is the first moment the robot can act on a goal.
4. Manual intervention: any keyboard/topic action influencing the run after the instruction is issued; pre-positioning and issuing the instruction are not intervention, because they are setup, not in-run correction.

## Peer review
- Reviewer: Dana Okafor. Divergences flagged: 2. All resolved: yes.
```

When a reviewer can read `what-i-heard.md` and your spec side by side and find no divergence, you have the artifact that defends the rest of your milestone — and the skeleton of your Week 41 safety case and Week 44 eval suite.

---

## Why this exercise matters

In a real shop, the cost of a misunderstood requirement is person-weeks. This exercise moves the discovery of every misunderstanding from the demo (expensive) to the kickoff (cheap). The traceability table is not bureaucracy — it is the map from the contract back onto thirty-nine weeks of components, and the "acceptance test" column is the list of measurements you will run for the rest of the track. Build it once, build it precisely, and every downstream week inherits a clean target.
