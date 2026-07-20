# Week 12 — Challenges

The exercises drill each classical-CV technique in isolation. **The challenge makes you the perception engineer who catches a sensor lying.** You're handed a drive where the wheel odometry is confidently wrong during a slip, and you have to detect it using nothing but the camera — the optical-flow-vs-wheel-odometry cross-check from Lecture 2 §4.1.

## Index

1. **[Challenge 1 — Flow velocity vs wheel odometry: catch the slip](challenge-01-flow-vs-wheel-odometry.md)** — estimate forward velocity from optical flow across a drive sequence, compare it frame-by-frame against the (lying) wheel odometry, and pinpoint the planted wheel-slip window where the two disagree. Then write up *why* an independent sensor catches a failure a single sensor never can. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 2 midterm in Week 16, where your fused perception stack must be *trustworthy*. The reviewer will ask "how would you know if your odometry were lying?" — and "I cross-check it against optical flow, and here's the slip I caught" is the answer that separates an engineer who *uses* sensors from one who *audits* them. Every real robot eventually slips a wheel on a wet floor; the engineer who built the cross-check is the one whose robot doesn't drive into a wall convinced it's somewhere else.
