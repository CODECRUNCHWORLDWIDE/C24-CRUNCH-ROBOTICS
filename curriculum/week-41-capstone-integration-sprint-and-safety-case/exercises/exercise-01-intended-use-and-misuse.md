# Exercise 1 — Intended Use and Foreseeable Misuse

**Goal:** Write the two sections that bound your entire capstone safety case. Everything downstream — every hazard, every mitigation, every residual-risk acceptance — is constrained by what you write here. Get these right and the rest of the case has a frame. Get them wrong (vague intended use, missing misuse) and a reviewer fails the whole case at the first page.

**Estimated time:** 50 minutes.

**Deliverable:** `safety-case/01-intended-use-and-misuse.md` in your capstone repo. This file is reused verbatim as §1 of the mini-project. Do not write it twice.

---

## Why this exercise is hard (and worth it)

Engineers find this harder than writing code, because there is no compiler to tell you when you're wrong. The "compiler" here is a skeptical reader. The skill you are building is *bounding a claim* — saying precisely what you are and are not asserting — which is the same skill behind a good API contract, a good SLA, and a good test. Robotics just raises the stakes: an unbounded safety claim is how people get hurt.

---

## Part A — Intended use and the Operational Design Domain

Write an **intended-use** statement and an explicit **Operational Design Domain (ODD)** for your capstone robot. Follow the structure from Lecture 1 §4.

### Steps

1. **One-paragraph intended use.** What is the robot *for*? Who operates it? On what kind of objects, in what kind of space? Be concrete — "an indoor mobile manipulator that retrieves small lightweight objects on flat finished floors in response to operator instructions," not "a helpful robot."

2. **The ODD, as a bulleted list of bounds.** At minimum, bound every one of these axes:
   - *Environment:* surface, slope, lighting range, indoor/outdoor, stairs (yes/no).
   - *People:* trained operators only, or untrained adults / supervised children too?
   - *Objects:* size, mass, type (rigid? liquid? sharp? living?).
   - *Speed:* nominal base speed and the reduced speed near people, arm TCP speed limits.
   - *Supervision:* is an operator reachable? Can they trigger a stop? Is the hardware E-stop physically reachable?
   - *Duty cycle / power:* run time, minimum battery, charging state during operation.

3. **The "out of scope" line.** Explicitly list three things the robot is *not* for and is not claimed safe for. (e.g. "not for outdoor use," "not for objects over 0.5 kg," "not for use without an operator reachable.") Every out-of-scope item is a hazard you exclude — but you must then *enforce* the exclusion. Note next to each: how is this bound enforced? (A geofence? A payload check? A battery cutoff?)

### Acceptance criteria for Part A

