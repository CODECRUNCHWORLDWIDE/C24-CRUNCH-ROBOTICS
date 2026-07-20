# Week 38 — Challenges

The exercises drill the planner, the grounding, and the executor. **The challenge makes you the adversary of your own planner.** Your job is to find the instructions and worlds that make an LLM emit *plausible-but-ungrounded* plans — hallucinated objects, impossible orderings, unsafe actions — and then prove your validator catches every class, before a motor turns.

## Index

1. **[Challenge 1 — The ungrounded plan](challenge-01-ungrounded-plan.md)** — engineer instructions/worlds that elicit each class of ungroundedness from the planner (hallucinated referent, precondition/ordering violation, unsafe/irreversible action, infeasible-given-affordances), measure how often the raw LLM produces them, and prove your validator + repair loop catches each. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the capstone safety case (Week 41), where you must show that a language-driven robot cannot execute an ungrounded or unsafe plan. The skill — adversarially probing an LLM planner until you know exactly how it goes wrong, and proving your runtime grounding catches it — is exactly what separates an engineer who "got the planner demo working" from one who can sign a safety case that says "the LLM proposes; nothing ungrounded ever reaches the actuators, and here is the evidence."
