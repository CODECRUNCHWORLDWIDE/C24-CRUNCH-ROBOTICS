# Week 38 — Resources

Every resource here is **free**. The grounded-planning papers are on arXiv; Llama 3.1, Ollama, vLLM, and the constrained-decoding libraries are open. No paywalled books are linked.

This week bridges to **C23 (Crunch Agents)** — if you have your C23 notes on tool use, structured output, and grounding, keep them open; this week is those ideas wired to a robot.

## Required reading (work it into your week)

- **SayCan — "Do As I Can, Not As I Say: Grounding Language in Robotic Affordances"** — the foundational grounded-planning paper; read the Say×Can decomposition carefully:
  <https://say-can.github.io/> · paper: <https://arxiv.org/abs/2204.01691>
- **Code as Policies — "Language Model Programs for Embodied Control"** — the LLM emits *code* that calls a skill API; the alternative to a flat skill sequence:
  <https://code-as-policies.github.io/>
- **Inner Monologue — "Embodied Reasoning through Planning with Language Models"** — closed-loop re-planning: the LLM consumes feedback (skill success/failure, scene changes) and re-plans:
  <https://innermonologue.github.io/>
- **Ollama** — run Llama 3.1 8B locally with one command; structured/JSON output and the Python client:
  <https://ollama.com/> · structured outputs: <https://ollama.com/blog/structured-outputs>
- **GBNF grammars (llama.cpp / Ollama)** — constrain generation to a formal grammar so the LLM emits only valid skill calls:
  <https://github.com/ggerganov/llama.cpp/blob/master/grammars/README.md>

## The papers (skim, don't memorize)

- **ProgPrompt — "Generating Situated Robot Task Plans using Large Language Models"** — prompting an LLM with the skill API as Python-like signatures so it generates grounded plans:
  <https://progprompt.github.io/>
- **Text2Motion / LLM+P** — combining LLMs with classical planners (PDDL) for guaranteed-valid plans; the "LLM proposes, planner verifies" pattern:
  <https://arxiv.org/abs/2302.05128>
- **VoxPoser** — LLMs composing value maps for manipulation; a different grounding mechanism worth knowing:
  <https://voxposer.github.io/>
- **ReAct — "Synergizing Reasoning and Acting in Language Models"** — the reason-act-observe agent loop from C23, the substrate of closed-loop robot planning:
  <https://arxiv.org/abs/2210.03629>

## Constrained decoding & structured output (the ones you'll use)

- **Outlines** — structured generation (JSON schema, regex, grammar) for local LLMs:
  <https://github.com/dottxt-ai/outlines>
- **vLLM guided decoding** (`guided_json`, `guided_grammar`) — serve an 8B model with schema-constrained output:
  <https://docs.vllm.ai/en/latest/features/structured_outputs.html>
- **Pydantic** — define your skill-call schema once and validate the LLM's output against it:
  <https://docs.pydantic.dev/latest/>
- **`jsonschema`** — validate a plan's JSON against a schema if you're not using pydantic:
  <https://python-jsonschema.readthedocs.io/>

## Local LLM deployment

- **Ollama Python client** — `ollama.chat(..., format=schema)` for JSON-constrained output:
  <https://github.com/ollama/ollama-python>
- **vLLM** — high-throughput serving for an 8B planner if you have a GPU:
  <https://github.com/vllm-project/vllm>
- **Llama 3.1 8B model card** — the recommended local planner; tool-use/function-calling support:
  <https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct>
- **llama.cpp** — CPU/GPU inference for GGUF-quantized models with GBNF grammar support:
  <https://github.com/ggerganov/llama.cpp>

## How-to / background

- **Ollama structured outputs guide** — force the model to emit JSON matching a schema:
  <https://ollama.com/blog/structured-outputs>
- **PDDL primer (for the LLM+classical-planner stretch)** — preconditions, effects, the planning formalism:
  <https://planning.wiki/>
- **MoveIt2 / Nav2 skill dispatch** — the motion layer your skills bind to (you have this from weeks 17–26):
  <https://moveit.picknik.ai/main/index.html>

## Talks worth your time (free, no signup)

- **CoRL / RSS language-and-robotics sessions** — the SayCan, Code-as-Policies, and Inner-Monologue talks are all posted free:
  <https://www.corl.org/>
- **Google DeepMind robotics talks** — the grounded-planning lineage from the teams that built it:
  <https://deepmind.google/research/>
- **Your C23 (Crunch Agents) material** — the tool-use, structured-output, and grounding lectures are the direct prerequisite; re-watch the tool-use one.

## Tools you'll use this week

- **Ollama** (or vLLM) running **Llama 3.1 8B** — the local planner LLM.
- **A grammar / JSON schema** (GBNF, Outlines, or `guided_json`) — to constrain the planner's output to valid skill calls.
- **Pydantic / jsonschema** — to validate plans against the skill-call schema.
- **Your skill stack** — MoveIt2 grasp, the Week-37 `crunch_vla` node, the Week-32 fallback, the BT.
- **`time.perf_counter()`** — to measure the planner's seconds-scale latency (and confirm it's fine because planning is infrequent).

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **LLM-as-planner** | Using a language model to decompose a task into a sequence of skills, not to emit motor commands. |
| **Skill** | A parameterized, composable robot capability with a precondition, an effect, and a typed signature (`grasp(object)`). |
| **Skill library** | The set of skills the planner may use — its "API surface" (the C23 tool-use pattern). |
| **SayCan** | Grounded planning = Say (LLM: what's useful) × Can (affordance: what's possible); act on the product. |
| **Affordance** | How feasible a skill is for the robot *right now* (reachable? object present?). |
| **Grounding** | Tying a plan's symbols to the real world: the objects exist, the skills apply, the preconditions hold. |
| **Constrained decoding** | Forcing the LLM to emit only output matching a grammar/schema — well-*formed* by construction. |
| **GBNF** | A grammar format (llama.cpp/Ollama) for constraining generation. |
| **Guided JSON** | vLLM/Outlines feature forcing output to match a JSON schema. |
| **Validation** | Checking a (well-formed) plan is also well-*founded*: skill exists, args typed, objects real. |
| **Plan repair** | Re-prompting the LLM with the validation errors so it fixes an ungrounded plan. |
| **Closed-loop re-planning** | Re-planning when a skill fails or the world changes mid-plan (Inner Monologue). |
| **Precondition / effect** | What must be true before a skill runs / what it makes true after. |
| **TAMP** | Task And Motion Planning — the high-level (task) + low-level (motion) planning split. |
| **Human-confirmation gate** | A required human approval before an irreversible/high-risk skill executes. |

---

*If a link 404s, please open an issue so we can replace it.*
