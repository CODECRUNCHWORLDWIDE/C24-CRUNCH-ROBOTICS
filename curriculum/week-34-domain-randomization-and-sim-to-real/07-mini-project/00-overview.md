# Mini-Project — `crunchbot_domain_rand`: A Config-Driven Randomization Layer + Gap-Closure Evaluator

> Build a reusable, simulator-agnostic domain-randomization layer — a config, a sampler, and a thin apply-to-sim adapter — plus a gap-closure evaluator that trains/evaluates nominal-vs-randomized and emits the honest gap number with its sanity check. So "did randomization help?" is answered by a regenerable table, not a claim.

This is the artifact that turns the challenge's one-off result into the standing sim-to-real tool of your portfolio. It extends last week's `crunchbot_sim_compare` (hold robot fixed, vary world, measure) into "hold robot fixed, *randomize* the world, measure the gap." It is the evidence-generator the Phase 5 milestone and the capstone safety case lean on, and the config you build here is the one you'd point at the capstone task in Week 40.

**Estimated time:** ~11 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** **Week 40** stands up the capstone system in sim; this harness is how you'd produce a credibility number for any sim-trained capstone component. **Week 41**'s safety case cites a gap-closure result as evidence the learned policy was hardened against distribution shift. The config-driven, sim-agnostic design means the capstone task is a new config, not a rewrite.

