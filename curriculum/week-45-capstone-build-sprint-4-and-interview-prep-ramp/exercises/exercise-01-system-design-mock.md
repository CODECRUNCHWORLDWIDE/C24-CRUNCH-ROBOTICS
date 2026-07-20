# Exercise 1 — System-Design Mock Interview: Warehouse AMR

**Goal:** Run a realistic 45-minute system-design mock with a peer. One of you is the candidate, one is the interviewer; then you swap. By the end you each have a scored rubric and a list of where you froze.

**Estimated time:** ~90 minutes for both of you (45 min each, plus 5 min of feedback per round).

**You need:** a peer (or a senior engineer), a whiteboard (physical, tablet, or Excalidraw), and a timer. Read Lecture 1 first — this exercise *is* Lecture 1, applied.

---

## The prompt

> **"Design the onboard autonomy stack for a warehouse Autonomous Mobile Robot (AMR) that moves totes between pick stations and packing, sharing floor space with human workers. Walk me through it."**

That's all the candidate gets to start. Everything else they have to ask for.

---

## Roles

### If you are the CANDIDATE

Run the seven-phase method from Lecture 1. Out loud. The whole time.

```
1. CLARIFY      (2–4 min)
2. SCOPE        (1–2 min)
3. BUDGETS      (4–6 min)
4. BOX DIAGRAM  (10–15 min)
5. DEEP-DIVE    (8–12 min)
6. FAILURE      (5–8 min)
7. WRAP         (2 min)
```

Your checklist — tick these as you go; the interviewer is scoring against the same list:

- [ ] You asked at least **three** clarifying questions before drawing anything.
- [ ] You stated your **assumptions out loud** and wrote them on the board.
- [ ] You **scoped** explicitly ("I'll design the onboard stack, not the fleet backend").
- [ ] You discussed at least **three of the four budgets** (sensor, compute, latency, power).
- [ ] You connected **latency to stopping distance to the safety layer** at least once.
- [ ] You drew a **box diagram** with labelled arrows and a **separate safety band**.
- [ ] You went **deep on at least one box** when asked.
- [ ] You **volunteered a failure-mode analysis** without being prompted.
- [ ] You **named the single biggest risk** in your wrap.
- [ ] You **never overclaimed** — everything you said, you could defend one level deeper.

### If you are the INTERVIEWER

Your job is to make the candidate *work*, then score them fairly. Stay quiet when they're driving well; push when they stall or hand-wave.

Open with the prompt verbatim. Then:

1. **Answer their clarifying questions** with these facts (don't volunteer; make them ask):
   - Payload: totes, up to 8 kg.
   - Space: shared with humans, no cages.
   - Fleet: ~50 robots in one facility.
   - Environment: brownfield, no floor markers allowed, concrete floor, decent Wi-Fi.
   - Speed target: up to 1.5 m/s.
2. **If they jump to components before clarifying**, ask: "Before you pick sensors — what are you optimizing for?" (Tests whether they self-correct to requirements.)
3. **Pick one box and force a deep-dive.** Good ones: "Go deeper on localization." or "How does perception not miss a person?" or "Walk me through what happens the instant the LiDAR dies."
4. **Probe with three layers of 'why'** on one decision. E.g.: "Why MPC for the base?" → "Why not LQR?" → "Why are the constraints hard rather than soft?" Note where they bottom out.
5. **Throw one curveball** near the end: "It's now 200 robots across three buildings — what changes?" (Tests whether they can scale their answer to fleet ops.)

Take notes on the rubric below as they talk. Don't coach mid-interview; save it for the debrief.

---

## The rubric (40 points)

Score each dimension 0–4. Candidate and interviewer score independently, then compare — the *gap* between your two scores is itself a signal about self-awareness.

| # | Dimension | 0 | 2 | 4 |
|---|-----------|---|---|---|
| 1 | **Clarification** | Started designing immediately | Asked 1–2 questions | Asked 3+ sharp questions, pinned the problem |
| 2 | **Scoping** | Tried to design everything | Implicit scope | Explicit, sensible scope stated up front |
| 3 | **Sensor budget** | No sensor reasoning | Listed sensors | Justified each sensor; separated safety vs perception sensing |
| 4 | **Compute budget** | Ignored compute | Named a target | Named target + split the budget across nodes |
| 5 | **Latency budget** | Never mentioned | Mentioned vaguely | Budgeted stages + tied to stopping distance/safety |
| 6 | **Box diagram** | No diagram or unreadable | Boxes, no labels | Clear, labelled arrows, safety band present |
| 7 | **Deep-dive depth** | Couldn't go deeper | Surface answer | Defended a box to the 2nd–3rd layer |
| 8 | **Failure analysis** | None | Prompted, thin | Volunteered, covered detection + response |
| 9 | **Communication** | Designed in silence | Narrated some | Narrated throughout, clear and structured |
| 10 | **Honesty / no overclaim** | Bluffed and got caught | Minor overclaim | Defended everything; said "I'd measure that" at the edge |

**Total: ___ / 40.** Write your two lowest dimensions down — those go into your study plan (exercise 3).

---

## Two reference answers to calibrate against

You're not grading against perfection; you're grading against these bands.

**A passing (28–32) candidate** clarifies payload/shared-space/fleet, scopes to the onboard stack, names an Orin target and a rough latency budget, draws a labelled box diagram with a safety band, goes one layer deep on localization or perception when asked, and volunteers two or three failure modes. They may stumble on the third "why" or forget the power budget. That's a pass.

**A strong (36–40) candidate** does all of the above *and* ties the 48 ms latency to 7 cm of travel to "that's why the safety LiDAR is on an independent certified path," handles the 200-robot curveball with fleet traffic-management and shared-map reasoning, defends MPC-over-LQR to the constraint level, and names "perception false-negatives in clutter" as the biggest risk in a crisp wrap. That candidate gets the next round.

---

## Expected output of this exercise

After both rounds you should each have:

```
System-design mock — candidate: <your name>
  Self-score:        29 / 40
  Interviewer score: 26 / 40
  Score gap:         3  (you rated yourself higher — watch for that)
  Two weakest dimensions: #5 latency budget (1/4), #8 failure analysis (2/4)
  Froze on: connecting latency to stopping distance; forgot the safety band until prompted
```

Keep this. Exercise 3 turns it into a study plan. Then **swap roles and run it again** — being the interviewer teaches you what good looks like faster than being the candidate.

---

## Common ways the candidate loses points (read after your round)

- Spent twelve minutes clarifying and ran out of time at the diagram. Budget the clock.
- Drew a gorgeous diagram in total silence. Narrate or it doesn't count.
- Forgot the safety band. In robotics this is near-disqualifying; it should be reflexive.
- Said "I'd use a factor graph for localization" and then couldn't say why not an EKF. Don't name what you can't defend.
- Answered "it depends" to everything and committed to nothing. State an assumption and move.

---

## Hint (read only if you froze badly)

If you blanked on the box diagram, it's because you tried to invent a new architecture under pressure. Don't. **Draw your own capstone.** You already built a perception → state-estimation → planning → control → policy stack with a safety layer. The warehouse AMR *is* that stack with totes instead of a red cup. The interview is narration, not invention. Walk in knowing your own box diagram cold and the rest is steering.
