# Exercise 1 — The Package Checklist

**Type:** Audit, hands-on.
**Estimated time:** ~40 minutes.
**Outcome:** A verified, complete defense package — every required deliverable committed, navigable, and ready for the panel (Lecture 1 §1).

A missing deliverable is a fail before you say a word. This exercise is the audit that catches the deliverable that is "basically done" but not actually committed, not linked from the README, or not playable. Run it early in the week; you will find at least one gap.

---

## The checklist

For each item, the bar is **committed, navigable from the top-level README, and verified** (you opened/played/ran it, not just "it exists somewhere").

### The seven required deliverables (from the capstone spec)

- [ ] **Integrated repo** — public, GPL-3.0, everything from week 1 forward, with a top-level README that routes a reader to every other deliverable. *Verify:* open the README on GitHub; can a stranger find the autonomy stack, the safety case, and the videos in under a minute?
- [ ] **Mermaid architecture diagram** — in-repo source *and* a PNG export, showing the full stack including the safety layer. *Verify:* it renders on GitHub and a peer can read it (Week 47 §2).
- [ ] **Two videos** — sim + real (Path A) or two clearly-labelled sim runs (Path B), each ≤ 5 min with voiceover, result shown first. *Verify:* both play; both are labelled; the labels are unambiguous.
- [ ] **Signed safety case** — 8–15 pages, hazard list + FMEA + mitigations + validation plan + residual risk, peer-signed. *Verify:* the peer signature is present; the residual-risk section is non-empty.
- [ ] **Two chaos-drill postmortems** — sensor-dropout and doorway-deadlock, each 2–4 pages, each passing the rubric, bag-cited timelines. *Verify:* both present; both have a root-cause-vs-factors split and owned action items.
- [ ] **Operator-dashboard recording** — 3 min, Foxglove streaming pose/costmap/policy/safety/load, ideally a chaos recovery. *Verify:* it plays; the safety-filter status panel is visible.
- [ ] **Polished portfolio** — three projects under `portfolio.md` (Week 47). *Verify:* `portfolio.md` exists and states the progression; all three READMEs pass the Week 47 scorer.

### Plus

- [ ] **Public retro** — the one-page "what I'd do differently" (Lecture 2 §6). *Verify:* it has real, specific regrets with transferable lessons, not platitudes.

---

## What you must produce

`package-audit.md`, with the checklist above filled in (checked/unchecked), and for each *unchecked* item, the exact gap and your plan to close it before Saturday's defense.

## Acceptance criteria

- [ ] Every item is marked, with a verification note (what you opened/played/ran to confirm it), not just a checkmark.
- [ ] Every gap has a concrete, dated plan to close it this week.
- [ ] The integrated repo's top-level README routes to all seven deliverables (a stranger could navigate it).
- [ ] If any deliverable is missing, it's flagged as the week's highest-priority work *ahead of polish*.

---

## Hint

The deliverables that are most often "done but not really":

- **The top-level README as a router.** You have forty-eight week-folders; without a top-level README that maps them, the repo is a fail of legibility even if every folder is excellent (Lecture 1 §3).
- **The PNG export of the diagram.** The Mermaid source renders on GitHub, but the spec wants a PNG too. Export it now.
- **The video labels (Path B).** "sim run" and "sim-hardened run" must be *unambiguously* labelled, or the panel can't tell which is which and the deliverable doesn't count.
- **The retro's specificity.** "I'd manage time better" is a platitude; "I'd build the latency budget in week 1, not week 39" is a real lesson. Rewrite any platitude.

Assembling the package is itself revealing: the gaps you find are the gaps the panel would have found, and finding them now means fixing them is cheap.
