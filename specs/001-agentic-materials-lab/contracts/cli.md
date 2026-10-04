# CLI Contract: Agentic Materials Discovery Lab

The project's user-facing interface is three experiment entrypoints (plus pytest). All write
artifacts under `results/` and `records/`. Exit code 0 on success; non-zero with a clear
stderr message on failure.

## `python experiments/run_baselines.py`

Runs the non-agentic arms.

| Flag | Type | Default | Meaning |
|---|---|---|---|
| `--seeds N` | int | 10 | number of seeds (≥10 for final numbers) |
| `--budget N` | int | 300 | total evaluations budget |
| `--rounds N` | int | 6 | rounds per run (batch = budget // rounds) |
| `--pool N` | int | 15000 | subsample size |
| `--gap-min F` / `--gap-max F` | float | 1.0 / 2.0 | target window (eV) |
| `--ehull-max F` | float | -1 (disabled) | optional stability filter (eV/atom); set ≥0 (e.g. 0.1) to enable |
| `--arms` | csv | `random,greedy,uncertainty` | subset allowed |
| `--quick` | flag | off | 2 seeds × tiny pool for smoke tests / fresh-clone check |
| `--out DIR` | path | `results/` | output directory |

**Outputs**: `<out>/baseline_<arm>.csv` (columns: arm, seed, round, evaluations, cumulative_hits,
rmse) and `<out>/baseline_random.png` (mean ± std hit curve). Random arm's overall hit rate MUST
≈ top-set fraction (printed to stdout as a sanity line).

## `python experiments/run_agentic.py`

Runs one or more seeds of the Omnigent-orchestrated loop.

| Flag | Type | Default | Meaning |
|---|---|---|---|
| `--seeds N` | int | 1 | seeds evaluated (10 for final numbers) |
| Common flags `--budget --rounds --pool --gap-min --gap-max --ehull-max` | as above | as above | as above |
| `--refutation-demo` | flag | off | run the fixed-seed engineered refutation scenario, trace → `records/refutation_example.jsonl` |
| `--no-analysis` | flag | off | ablation arm: analysis feedback disabled |
| `--use-cache DIR` | path | `cache/` | LLM/API cache location |
| `--out DIR` | path | `results/` | output directory |

**Outputs**: `<out>/agentic.csv` (same columns as baselines plus `strategy`), or
`<out>/ablation.csv` under `--no-analysis`; appends handoffs to `records/research_log.jsonl`.
Exits non-zero if a handoff fails schema validation or the workflow cannot start.

## `python experiments/analyze_results.py`

Reads all result CSVs and produces the report artifacts.

| Flag | Type | Default | Meaning |
|---|---|---|---|
| `--results DIR` | path | `results/` | input CSV directory |

**Outputs**: `results/summary.csv` (per arm: seeds, evals-per-hit-milestone (5/10/15/20) mean±std, total
hits-at-budget mean±std, speedup vs random mean±std, strategy switches) and
`results/curves.png`. All reported numbers in the README originate ONLY from
`results/summary.csv` (constitution Principle I).

## `pytest -q`

Runs `tests/test_oracle.py`, `tests/test_schemas.py`, `tests/test_strategies.py`. All MUST
pass before any results are considered reportable.

## Workflow config (`omnigent/workflow.yml`, informational contract)

Declares agents, allowed tools per agent (mirroring `policies/tool_permissions.yaml`), handoff
edges (Literature→Insight→Planner→Runner→Analysis→Record; Safety observes all), and the
approval hook for the three gated actions. Validated by Omnigent's own loader; additionally
checked in CI-style validation that permitted tool lists match the policy file exactly.

## LLM provider environment (`src/llm.py`)

`run_agentic.py` routes Insight hypothesis generation and Planner rationale text through
`llm.complete(...)`, which is cache-first (`cache/llm/`, key = sha256(agent|model|seed|prompt)).
The provider is selected entirely by environment:

| Variable | Values / default |
|---|---|
| `LLM_PROVIDER` | `engine` (default; deterministic, no network) \| `openai` \| `anthropic` |
| `LLM_MODEL` | model name, required for real providers |
| `LLM_BASE_URL` | endpoint override; `openai` defaults to `https://api.openai.com/v1`, `anthropic` to `https://api.anthropic.com` |
| `LLM_API_KEY` | shared key; falls back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` |
| `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` | provider-specific base URL overrides |

`openai` accepts any OpenAI-compatible `/chat/completions` endpoint (OpenAI, Databricks
model serving, vLLM, Ollama, Azure with adapter) **or** the OpenAI Responses API — set
`LLM_BASE_URL` to a `.../responses` endpoint (e.g. OpenCode Zen
`https://opencode.ai/zen/v1/responses`) and it is detected automatically. Strategy decisions, budgets, and
refutation detection stay deterministic in all modes; only hypothesis text and planner
rationale come from the model. Cached entries record the producing `model` so engine and
real-provider outputs are never conflated.
