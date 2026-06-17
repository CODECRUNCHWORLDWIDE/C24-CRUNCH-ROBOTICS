# Week 41 — Challenges

One challenge this week, and it is the hinge of the whole safety case: take your FMEA, find the single most dangerous failure mode in your *integrated* autonomy stack, and demonstrably drive its risk down — with before/after numbers and evidence, not assertions.

## Index

1. **[Challenge 1 — FMEA the stack, kill the worst failure mode](./challenge-01-fmea-highest-severity-mitigation.md)** — run the FMEA across your full stack, identify the highest-severity failure mode, design and implement a mitigation that *demonstrably* reduces its risk rating, and document the before/after. (~2–3 hours)

## How to work the challenge

- This is open-ended on purpose. There is no single right answer — there is a right *method*: find the worst thing, attack it with an independent layer, measure that the attack worked.
- Use the FMEA tool from exercise 3 as your scoring engine so your before/after numbers come from the same source on both sides.
- "Demonstrably reduces" means a *measurement* or a *test*, not a claim. If you say detection improved, show the test that now catches what it previously missed.
- The before/after writeup is a portfolio artifact. It is exactly the story a robotics-startup interviewer wants: "here was our scariest failure, here is how we made it less scary, here is the evidence." Write it like you'll be asked to defend it, because you will.