**Suggested order of work (so you don't get stuck):**

1. Start with `randomizer.py` — lift the Exercise-2 `DomainRandomizer`, get `test_randomizer.py` green (in-range, reproducible, coverage). Pure logic, no sim, no GPU — do it first.
2. Build `gap.py` next — lift the Exercise-3 gap math + sanity check, get `test_gap.py` green including the contaminated-case flag. Still no sim.
3. Now `apply.py` — the only sim-aware file. Wire one backend (Gz reset on Path B, Isaac event terms on Path A).
4. Run the *nominal* and *randomized* trainings, evaluate on the held-out world, feed counts to `gap.py`, generate `reports/gap.md`.
5. Add the ADR controller and `test_adr.py`, then polish docs and tests.

The deliberate order keeps the sim-independent core (steps 1–2) testable *before* you touch a simulator, so when something breaks in step 3–4 you know it's the sim glue, not the logic. That separation is the whole reason the layer is designed this way — use it.

---

## What you will build

A small Python package `crunchbot_domain_rand` with three deliverables:

1. **`crunchbot_domain_rand/randomizer.py`** — the simulator-independent core: the `DomainRandomizer` (from Exercise 2, hardened) plus an optional **ADR** controller that widens ranges on a success signal. Pure logic, unit-tested, no simulator import.
2. **`crunchbot_domain_rand/apply.py`** — the thin **adapter** that applies a sampled parameter dict to a concrete simulator on reset: an Isaac Lab event-term path (Path A) and a Gz Sim episode-reset path (Path B), behind a common `apply(params, env)` interface. This is the *only* sim-specific file — the rest of the package never imports a simulator.
3. **`crunchbot_domain_rand/gap.py`** — the gap-closure evaluator (from Exercise 3, formalized): given eval counts for nominal/randomized on nominal/held-out worlds, compute the gap, the Wilson CIs, and the sanity verdict; emit a committed `reports/gap.md`.

By the end you have a repo of ~350–450 lines that runs `domain-rand sample --config grasp.yaml` (inspect a draw), wires into your training loop via `apply()`, and `domain-rand gap --results results.json` (emit the report).

---

## Why a layer and not inline randomization

You *could* sprinkle `np.random.uniform` calls through your env reset. Don't — not as the source of truth. A config-driven layer gives you:

- **Reproducibility.** The randomization is a committed config + a seed, regenerable. "We randomized friction 0.4–1.2" is in a file, not buried in env code.
- **Sim-agnosticism.** The sampler and the gap evaluator never import a simulator; only `apply.py` does. Moving from Gz Sim to Isaac Lab is swapping the adapter, not rewriting the randomization — the same separation that made Week 33's comparison harness portable.
- **Honest evaluation built in.** The gap evaluator *requires* you to supply nominal-on-held-out, randomized-on-held-out, and the nominal-world sanity cells — so you can't accidentally report a gap without the sanity check that catches contamination.

---

## Package layout

```
crunchbot_domain_rand/
├── pyproject.toml
├── crunchbot_domain_rand/
│   ├── __init__.py
│   ├── randomizer.py       # DomainRandomizer + ADR controller (sim-independent)
│   ├── apply.py            # apply(params, env): Isaac event-term OR Gz reset (the ONLY sim file)
│   ├── gap.py              # gap-closure metric, Wilson CI, sanity check, report
│   └── cli.py              # `domain-rand` entry point (sample | gap)
├── configs/
│   ├── grasp.yaml          # the manipulation recipe (Exercise 1 Part A)
│   └── nav.yaml            # the navigation recipe (Exercise 1 Part B)
├── reports/                # generated, committed gap reports
└── tests/
    ├── test_randomizer.py  # in-range, reproducible, coverage (the Exercise-2 checks, formalized)
    ├── test_adr.py         # ranges widen only after the success threshold is cleared
    └── test_gap.py         # gap math + the sanity check flags a contaminated case
```

---

## Deliverable 1 — `randomizer.py` (the core + ADR)

Lift `DomainRandomizer` from Exercise 2 and add an **ADR controller**:

```python
class ADRController:
    """Widens each parameter's range as the policy clears a success threshold.

    Start narrow (near nominal); on each evaluation, if success >= threshold on the
    current ranges, widen by a step; if success drops below a floor, narrow back.
    This is Dactyl's curriculum-of-distributions (Lecture 2 Part 2.2) made concrete.
    """
    def __init__(self, base_config, widen_step=0.1, success_threshold=0.7): ...
    def current_config(self) -> dict: ...           # the (possibly widened) ranges now
    def update(self, success_rate: float) -> None:  # widen/narrow based on competence
        ...
```

`test_adr.py` must prove: ranges **do not** widen below the threshold, **do** widen above it, and never widen past the configured ceiling (the over-randomization guard). The randomizer core stays sim-independent — `grep -rn "isaac\|gz\|omni" crunchbot_domain_rand/randomizer.py` must be empty.

---

## Deliverable 2 — `apply.py` (the only sim-specific file)

A single function behind which both simulators live:

```python
def apply(params: dict, env, backend: str) -> None:
    """Apply one sampled world to the sim on reset.

    backend == "isaac": set Isaac Lab event-term values per parallel env (mass, friction,
                        material, lighting) from `params`.
    backend == "gz":    set Gz Sim model params (friction/mass via SDF/service), swap
                        textures, reposition lights/camera, before the episode runs.
    The policy and training loop never call this directly — the env reset does.
    """
```

The discipline: **this is the only file that imports a simulator.** If `randomizer.py` or `gap.py` import `isaacsim`/`gz`, you've broken the layer's portability. The grader greps for exactly this.

---

## Deliverable 3 — `gap.py` (the honest evaluator)

Formalize Exercise 3: take the four eval cells (nominal/randomized × nominal/held-out worlds), compute `gap_closed`, the Wilson CIs, and the **sanity verdict**, and write `reports/gap.md`. It must **refuse to declare a win** when the sanity check flags contamination (randomized better on both worlds) — print SUSPECT and exit non-zero, so a leaky held-out world can't silently ship as a result.

```
=== crunchbot_domain_rand: gap report ===
task: reach    held-out world: real_style_A    n: 100
nominal-trained     held-out: 31/100 (31%)  CI[23,41]
randomized-trained  held-out: 84/100 (84%)  CI[76,90]
GAP CLOSED: +53 pts
(sanity) nominal world: nominal 92% | randomized 88%   -> verdict: OK
exit 0
```

---

## Rules

- **You may** read the Tobin/Dactyl papers, the Isaac Lab randomization docs, the Gz Sim docs, and your own exercise solutions.
- **You must not** let `randomizer.py` or `gap.py` import any simulator. Only `apply.py` is sim-aware. (`grep -rn "import isaacsim\|import gz\|import omni" crunchbot_domain_rand/randomizer.py crunchbot_domain_rand/gap.py` must be empty.)
- **You must not** report a gap-closure win when the sanity check says SUSPECT — `gap.py` exits non-zero in that case. A leaky held-out world is a failed experiment, not a result.
- Every numeric randomization sample must stay inside its declared range (the Exercise-2 guard), enforced by a test.
- Python 3.12, NumPy + `pyyaml`. No third-party DR libraries (the point is to understand the layer).

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-34-crunchbot-domain-rand-<yourhandle>`.
- [ ] `randomizer.py` and `gap.py` import **no** simulator; only `apply.py` does (grep-clean).
- [ ] `domain-rand sample --config configs/grasp.yaml` prints a validated sampled world; `--config configs/nav.yaml` prints the (different) nav recipe's world.
- [ ] `domain-rand gap --results results.json` emits `reports/gap.md` with the gap, CIs, and sanity verdict, and **exits non-zero on a SUSPECT (contaminated) result**.
- [ ] ADR widens ranges only after the success threshold and never past the ceiling (tested).
- [ ] `tests/` pass: `test_randomizer.py` (in-range/reproducible/coverage), `test_adr.py` (widen logic), `test_gap.py` (gap math + sanity flag).
- [ ] A `README.md` with the config schema, the two recipes, the run commands, and a paragraph on why the layer is sim-agnostic.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Randomizer correctness** | 20 | In-range/reproducible/coverage; the two recipes match Exercise 1's exposure logic. |
| **Sim-agnostic layering** | 20 | Only `apply.py` is sim-aware; grep-clean core; adding a sim is a new adapter. |
| **ADR** | 15 | Widens on success, narrows on failure, respects the ceiling; the curriculum is real. |
| **Honest gap evaluation** | 25 | Gap + CIs + sanity verdict correct; refuses to declare a win on a contaminated held-out world (non-zero exit). |
| **Tests** | 15 | Randomizer, ADR, and gap logic all tested; green. |
| **Docs & hygiene** | 5 | Clear README; no checkpoints/blobs committed; sensible commits. |

**90+** is portfolio-grade and ready to point at the capstone task in Week 40. **70–89** works but has sim leakage in the core or a soft sanity check. **Below 70** means the gap evaluation isn't honest-by-construction — fix the sanity-gate first.

---

## How this connects to the rest of C24

- **It extends Week 33's `crunchbot_sim_compare`.** Last week's harness held the robot fixed and varied the *simulator* to measure throughput/fidelity. This harness holds the robot fixed and *randomizes the world* to measure the *gap*. Same "hold robot fixed, vary something, measure" spine; a different something. If you built last week's harness cleanly, this one reuses its metric-capture instincts.
- **Week 40 (Phase 5 milestone)** stands up the capstone system in sim. Any sim-trained capstone component — the VLA, an RL controller — gets its credibility from a gap-closure number, and this harness is how you produce one for the capstone task (a new config, not a rewrite).
- **Week 41 (safety case)** cites sim-to-real evidence. A safety reviewer asks "you trained this in sim; why is it safe to deploy?" The honest answer pairs a gap-closure result ("randomization closed N points") with the acknowledgment that the safety filter still matters because randomization narrows but never erases the gap. This harness produces the first half; the safety case supplies the second.

## Common pitfalls (read before you start)

The mistakes that cost the most time on this project:

- **Sim leakage into the core.** If `randomizer.py` or `gap.py` imports a simulator, the whole portability premise is broken. Only `apply.py` is sim-aware; the grader greps for exactly this.
- **A contaminated held-out world.** The single most damaging error: reusing a training parameter in the "held-out" world inflates the gap. The sanity gate catches the symptom (randomized beats nominal on both worlds), but the fix is to design the held-out parameters disjoint from training *before* you train.
- **Reporting a gap without the sanity line.** A bare "+53 pts" is unverifiable. The report must show the nominal-world sanity cells, and `gap.py` must refuse (non-zero exit) to declare a win when the sanity check flags contamination.
- **Out-of-range samples.** A randomizer that occasionally emits a value outside its declared range silently poisons training. The in-range test is not optional.
- **Confusing conditions with the task.** Randomizing the goal or the objective (instead of the world conditions) produces a moving target that looks like over-randomization. Randomize conditions, never the task.

## Stretch goals

- **Family ablation built in.** Add a `--families visual,dynamics` flag so the harness can train/eval each family in isolation and the report attributes the gap closure per family ("visual closed 40 of 53 pts").
- **Latency randomization adapter.** Add `action_delay_ms` handling to `apply.py` for both backends, and show it makes the policy robust to the real-actuator latency that ambushes first-hardware-contact controllers.
- **System-ID centering.** Add a step that takes a measured real parameter (e.g., floor friction from a quick real test) and *centers* the randomization range on it, then show the gap closes further — DR around a measured mean beats DR around a guessed one.
- **CI gate.** A GitHub Action that runs the tests and a tiny synthetic gap evaluation, failing the build if the sanity-gate logic regresses. Your honest-evaluation discipline, enforced.

## What "done" looks like

When this project is finished, you can produce — from a config and a command — the single most important artifact of the entire Sim2Real phase:

```bash
domain-rand gap --results results.json    # emits reports/gap.md, exit 0 if honest
```

and `reports/gap.md` contains a gap-closure number, with its sanity line and confidence intervals, that a safety reviewer or a future employer reads as *evidence* a sim-trained policy will survive contact with reality. The harness *refuses* to call a contaminated result a win (non-zero exit on a flagged sanity check), so the artifact is honest by construction — you literally cannot ship a leaky gap number through it. That "honest by construction" property is what makes this a portfolio piece: it's not just that you ran domain randomization, it's that your evaluation tool *enforces* the discipline that makes the result trustworthy. Pair it with the Week 33 sim-compare harness and you have a two-tool sim-engineering portfolio that demonstrates exactly the rigor a robotics-learning team hires for.

The one-line pitch for the repo README: *"A config-driven domain-randomization layer and a gap-closure evaluator that refuses to report a contaminated result — so every sim-to-real claim it produces is honest by construction."* That sentence, backed by the code, is the artifact.

Build it well, keep it, and point it at the capstone task in Week 40 — the gap-closure number it produces there is part of what makes the capstone defensible.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
