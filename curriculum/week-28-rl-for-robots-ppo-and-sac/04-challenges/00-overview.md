# Week 28 — Challenges

The exercises drill the algorithms. **The challenge makes you the reward engineer** — the person who has to look at a policy that's "winning" and realize it's cheating. Reward hacking is not a beginner mistake you grow out of; it's a permanent property of optimization, and catching it is the single most valuable RL skill on a robot team.

## Index

1. **[Challenge 1 — The reward-hacking bestiary](./challenge-01-reward-hacking-bestiary.md)** — you're given a reach task with three subtly broken reward functions. Each produces a *rising reward curve* and *wrong behavior*. Diagnose each exploit from the rollout (not the curve), name it against the Lecture 2 §3.3 catalogue, and rewrite the reward — using potential-based shaping where it belongs — so the policy learns the task you meant. (~90 min)

Challenges are optional for passing the week, but this one is the best possible preparation for the Phase 4 midterm (Week 32), where you defend a *learned-policy stack* to a panel and the first question is always "how do you know your policy is doing the task and not gaming the reward?" This challenge *is* that conversation, rehearsed. The engineer who can watch a rollout and name the exploit in two minutes is the one whose policies actually ship.
