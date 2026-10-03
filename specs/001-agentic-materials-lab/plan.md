# Implementation Plan: Agentic Materials Discovery Lab

**Branch**: `001-agentic-materials-lab` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-agentic-materials-lab/spec.md`

## Summary

Build a 24-hour closed-loop agentic lab that searches NIST JARVIS `dft_3d` for materials with
band gap in 1.2-1.8 eV using as few simulated expensive evaluations (budget-enforced label
reveals) as possible. Technical approach: a science core (data loader, budget-enforced oracle,
RandomForest surrogate with tree-variance uncertainty, four acquisition strategies, Pydantic
handoff contracts, append-only JSONL record) plus an Omnigent-orchestrated 7-agent workflow
(Literature → Insight → Planner → Runner → Analysis → Record, with Safety gating), benchmarked
against random/greedy/uncertainty baselines over ≥10 seeds with an analysis-agent ablation and a
deliberately engineered hypothesis-refutation scenario.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: jarvis-tools (JARVIS dft_3d loader), matminer Magpie composition
features (fallback: hand-built element-property statistics), scikit-learn RandomForestRegressor
(per-tree variance as uncertainty; LightGBM as alternative), pydantic v2 (handoff schemas),
requests (OpenAlex/arXiv clients with on-disk caching), matplotlib, numpy/pandas, Omnigent
(mandated orchestrator, exact workflow syntax from its current docs)

**Storage**: Files only — parquet/csv caches for data and features, JSON on-disk caches for LLM
and API outputs, `records/*.jsonl` research record, `results/*.csv` + PNG plots. No database,
no vector store.

**Testing**: pytest — three integrity-critical suites (oracle leak, budget enforcement,
double-reveal rejection; handoff schema validation incl. AGENT-GENERATED label enforcement)
plus golden-fixture unit tests for strategies.

**Target Platform**: Linux (hackathon workstation); Omnigent managed Databricks sandbox or
open-source runtime.

**Project Type**: CLI experiment scripts + library + agent workflow config (`omnigent/`).

**Performance Goals**: one full agentic 6-round run (seed) in minutes; ≥10-seed sweeps
feasible within the Rounds 5-6 time-box thanks to disk caching of data, features, LLM and
API outputs.

**Constraints**: budget 300 evaluations (6 rounds × 50); pool 10-20k subsample; one dataset,
one property, one loop (constitution Principle VIII); all agent labels hidden except through
oracle (Principle II); feature freeze at hour 19.

**Scale/Scope**: 7 agent specs, ~10 Python modules, 3 experiment entrypoints, 1 workflow
config, 2 policy files, 3 test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Scientific Honesty | Only measured numbers in README/results artifacts; limitations section mandatory | PASS (FR-015, SC-003 encode this; plan's analyze_results.py only reads measured CSVs) |
| II. Oracle Integrity | Single private label store; reveal-only access; automated leak test; no label column in features | PASS (oracle.py single access path; test_oracle.py asserts non-reachability; featurization excludes target column) |
| III. Citations | Claims only from real API responses cached to disk; uncited-as-fact blocked by Safety | PASS (tools_lit.py caches; approval_rules.yaml + Safety gate) |
| IV. Labeling | AGENT-GENERATED required by schema; uncertainty surfaced | PASS (Hypothesis schema rejects missing label; verdicts carry evidence) |
| V. Human Approval | Permission/policy enforcement, not prompts; Runner lacks recommend capability | PASS (policies/tool_permissions.yaml grants oracle only to Runner; recommend_for_validation lives behind approval path) |
| VI. Reconstructability | Pydantic-validated handoffs logged with run_id/seed/hash | PASS (schemas.py Handoff + record.py JSONL append) |
| VII. Reproducibility | Pinned requirements, fixed seeds, one-command run, fresh-clone check | PASS (requirements.txt; seeds in every run; quickstart one-command flow) |
| VIII. Scope Discipline | One dataset/property/loop; no GNN/DFT/vector DB/extra frameworks | PASS (plan includes none of these) |
| IX. Orchestration | Omnigent orchestrates live loop | PASS (omnigent/ workflow; fallback keeps science core only, not a replacement) |
| X. Testing | oracle-leak, schema-validation, budget-enforcement tests real and required | PASS (tests/ contains exactly these before extra coverage) |

Gate evaluation: no violations requiring justification. Post-design re-check (Phase 1): still
clean — contracts and data model introduce no label-access path outside the oracle and no new
frameworks or datasets.

## Project Structure

### Documentation (this feature)

```text
specs/001-agentic-materials-lab/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (handoff JSON schema, CLI/workflow contracts)
└── tasks.md             # /speckit-tasks output (next command)
```

### Source Code (repository root)

```text
agents/
├── literature.md        # spec: decision owned, tools, I/O schema
├── insight.md
├── planner.md
├── runner.md
├── analysis.md
├── record.md
└── safety.md

policies/
├── tool_permissions.yaml  # which agent may call which tool
└── approval_rules.yaml    # actions requiring human approval

omnigent/
└── workflow.yml           # Omnigent workflow definition (syntax per Omnigent docs)

src/
├── data.py                # load + subsample + featurize JARVIS; define top set
├── oracle.py              # budget-enforced label reveal (sole label access path)
├── surrogate.py           # RandomForest model + tree-variance uncertainty
├── strategies.py          # exploit / explore / hybrid (UCB) / hypothesis_test
├── tools_lit.py           # OpenAlex / arXiv wrappers with on-disk cache
├── schemas.py             # Pydantic handoff + entity schemas
└── record.py              # append-only JSONL research-record writer

experiments/
├── run_baselines.py       # random / greedy / uncertainty, N seeds
├── run_agentic.py         # full Omnigent-orchestrated loop (+ --no-analysis ablation)
└── analyze_results.py     # curves, speedup, summary tables

tests/
├── test_oracle.py         # leak, budget, double-reveal
├── test_schemas.py        # handoff validation, label enforcement
└── test_strategies.py     # golden-fixture strategy behavior

records/
└── research_log.jsonl     # append-only record (plus refutation_example.jsonl)

results/                   # CSVs and plots (curves.png, summary.csv, ...)
demo/
└── script.md              # 2-minute demo script
```

**Structure Decision**: Flat single-package layout from the project plan (PLAN.md §7): `src/`
holds the science core, `experiments/` holds runnable entrypoints, `agents/` + `policies/` +
`omnigent/` hold the orchestration deliverables required by the brief. No nested packages —
keeps imports trivial for hackathon speed and matches the constitution's scope discipline.

## Complexity Tracking

> No constitution violations — table not required.
