# Week 23 — Challenges

The exercises drill the mechanics — FK, IK, a pose goal. **The challenge makes you the engineer who knows the arm's limits before the planner does.** You're handed an arm and asked the question every manipulation project eventually asks: *where, exactly, can this hand go, and where does it get unreliable?* That is a reachability map, and building one teaches you to read a workspace the way a senior engineer reads a costmap.

## Index

1. **[Challenge 1 — Build a reachability map of the arm's workspace](./challenge-01-reachability-map.md)** — sample thousands of joint configurations, run FK to find where the hand reaches, score each pose by manipulability, and produce a reachability map that shows both the *boundary* (where IK starts failing) and the *singular zones* (where the arm is reachable but unreliable). Then validate it against MoveIt2's own IK success rate. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 milestone in Week 24, where your composed Nav2 + MoveIt2 robot must reach a pose on a table — and the first question a reviewer asks is "how did you know that pose was reachable?" The reachability map *is* that answer. The skill — knowing your arm's envelope cold, including the unreliable interior near singularities — is exactly what separates a junior who "got MoveIt2 to plan once" from a senior who can promise an arm will reach a shelf before the robot is built.
