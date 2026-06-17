# Week 37 — Challenges

The exercises drill the wiring. **The challenge makes you the red-team engineer.** Your job is to *break* your own VLA — to engineer scenes and instructions that make it confidently wrong — and then prove your gate catches each one. A robot you can't break in the lab is a robot that breaks in the field; the discipline is to find the failures yourself, first.

## Index

1. **[Challenge 1 — Hallucination hunt](./challenge-01-hallucination-hunt.md)** — construct adversarial scenes that trigger each of the five VLA failure modes, measure how often the un-gated VLA executes the wrong action, then show your grounding gate + fallback catches them and report the residual rate. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 5 milestone (Week 40) and the capstone safety case (Week 41), where you must document *foreseeable misuse* and the mitigations for it. The skill — adversarially probing a learned policy until you know exactly where it lies, and proving your runtime check catches it — is exactly what separates an engineer who "got the VLA demo working" from one who can sign a safety case that says "here is where it fails and here is what stops the failure from reaching the actuators."
