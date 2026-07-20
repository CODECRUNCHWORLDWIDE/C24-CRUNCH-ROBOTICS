# Week 32 — Challenges

One challenge this week, and it is the bridge between the exercises and the second-midterm review. The exercises gave you the leash: a constraint set, a predictive safety filter, and a three-rejection fallback switch with an intervention meter. The challenge makes you **defend** that leash the way you will defend it to the panel on review day — live, against the rubric, to someone who did not build it and will not extend you the benefit of the doubt.

| # | File | What you build | Est. time |
|---|------|----------------|-----------|
| 1 | [challenge-01-defend-the-stack.md](./challenge-01-defend-the-stack.md) | A dry run of the second-midterm architecture review: defend your learned-policy stack against the five-part rubric to a peer panel, with the safety filter and fallback firing live, and the intervention-rate breakdown as your headline number. | ~2h |

## Why this is the right challenge for Week 32

The Week 32 milestone is graded twice — once as the mini-project (the wrapped policy, measured) and once as the **second-midterm architecture review**, a live panel session that is a hard gate (10% of the track). The most common way to fail the review is not a weak stack; it is a stack you cannot *defend* — you built it, it works, but when the panel asks "show me an action get rejected" or "what's your intervention rate, and what does the breakdown tell you?", you don't have the live demonstration or the number. This challenge rehearses exactly that conversation, so review day is a confirmation, not a discovery.

## How challenges differ from exercises

Exercises are guided — they hand you the structure and most of the code. A challenge hands you a spec and acceptance criteria and expects you to assemble the defense yourself from your own components. There is no starter file. You reuse your Exercise 1 constraint set, your Exercise 2 filter, your Exercise 3 fallback + meter, your best policy, and your hazard-log update — and you wire them into a *live, narratable defense* of the architecture.

The central test, like the midterm itself, is whether a panel that did not build your stack can watch it run, watch the leash fire, read your numbers, and sign off — or send you back to the artifact that didn't hold up. If you cannot make the filter reject an action *on demand* in front of them, or you cannot state your intervention rate and read its breakdown, you have a gap to close before review day. Better you find it rehearsing with a peer this week than the panel finds it live.
