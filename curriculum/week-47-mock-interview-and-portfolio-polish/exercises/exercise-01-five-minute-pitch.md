# Exercise 1 — The Five-Minute Pitch

**Type:** Written + recorded.
**Estimated time:** ~50 minutes.
**Outcome:** A written and recorded five-minute capstone pitch, timed under 5:00, that seeds the deep-dive toward your strengths and pre-answers the failure question (Lecture 1 §5).

"Tell me about your capstone" opens the behavioral round and often the whole loop. The first thirty seconds decide whether the interviewer leans in or checks the clock. This is the single most-reused answer in your interview career — write it, record it, time it, until it's automatic.

---

## The structure (five parts, five minutes)

Write one section per part. The time budgets are targets — total must come in under 5:00.

1. **The problem (20 s).** One sentence, concrete, the *what* before any *how*. "I built an autonomous mobile manipulator that takes a natural-language instruction — 'bring me the red cup from the left bench' — and carries it out safely in a shared space."

2. **The stack (90 s).** The spine, named, not explained: fused IMU+LiDAR+RGB-D perception → EKF → Nav2 (base) + MoveIt2 (arm) → an OpenVLA policy that picks the grasp from the instruction → a behavior tree on top → a safety layer underneath. You're giving the map, not the tour.

3. **One hard decision (60 s).** The decision you can defend *best*, told as a trade-off. This is the hook that steers the deep-dive toward ground you're ready for. "The hardest call was the base controller — I chose MPC over LQR because the aisles have hard lateral constraints I wanted inside the optimization..."

4. **One failure survived (60 s).** Your chaos drill (Week 46). "In gameday the LiDAR was killed mid-task; the robot detected it in 1.2 s via a QoS deadline event, dropped to camera-only nav, flagged the operator, and safe-aborted the grasp because it needed the sensor it lost." This pre-answers "tell me about a failure."

5. **The result (30 s).** A number, against the capstone acceptance criteria. "17 of 20 eval instructions, under 0.5 m drift over 20 meters, cold-boots in under a minute."

---

## What you must produce

- `pitch-script.md` — the written pitch, the five parts, ≤ 600 words (you speak ~120 wpm, so 600 words ≈ 5 minutes).
- `pitch-recording.{m4a,mp4}` — you delivering it, timed, **under 5:00**.
- A one-line self-note: the time you hit and the one part that ran long.

---

## Acceptance criteria

- [ ] All five parts present, in order, with the problem stated as one concrete sentence *before* any how.
- [ ] The "one hard decision" is a real trade-off with a named rejected alternative (not "I used X because the lecture did").
- [ ] The "one failure survived" is your actual chaos drill, with a detection *time*.
- [ ] The result is a *number* tied to the acceptance criteria, not an adjective.
- [ ] The recording is **under 5:00** without rushing (if you had to speed up to fit, the script is too long — cut it).

## Deliverable

Commit `pitch-script.md` and the recording next to your capstone. This is your Week 48 opening line; rehearse it until it's under five minutes cold.

---

## Hint

The two parts learners get wrong:

- **The problem sentence runs long.** "So my capstone is a robot that, um, uses a vision-language model and also does navigation and..." — that's not a sentence, it's a list. One concrete sentence: *what* it does, for a human listener. Rewrite it five times until it's tight.
- **The result is an adjective.** "It worked really well" tells the interviewer nothing and signals you didn't measure. "17/20, < 0.5 m drift" tells them you're an engineer. Pull the numbers from your Week 44 eval suite and Week 39 latency report — they're your ammunition (Lecture 1 §7).

Record it, watch it back at 1.5x with the sound off (Lecture 1 stretch goal), and count your filler words with the sound on. Both are fixable and both cost you credibility in the room.
