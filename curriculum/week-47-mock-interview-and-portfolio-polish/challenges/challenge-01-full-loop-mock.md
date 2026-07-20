# Challenge 1 — The Full-Loop Mock

**Type:** Live, adversarial, paired. Needs a senior reviewer (or instructor) to run the loop and score it.
**Estimated time:** ~3 hours (loop ~2h, debrief + write-up 1h).
**Difficulty:** Hard — this is the mock robotics-startup interview, 5% of the track, and the dress rehearsal for the Week 48 defense.

---

## The setup

A senior-engineer reviewer runs you through the complete five-round loop, back to back, the way a real robotics startup would. They have the rubric and a notepad. Their job is to find the gap between what your portfolio claims and what you actually know. Your job is to survive all five rounds, manage your energy, and defend your stack honestly under follow-up. Solo-path learners: the mini-project explains how to self-run the loop with a recording and a structured self-debrief — but find a human; the unfamiliar interviewer's pressure is the point.

---

## The five rounds

Run them in order, with short breaks, on the clock.

### Round 1 — Intro (15 min)
The reviewer asks you to walk through your background and how you got to robotics. Tests: coherent narrative, reading the room. Use it to warm up and set a calm, confident tone.

### Round 2 — Technical deep-dive (45 min)
The reviewer picks one thing from your stack and digs until they find your edge. Likely: "Explain your EKF; write the predict step." or "Why a VLA, not a scripted grasp?" Tests: depth, not breadth. Bring a number to every claim. When you hit your edge, say so and say how you'd find out — don't bluff.

### Round 3 — System design (45 min)
"Design the autonomy stack for a warehouse AMR" (or another robot). Run the seven-phase method out loud: clarify → requirements → sensor budget → compute/latency budget → box diagram → failure modes → safety one-liner. Tests: judgment under ambiguity. Watch the clock; reach failure modes.

### Round 4 — Behavioral / portfolio (45 min)
Lead with your five-minute capstone pitch. Then: "tell me about a time it failed" (your chaos drill), "what would you do differently" (your retro), "the hardest bug" (with the debugging process). Tests: communication, honesty, ownership.

### Round 5 — Founder / culture (30 min)
"Why robotics? Why this kind of company?" Tests: motivation and fit. Save genuine enthusiasm for it even though you're tired.

---

## Acceptance criteria

You pass the challenge if:

- [ ] You completed **all five rounds** on the clock without skipping.
- [ ] In the **deep-dive**, you defended at least one decision through three "why" layers with a *number* from a real artifact, and named a rejected alternative.
- [ ] In **system design**, you ran the seven-phase method end to end and reached **failure modes** and the **safety one-liner** (not just the box diagram).
- [ ] In the **behavioral**, you delivered the five-minute pitch under 5:00 and answered the failure question with a real chaos-drill story.
- [ ] You hit your knowledge edge at least once and handled it with **"here's how I'd find out,"** not a bluff (this is a pass).
- [ ] You and your reviewer **both scored** the loop, and you recorded the self-vs-interviewer gap honestly.

## Deliverable

Commit, next to your capstone:

1. `loop-debrief.md` — the reviewer's per-round scores and notes, your self-scores, and the gap (from Exercise 3's tool).
2. The **two weakest rounds** named, with a concrete fix scheduled before Week 48.
3. The **marker line** from the README:

   ```
   Loop mock (5 rounds): intro 8/10 · technical 26/30 · system-design 24/30 ·
                         behavioral 17/20 · culture 9/10   → 84/100  (weakest: system-design pacing)
   ```

This debrief is the input to your final week of prep. Do it honestly — a loop you "passed" by going easy on yourself is worth nothing, because the Week 48 panel will not go easy.

---

## Stretch

- **The hostile interviewer.** Have the reviewer deliberately assert something false mid-deep-dive ("an EKF is exact for nonlinear systems, right?") and see if you catch and correct it. Catching it scores big; agreeing to be agreeable is a quiet fail.
- **The second system-design prompt.** Run a *different* robot (hospital delivery, sidewalk rover) cold. Notice which parts of your answer transfer and which you had memorized. The transferable parts are the ones you actually understand.
- **Record the whole loop** and watch the deep-dive back. Where do you reach for filler ("um, basically, kind of") — that's where you're least sure, and the interviewer hears it too.
- **Swap seats.** Interview a peer through one round. Being the interviewer teaches you what the questions are *for*, which makes you a better candidate.
