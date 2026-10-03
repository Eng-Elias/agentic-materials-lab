# Tasks: Agentic Materials Discovery Lab

**Input**: Design documents from `/specs/001-agentic-materials-lab/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (handoff.schema.json, cli.md), quickstart.md

**Tests**: INCLUDED — constitution Principle X mandates oracle-leak, schema-validation, and budget-enforcement tests; PLAN.md §13 requires them before any result is trusted.

**Organization**: Foundational science core first (oracle/baselines before agents, per SPECKIT guide §2.2), then one phase per user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify environment, Omnigent, and dataset before any implementation

- [x] T001 Verify JARVIS download works: `python -c "from jarvis.db.figshare import data; import pandas as pd; df=pd.DataFrame(data('dft_3d')); print(len(df), df.columns.tolist())"`; record exact field names (e.g., band-gap and ehull columns) in `docs/DATA_FIELDS.md` since downstream tasks depend on them
- [ ] T002 Omnigent two-agent smoke test: get two Omnigent agents exchanging ONE JSON message shaped like contracts/handoff.schema.json; save the minimal working workflow snippet to `omnigent/smoke/` (pass/fail gate for Phase 6; escalate immediately if failing)
- [x] T003 [P] Create directory skeleton per plan.md: `src/ experiments/ tests/ agents/ policies/ omnigent/ records/ results/ demo/ cache/lit/ cache/llm/ docs/`
- [x] T004 [P] Add `src/__init__.py`, `experiments/__init__.py`, `tests/__init__.py`, `conftest.py` (sys.path bootstrap) and a `.gitignore` section for `cache/`, `records/*.jsonl` exclusion review, and `results/` keep-files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data pipeline, oracle, contracts, and record — MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement `src/data.py`: load `dft_3d` via `jarvis.db.figshare.data` with raw frame cached to `cache/dft_3d.pkl`; filter rows with valid band gap using field names from T001; subsample with fixed `seed` and `pool=15000`; define `top_set` as gap in `[gap_min, gap_max]` (default 1.0-2.0 eV) AND `ehull < ehull_max` when the filter is enabled (disabled by default); print pool size, top-set size, fraction; featurize compositions via matminer `ElementProperty.from_preset('magpie')` with graceful fallback to hand-built element statistics (mean/std/range of electronegativity, atomic mass, group number over constituents); expose `load_pool(...) -> (features_df, labels: pd.Series, top_set: set[str])` — labels MUST NOT appear in `features_df`
- [x] T006 Implement `src/oracle.py`: class `Oracle(labels: pd.Series|dict, budget: int)` storing labels in a name-mangled private attribute; methods `reveal(ids) -> dict[str,float]` (raises `BudgetExceededError` when `len(ids) > budget_remaining`, raises `ValueError` on already-revealed ids, decrements budget, returns ONLY requested values), `budget_remaining()`, `revealed_ids()`, `hits_found(top_set)`; NO public method or attribute returns unrevealed labels or the full label array
- [x] T007 [P] Write `tests/test_oracle.py`: (1) revealing beyond budget raises and leaves budget unchanged, (2) no public attribute/method exposes unrevealed labels (introspect `Oracle` public surface; assert unrevealed ids' values absent from dumps/returns/loggable state), (3) re-revealing an id raises, (4) `reveal([])` is a no-op costing 0 — run against T006 and ensure they FAIL first except where trivially true
- [x] T008 [P] Implement `src/schemas.py` as Pydantic v2 models mirroring contracts/handoff.schema.json exactly: `Citation` (id, claim, source_title, doi_or_url, year, cached_response_id — all required), `Hypothesis` (`label: Literal["AGENT-GENERATED"]` with missing/other value REJECTED, `testable_feature_set` min length 1, `supporting_citation_ids` min length 1), `ExperimentSpec` (`strategy` enum exploit/explore/hybrid/hypothesis_test; `rejected_alternatives` min items 1 with {strategy, reason}; `cost == len(batch_ids)`), `RunResult`, `AnalysisVerdict` (refuted verdict requires evidence + strategy_recommendation + reason), `ApprovalRequest/ApprovalDecision` (`action` enum recommend_for_validation/budget_increase/report_uncited_claim), `Handoff` envelope with run_id, round, from_agent/to_agent enums of the 7 agents + "scientist", discriminated payload union
- [x] T009 [P] Write `tests/test_schemas.py`: malformed handoffs rejected; hypothesis without `AGENT-GENERATED` label rejected; ExperimentSpec without rejected_alternatives rejected; refuted verdict without evidence rejected; full example from PLAN.md §5 validates
- [x] T010 [P] Implement `src/record.py`: append-only JSONL writer to `records/research_log.jsonl` writing {timestamp (ISO-8601), agent, run_id, seed, input_hash (sha256 of canonical JSON input), output, citations}; append-only guarantee (no edit/delete API)
- [x] T011 [P] Centralize run configuration in `src/config.py` (dataclass: seeds, budget=300, rounds=6, pool=15000, gap_min=1.0, gap_max=2.0, ehull_max=None (disabled), output dirs) consumed by all experiment scripts

**Checkpoint**: `pytest -q` runs test_oracle + test_schemas; T001 fields confirmed; science-core primitives exist

---

## Phase 3: User Story 1 - Configure Objective and Measure Discovery Efficiency (Priority: P1) 🎯 MVP

**Goal**: Scientist configures window/budget; random/greedy/uncertainty baselines run over ≥10 seeds with reproducible hit curves and an honest results table

**Independent Test**: `pytest -q` green + `python experiments/run_baselines.py --quick` prints top-set fraction and random hit rate matching it (quickstart Scenario 1/2)

### Tests for User Story 1

- [x] T012 [P] [US1] Write `tests/test_strategies.py` golden-fixture tests: tiny in-memory pool (e.g., 20 ids, hand-set means/stds) asserting exploit picks highest in-window probability, explore picks max std, hybrid-UCB picks max score of the documented formula, each returns exactly `batch_size` unrevealed ids, and strategies never pick revealed ids

### Implementation for User Story 1

- [x] T013 [US1] Implement `src/surrogate.py`: class `Surrogate` wrapping `sklearn.ensemble.RandomForestRegressor(n_estimators=200, random_state=seed, n_jobs=-1)`; `fit(features, labels)` on revealed data only; `predict(X) -> (mean, std)` using per-tree prediction std; `in_window_probability(X, lo, hi)` converting (mean, std) to P(value in window) assuming Gaussian predictive distribution — constituting FR-005's "prediction + uncertainty" interface
- [x] T014 [US1] Implement `src/strategies.py`: functions `exploit(candidates, surrogate_pred, k)`, `explore(candidates, surrogate_pred, k)`, `hybrid_ucb(candidates, surrogate_pred, k, beta=2.0)` (score = in-window probability weighted mean + beta * std over candidates), each taking only UNREVEALED candidate ids and returning exactly k ids; plus `hypothesis_test(candidates, surrogate_pred, hypothesis, k)` selecting ids maximizing predicted separation on the hypothesis's feature set (used by Planner)
- [x] T015 [US1] Implemented `experiments/run_baselines.py`: CLI per contracts/cli.md (`--seeds --budget --rounds --pool --gap-min --gap-max --ehull-max --arms --quick --out`); one seeding round of 50 random ids shared-identically across arms for a seed; arms `random | greedy | uncertainty` loop rounds: train surrogate on revealed data (greedy/uncertainty), pick batch via corresponding strategy (random via `numpy.RandomState(seed)`), `Oracle.reveal`, record row {arm, seed, round, evaluations, cumulative_hits, rmse}; write `<out>/baseline_<arm>.csv`; print sanity line `top_set_fraction=… random_hit_rate=…` (MUST be ≈ equal); `--quick` = 2 seeds, pool 2000, budget 100, rounds 2
- [ ] T016 [P] [US1] Implement `experiments/analyze_results.py`: read `results/*.csv`; compute per arm over seeds: mean±std cumulative-hits curve, evaluations-to-hit-milestones {5,10,15,20} (mean±std, NaN if unreached), hits-at-full-budget (mean±std), speedup N_random/N_agentic at matched hit counts (deferred to US2 sweeps but code path complete); write `results/summary.csv` + `results/curves.png` (mean curve + std shading per arm); assert count of `*.csv` inputs matches expected arm set and refuse to fabricate missing arms as zero (exit non-zero with message)
- [x] T017 [US1] Run (GATE PASSED 2026-10-04: greedy hit rate 18.6% vs random 5.8% ≈ top-set fraction; 20-hit milestone 170 vs 300 evals = 1.76x): `python experiments/run_baselines.py --seeds 10` and inspect: random curve hit-rate sanity, greedy and/or uncertainty MUST beat random — if not, STOP and tune features/model/window now (constitution decision gate), do not proceed to US2

**Checkpoint**: MVP exists: honest oracle + 3 baseline curves + summary.csv (quickstart Scenarios 1-2 pass)

---

## Phase 4: User Story 2 - Watch the Agentic Discovery Loop (Priority: P2)

**Goal**: One complete Omnigent-orchestrated loop with cited literature, labeled hypotheses, strategy comparison with rejected alternatives, budgeted reveals, analysis verdicts, and full logging

**Independent Test**: `python experiments/run_agentic.py --seeds 1` exits 0; `records/research_log.jsonl` shows schema-validated handoffs for Literature→Insight→Planner→Runner→Analysis→Record (quickstart Scenario 3)

- [ ] T018 [P] [US2] Implement `src/tools_lit.py`: `search_openalex(query, cache_dir) -> list[Citation]` and `search_arxiv(query, cache_dir) -> list[Citation]` using requests; response cached to `cache/lit/<sha256(query)>.json`; claims constructed ONLY from cached fields (title, authors, year, doi or id-url); cache hit returns without network
- [ ] T019 [US2] Manual pre-fetch: run tools_lit queries for band-gap predictors (electronegativity difference, s/p-orbital character proxy via average group, mean electronegativity, formation energy relation); verify each citation's DOI/URL resolves; keep cache under `cache/lit/` (record verification list in docs/CITATIONS.md)
- [ ] T020 [P] [US2] Write 7 agent specs `agents/{literature,insight,planner,runner,analysis,record,safety}.md`, each with: decision owned, tools allowed, input schema, output schema (referencing src/schemas.py models by name), rules — content from PLAN.md §4 (Planner MUST record rejected alternatives; Runner MUST NOT exceed budget; Safety gates the three consequential actions)
- [ ] T021 [P] [US2] Write `policies/tool_permissions.yaml` granting: literature→[search_lit], insight→[read_stats, read_lit], planner→[query_surrogate, read_budget], runner→[oracle_reveal, train_surrogate], analysis→[read_results], record→[append_record], safety→[request_approval, recommend_for_validation]; and `policies/approval_rules.yaml` listing exactly the three gated actions with required fields
- [ ] T022 [US2] Implement the Omnigent workflow in `omnigent/workflow.yml` per the syntax validated in T002: declare the 7 agents, tools from `src/`, handoff edges Literature→Insight→Planner→Runner→Analysis→Record with Safety observing/gating, every handoff validated via `schemas.Handoff.model_validate` and logged via `record.append`; declaratively mirror tool permissions from T021
- [ ] T023 [US2] Implement `experiments/run_agentic.py`: CLI per contracts/cli.md (`--seeds --budget --rounds --pool --gap-min --gap-max --ehull-max --refutation-demo --no-analysis --use-cache --out`); round-0 shared random seeding batch of 50; rounds 1..N drive the Omnigent workflow; deterministic Planner scoring aids (expected learning/feasibility/cost per strategy) computed in Python and fed to the Planner agent (research R5); LLM completions cached to `cache/llm/` by (agent, model, prompt-hash); output `results/agentic.csv` rows {arm:"agentic", seed, round, evaluations, cumulative_hits, rmse, strategy}
- [ ] T024 [US2] Run `python experiments/run_agentic.py --seeds 1` end-to-end; confirm one full loop logged; if the hour-14 checkpoint is at risk, cut to scope: pre-fetched citations only, Omnigent covering Planner→Runner→Analysis with the rest deterministic (constitution cut order)

**Checkpoint**: AC-2 (one complete loop) satisfied; research_log.jsonl committed

---

## Phase 5: User Story 4 - Human Approval for Consequential Actions (Priority: P2)

**Goal**: The three consequential actions blocked by permissions/policies until human approval; approval path logged

**Independent Test**: Negative control — Runner calling recommend_for_validation is denied by the permission layer before any human prompt; approved request via Safety proceeds and is logged (quickstart Scenario 6)

- [ ] T025 [US4] Implement runtime permission enforcement `src/permissions.py`: `allowed(agent, tool) -> bool` loaded from `policies/tool_permissions.yaml`; `require_approval(action, justification) -> ApprovalDecision` gated on `policies/approval_rules.yaml` and interactive confirmation; both write ResearchRecord lines
- [ ] T026 [US4] Wire enforcement: runner's tool surface in `omnigent/workflow.yml` contains NO recommend_for_validation; the only invoke path is Safety's post-approval; recommend_for_validation result becomes the final shortlist artifact `results/shortlist.json` (candidates + citations + uncertainty)
- [ ] T027 [P] [US4] Add `tests/test_permissions.py`: every (agent, tool) pair NOT granted in tool_permissions.yaml denied; each of the three gated actions requires an ApprovalDecision{approved:true} before its side effect; denial path leaves zero side effects

**Checkpoint**: quickstart Scenario 6 demonstrable live

---

## Phase 6: User Story 3 - Result Changes the Decision (Priority: P2)

**Goal**: Reproducible designed scenario: misleading hypothesis → exploitation plateau → refutation → strategy switch → recovery

**Independent Test**: `python experiments/run_agentic.py --refutation-demo` writes `records/refutation_example.jsonl` with refuted verdict after two consecutive at/below-random rounds and subsequent strategy change (quickstart Scenario 4)

- [ ] T028 [US3] Implement the seeded scenario in `src/refutation.py` (or `experiments/run_agentic.py --refutation-demo` branch): force Insight's top hypothesis to the electronegativity-difference-only rule; Analysis refutes when hit rate ≤ random baseline for 2 consecutive rounds (evidence string with both rates); Planner MUST switch to hybrid or explore next round and log reason; everything under fixed seed with cached LLM outputs
- [ ] T029 [US3] Run the scenario; if the refutation never triggers naturally after one tuning pass, keep the forced variant and record in README that the moment is a designed scenario (constitution honesty); produce the hits curve segment showing pre/post-switch rates

**Checkpoint**: AC-3 satisfied; `records/refutation_example.jsonl` committed

---

## Phase 7: User Story 5 - Reconstruct Every Decision as a Reviewer (Priority: P3)

**Goal**: Any decision reconstructable from the record alone

**Independent Test**: reconstruction check passes on a real run (quickstart Scenario US5 acceptance)

- [ ] T030 [P] [US5] Add `experiments/replay_log.py`: given `records/research_log.jsonl` + run_id, verify ordered chain completeness (every experiment spec has a runner result and analysis verdict; every verdict's hypothesis id exists; every citation id exists), print any gap; used by the reviewer journey and README audit section

**Checkpoint**: reviewer can walk a decision end-to-end from the log alone

---

## Phase 8: Multi-Seed, Ablation & Results (Cross-cutting results rigor)

**Purpose**: Final measured numbers for AC-1/AC-4/AC-5 and FR-012/013/014

- [ ] T031 Run `python experiments/run_agentic.py --seeds 10 --use-cache cache/` (LLM outputs cached; seeds parallelizable if time allows)
- [ ] T032 [P] Run ablation `python experiments/run_agentic.py --seeds 10 --no-analysis` producing `results/ablation.csv` (planner receives no Analysis feedback; strategy held at round-1 choice)
- [ ] T033 Produce final artifacts via analyze_results.py: `results/curves.png` (all 5 arms, mean ± std) and `results/summary.csv` (evals-per-hit-milestone and matched-count speedup mean±std per arm incl. ablation); numbers reported EXACTLY as measured
- [ ] T034 Citation audit: open every DOI/URL in records + docs/CITATIONS.md, confirm resolution, remove or re-fetch any that fail

---

## Phase 9: Polish & Cross-Cutting Concerns — CODE FREEZE at start

**Purpose**: Packaging, README honesty, demo; features frozen (constitution hour-19 gate)

- [ ] T035 [P] Write `README.md`: question, bottleneck, method, agent table (decision/tools/I-O), approval gates & policies, results ONLY from `results/summary.csv` (embed `results/curves.png`), the designed refutation example description, limitations (retrospective benchmark, proxy oracle, composition features only, designed scenario), validation still needed (DFT then wet lab), next experiment, path-to-10x section, one-command reproduction
- [ ] T036 [P] Write `demo/script.md` per PLAN.md §9 timing table (0:00 question → 0:15 Omnigent handoffs → 0:40 reveal + budget → 1:05 refutation + switch → 1:30 speedup curve → 1:50 approval gate + next step)
- [ ] T037 Verify every handoff in final committed `records/research_log.jsonl` against contracts/handoff.schema.json and run `experiments/replay_log.py` clean
- [ ] T038 Fresh-clone test exactly as quickstart Scenario 7 (`git clone` to /tmp, venv, pip install, `pytest -q`, `run_baselines.py --quick`); fix any friction
- [ ] T039 Final repo freeze: commit agent specs, policies, omnigent/workflow.yml, records, results, demo; tag `submission`

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 Setup
   └─> Phase 2 Foundational (T005 blocks all; T006/T008 block their story phases)
         ├─> Phase 3 US1 (MVP: needs T005, T006)
         │     └─> Phase 8 multi-seed baselines contribution (T033)
         ├─> Phase 4 US2 (needs T005-T010; T002 smoke must pass before T022)
         │     ├─> Phase 5 US4 (needs T021/T022 workflow)
         │     ├─> Phase 6 US3 (needs T023 runnable loop)
         │     ├─> Phase 7 US5 (needs a complete logged run)
         │     └─> Phase 8 T031/T032 sweeps
         └─> Phase 9 Polish (needs Phase 8 results)
```

### User Story Dependencies

- **US1 (P1)**: Foundational only. Must complete (incl. T017 decision gate) before US2.
- **US2 (P2)**: US1 decision gate + T002 Omnigent smoke. Core orchestration deliverable.
- **US4 (P2)**: needs policies (T021) + workflow (T022); completes the submission's responsibility story before multi-seed runs.
- **US3 (P2)**: needs a runnable agent loop (T023).
- **US5 (P3)**: needs a real logged run; standalone script, low risk.

### Within Each User Story

- Tests FIRST (T012 before T013/T014 under TDD for strategies; T007/T009 written alongside their foundational modules)
- Models/schemas before services; services before CLI entrypoints; run the story's independent test at checkpoint

### Parallel Opportunities

- Phase 1: T003 + T004
- Phase 2: T008/T009/T010/T011 parallel once T005-T007 pattern settled; T007 pairs with T006
- Phase 3: T016 (analysis) parallel with T015 once CSV format agreed
- Phase 4: T018, T020, T021 fully parallel (different dirs); T019 manual fetch parallel
- Phase 9: T035 + T036 parallel

### Parallel Example: Phase 4 kick-off

```bash
# Launch together (different files, no cross-deps):
Task: "Implement src/tools_lit.py (T018)"
Task: "Write 7 agent spec files agents/*.md (T020)"
Task: "Write policies/tool_permissions.yaml + approval_rules.yaml (T021)"
```

---

## Implementation Strategy

### MVP First (Phases 1-3 Only)

1. Phase 1 Setup — exit when JARVIS loads and Omnigent smoke passes/fails-cleared
2. Phase 2 Foundational — `pytest -q` green with the three integrity suites
3. Phase 3 US1 — baselines beat random (T017 gate)
4. **STOP and VALIDATE** — quickstart Scenarios 1-2

### Incremental Delivery

1. US2 single loop (Phase 4 checkpoint = hour-14 equivalent; if red, apply cut scope in T024)
2. US4 approval gate (demo-critical)
3. US3 refutation moment (demo centerpiece)
4. Phase 8 sweeps + ablation, then Phase 9 packaging behind code freeze

### Cut Order (constitution; if time collapses)

stretch goals → live literature (use T019 cache) → ablation (T032) → hypothesis_test strategy → extra plots. NEVER cut phases 2-3 tests, the Omnigent loop, or T035 README honesty.

---

## Notes

- [P] tasks = different files, no dependencies
- Field-level constraints (min items, enums, const labels) quoted from data-model.md / contracts/handoff.schema.json so no requirement is left to implementation discretion
- Verify tests fail before implementation where applicable (T007, T012)
- Commit after each task or logical group; every unverified number stays out of README/report
