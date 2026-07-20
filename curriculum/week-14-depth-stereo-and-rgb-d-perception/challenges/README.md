# Week 14 — Challenges

The exercises drill the mechanics. **The challenge makes you the on-call perception engineer.** You're handed a depth stream that's "mostly fine" but producing bad decisions downstream, and you have to find *why* — three different depth failures, each with a different signature, none of them an exception or an error log.

## Index

1. **[Challenge 1 — Diagnose three depth failures on a live stream](challenge-01-diagnose-three-depth-failures.md)** — a harness publishes a depth stream with three planted faults across three failure classes: a glass/specular hole treated as free space, a flying-pixel skirt at object edges, and a `16UC1`-vs-`32FC1` unit bug. Identify each from its signature, explain the physics or the encoding behind it, and prescribe the fix. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Week 16 midterm, where you defend your perception stack to a panel. The reviewer will point at your point cloud and ask "what here is real, and what did the camera invent — and how would you know?" This challenge *is* that question, rehearsed. The skill — reading a depth image you didn't produce and naming what's fabricated in under five minutes — is exactly what separates a junior who "set up the camera" from a senior who can tell a flying pixel from a real obstacle at 3 a.m.
