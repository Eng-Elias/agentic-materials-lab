# Research: Agentic Materials Discovery Lab

Phase 0. Every technical choice below resolves a decision needed by the Technical Context; no
open NEEDS CLARIFICATION remain.

## R1: JARVIS data loading

- **Decision**: Load `dft_3d` via `from jarvis.db.figshare import data; df = pd.DataFrame(data('dft_3d'))`;
  keep the loader call behind a thin function in `src/data.py` and cache the raw frame to
  disk (pickle/parquet) after first download.
- **Rationale**: `jarvis.db.figshare.data(dataset_name)` is the documented jarvis-tools loader;
  caching avoids repeated ~GB downloads across ≥10 seeds.
- **Alternatives considered**: `jarvis.db.figshare.get_db_info` + manual CSV fetch (more moving
  parts); `jarvis.core.atoms` structure-featurization path (rejected — constitution Principle
  VIII: no structure-based models).
- **Verify-at-install note**: exact field names (`optb88vdw_bandgap`, `ehull`, `atoms`,
  `jid`, `formula`) are confirmed after install per the setup checklist; the loader function
  is the only code touching the raw frame so adaptation cost is one file.

## R2: Composition featurization

- **Decision**: matminer `ElementProperty.from_preset('magpie')` with `featurize_dataframe`
  over compositions parsed with pymatgen; fallback to hand-built element-property statistics
  (mean/std/range of electronegativity, atomic mass, group, Mendeleev number per constituent)
  computed with jarvis-tools' element-list CSV if matminer fails to install.
- **Rationale**: Magpie is fast, structure-free, and is the plan's sanctioned choice; the
  fallback preserves the identical feature-pipeline interface.
- **Alternatives considered**: SOAP/structure descriptors and GNN embeddings (rejected —
  unconstitutional scope); hand features as primary (kept as Plan B only).

## R3: Surrogate model and uncertainty

- **Decision**: `sklearn.ensemble.RandomForestRegressor` (n_estimators=200,
  `random_state=seed`); prediction = mean of per-tree predictions, uncertainty = standard
  deviation across trees. Retrain after every round on revealed data. LightGBM kept as drop-in
  alternative behind the same `fit/predict(X) -> (mean, std)` interface.
- **Rationale**: Native, trustworthy epistemic uncertainty without extra dependencies;
  fast enough for 20k rows × 6 rounds × 10 seeds.
- **Alternatives considered**: LightGBM quantile models (fine but duplicate work as primary);
  GP regression (too slow at 10-20k pool); deep ensembles (out of scope).

## R4: Label hiding / oracle

- **Decision**: `oracle.py` `Oracle` class constructed with the full label array; labels
  stored as a private attribute with name-mangling; only `reveal(ids) -> np.array` returns
  values, decrementing budget and rejecting duplicates via a revealed set. `budget_remaining()`
  and `hits_found()` expose aggregates only. Tests introspect public surface for leakage.
- **Rationale**: single access path is the constitution's hard requirement; Python privacy by
  convention is sufficient because adversarial access is out of threat model — the leak risk is
  accidental plumbing, covered by the leak test.
- **Alternatives considered**: encrypting labels (overkill); subprocess isolation (complexity).

## R5: Strategy scoring (Planner)

- **Decision**: deterministic scoring core in Python — for each candidate strategy
  (exploit / explore / hybrid-UCB / hypothesis_test) compute expected learning (anticipated
  information gain / hit probability proxy), feasibility (batch fits budget), cost — then let
  the Omnigent Planner agent reason over these scores and emit a Pydantic-validated choice
  with rationale and rejected alternatives. Strategy selection inside baseline arms is the
  corresponding fixed policy without the agent.
- **Rationale**: keeps numerics honest and cheap while preserving agent decision-making for
  the orchestration score; identical baseline comparison possible.
- **Alternatives considered**: fully LLM-chosen raw candidate ids (unverifiable, leak-risky,
  slow); fully deterministic planner without agent (fails orchestration intent).

## R6: Literature agent data source

- **Decision**: OpenAlex REST API (`/works?search=...`) as primary, arXiv API (`export.arxiv.org/api/query`)
  as backup; responses serialized to `cache/lit/` keyed by query hash; claims extracted only
  from cached responses, each carrying title + DOI or URL + year.
- **Rationale**: both are keyless, documented, JSON-returning APIs; caching satisfies the
  multi-seed cost constraint and the verify-citations requirement.
- **Alternatives considered**: Europe PMC (biomedical skew, not needed); web scraping
  (unreliable, unverifiable); LLM-from-memory citations (forbidden: hallucination risk).

## R7: Handoff contract format

- **Decision**: Pydantic v2 models in `src/schemas.py` — `Citation`, `Hypothesis`
  (literal `AGENT-GENERATED` label field), `ExperimentSpec` (with `rejected_alternatives`),
  `RunResult`, `AnalysisVerdict`, `Handoff`. Every inter-agent message validates with
  `model_validate`; failures raise and are logged as rejected.
- **Rationale**: plan-mandated; Pydantic gives free JSON Schema export for the contracts/
  artifact and strict validation in one dependency.
- **Alternatives considered**: dataclasses + jsonschema separately (two sources of truth);
  raw dicts (violates constitution Principle VI).

## R8: Omnigent integration boundary

- **Decision**: Omnigent orchestration declares the 7 agents, tools, handoffs, and policies;
  tools wrap plain-Python functions from `src/` (reveal, query_surrogate, train_surrogate,
  search_lit, append_record, request_approval). Exact Omnigent workflow syntax is taken from
  its current docs/cli help at implementation time and pasted into `omnigent/workflow.yml`.
- **Rationale**: Omnigent specifics evolve (plan explicitly says to read its docs first); the
  science core stays plain-Python so at-Risk surface is orchestration only (Risk table #1).
- **Alternatives considered**: in-process loop calling LLM via OpenAI client only (rejected —
  30% scoring weight requires Omnigent in the live path); LangGraph (out of scope).

## R9: Caching of LLM outputs

- **Decision**: file cache keyed by `(agent, model, prompt-hash, seed-bucket)` storing exact
  JSON completions; `--no-cache` opt-out. The refutation-scenario round prompts are keyed
  per fixed demo seed so the moment is reproducible.
- **Rationale**: 10-seed sweeps are otherwise too slow/costly in hours 14-19 (Risk table #4).
- **Alternatives considered**: sqlite cache (fine but unnecessary); no cache (rejected).

## R10: Results computation

- **Decision**: `experiments/analyze_results.py` reads per-arm CSVs (`results/*.csv`), computes
  per-seed hit curves, evaluations-to-50%-of-top-set, speedup mean±std across seeds,
  surrogate RMSE per round from logged run results, and writes `results/summary.csv` +
  `results/curves.png`. README embeds only numbers from `summary.csv`.
- **Rationale**: single source of measured truth satisfies Principle I.
- **Alternatives considered**: notebook analysis (less reproducible); in-run ad-hoc reporting
  (drift risk).