- [ ] Intended use is one specific paragraph a stranger could read and correctly describe the robot.
- [ ] The ODD bounds all six axes above with *numbers* where numbers apply (speeds, masses, lux, slope).
- [ ] At least three explicit out-of-scope items, each with a one-line note on how the bound is enforced.
- [ ] A peer can read the ODD and tell you one thing your real demo does that the ODD forbids — and you either fix the demo or widen the ODD honestly. (If they can't, your ODD may be too vague to bound anything.)

---

## Part B — Reasonably foreseeable misuse

Now the section juniors skip. Write the **reasonably foreseeable misuse** section: the things people will *actually do* that you did not intend but can predict. Follow Lecture 1 §5.

### Steps

1. **Enumerate at least eight misuse scenarios.** Draw from these categories (and add your own):
   - A person enters the robot's planned path.
   - A person reaches into the arm's workspace while it moves.
   - A child climbs on / grabs the base or arm.
   - Someone operates it outside the ODD (a ramp, the dark, an overweight object).
   - Someone defeats a guard (tapes the E-stop, disables a speed gate for a demo).
   - An ambiguous or adversarial instruction is issued ("bring me the knife"; "go faster").
   - Someone keeps using the robot while it is visibly degraded (flaky LiDAR).
   - Two of your own, specific to your capstone's task.

2. **For each scenario, write one sentence of worst-credible-harm.** Not the mitigation yet — just *what is the worst that could plausibly happen?* (e.g. "the arm continues to a target and strikes the reaching hand at full TCP speed.")

3. **Tag each scenario with a hazard-log ID** you will create in exercise 3 (e.g. `→ HZ-04`). This is the cross-reference that makes the misuse section *connect* to the hazard log instead of floating. You don't have the hazard log yet; assign the IDs now and create the matching rows in exercise 3.

### Acceptance criteria for Part B

- [ ] At least eight misuse scenarios, including the language-instruction one (your capstone takes natural-language commands — this hazard is non-negotiable for C24).
- [ ] Each scenario has a one-sentence worst-credible-harm.
- [ ] Each scenario carries a `→ HZ-NN` tag that you will honor in exercise 3.
- [ ] Not a single scenario is dismissed with "we assume that won't happen." If your ODD admits untrained people, you may not assume they behave.

---

## Worked fragment (use as a template, do not copy)

Here is a fragment for a generic indoor mobile manipulator. Yours must be specific to *your* capstone.

```markdown
## 1. Intended use

CrunchBot-41 is a single autonomous indoor mobile manipulator that retrieves
and delivers rigid objects (≤ 0.5 kg, ≤ 15 cm) on flat finished indoor floors
in response to natural-language instructions from an authorized operator. It is
intended for an assistive fetch-and-carry task in an office or lab, supervised
by an operator who is in the room or watching the dashboard.

### Operational Design Domain

- Environment: indoor, flat, dry, finished floor; 200–1000 lux; slope ≤ 3°; no stairs.
- People: shares space with untrained adults and supervised children (NOT operators).
- Objects: rigid, graspable, ≤ 0.5 kg, ≤ 15 cm; NOT liquids, sharps, or living things.
- Speed: base ≤ 0.5 m/s; ≤ 0.25 m/s within 1.5 m of a detected person; arm TCP ≤ 0.25 m/s near a person.
- Supervision: operator reachable; software E-stop on dashboard; hardware E-stop reachable on robot.
- Duty cycle: ≤ 2 h continuous; no operation below 20% battery.

### Out of scope (and how the bound is enforced)

- Outdoor / sloped / stair environments — enforced by a map geofence; robot refuses goals outside the mapped, validated area.
- Objects > 0.5 kg — enforced by a payload check on grasp; arm aborts and reports if measured load exceeds the limit.
- Operation with no operator reachable — enforced by a dashboard-heartbeat gate; autonomy refuses to start a task without an operator session.

## 2. Reasonably foreseeable misuse

| # | Scenario | Worst credible harm | Hazard |
|---|----------|---------------------|--------|
| M1 | A pedestrian walks into the corridor the base is traversing | Base impacts a shin / runs over a foot at speed | → HZ-01 |
| M2 | A bystander reaches for the object as the arm picks it | Arm strikes the reaching hand at TCP speed | → HZ-07 |
| M3 | A child grabs the moving arm | Pinch/crush of small fingers in a joint | → HZ-08 |
| M4 | Operator tapes down the E-stop to finish a demo | All software mitigations are now the only defense | → HZ-12 |
| M5 | Instruction "bring me the knife" issued; VLA grounds "knife" | Robot grasps and transports a sharp object toward a person | → HZ-09 |
| M6 | LiDAR is flaky but operator keeps running tasks | Stale costmap; base drives into an undetected obstacle/person | → HZ-03 |
| M7 | Someone places a 3 kg object and commands a pick | Overload; arm drops the load or destabilizes the base | → HZ-10 |
| M8 | Bystander stands still in the arm's swept volume, unseen | Arm completes motion into the person | → HZ-07 |
```

---

## Acceptance criteria (whole exercise)

You can mark this exercise done when:

- [ ] `safety-case/01-intended-use-and-misuse.md` exists with both sections.
- [ ] The ODD bounds all six axes with numbers; at least three enforced out-of-scope items.
- [ ] At least eight misuse scenarios, each with worst-credible-harm and a `→ HZ-NN` tag.
- [ ] A peer has read it and could not find an unbounded claim or an unaddressed obvious misuse.
- [ ] Nothing is dismissed with "won't happen."

---

## Stretch

- Add an **assumptions and dependencies** sub-section: what your safety claim *depends on* that is outside your control (the floor is maintained flat; the operator is trained on the dashboard; the network is present). Every assumption is a hazard if it is violated — note which ones you can enforce vs only assume.
- Compute the kinetic energy of your base at top speed (½mv²) and of your arm's worst-case TCP impact, and put the numbers in the intended-use section. Numbers make a reviewer trust you; "it's not very fast" does not.
- Map your ODD against ISO 13482's robot-type definitions (mobile servant / physical assistant / person carrier) and state which type your robot is and which clauses therefore apply.
