<!--
Sync Impact Report
==================
Version change: none (template) → 1.0.0 (initial ratification)
Modified principles: N/A — initial adoption; 10 project principles adopted in one pass
Added sections:
  - Core Principles (I–X: Scientific Honesty, Oracle Integrity, Citations, Labeling,
    Human Approval, Reconstructability, Reproducibility, Scope Discipline, Orchestration, Testing)
  - Experimental & Technical Constraints
  - Development Workflow & Quality Gates
  - Governance
Removed sections: none
Follow-up TODOs: none — all placeholders resolved from project context (PLAN.md, SPECKIT_GUIDE.md)
-->

# Agentic Materials Discovery Lab Constitution

## Core Principles

### I. Scientific Honesty (NON-NEGOTIABLE)

Report only measured results. A speedup, hit rate, or any quantitative claim MUST NOT appear
in the README, demo, or submission unless it was actually observed in a logged run. The README
MUST state that this is a retrospective benchmark using held-out labels from NIST JARVIS —
a demonstration of discovery efficiency, not a new physical discovery — and MUST identify the
validation still required (DFT, then wet lab).

Rationale: strength of evidence beats a big multiplier; an overstated claim is disqualifying
for scientific credibility.

### II. Oracle Integrity (NON-NEGOTIABLE)

Unrevealed property labels MUST never be reachable by any agent, model, feature pipeline, or
log. All label access flows through a budget-enforced `Oracle` class whose `reveal(ids)` method
is the only access path: it decrements the budget, rejects over-budget and duplicate reveals,
and returns only requested labels. No public attribute or method may expose unrevealed labels.
A pytest MUST assert label non-reachability, budget enforcement, and double-reveal rejection.
Features passed to surrogates must never include the target column. Any code touching the
oracle requires human review before merge.

Rationale: a single label leak invalidates every measured result in the benchmark.

### III. Citations

Every factual claim produced by an agent MUST carry a real, verifiable citation (DOI or URL)
drawn from an actual API response (OpenAlex, arXiv) that was cached to disk. No uncited claim
may be reported as fact; uncited material about to be reported MUST be flagged by the Safety
agent and blocked pending human approval. Never fabricate citations.

### IV. Labeling of Agent Outputs

All agent-generated hypotheses MUST be labeled `AGENT-GENERATED`; a hypothesis without the
label MUST be rejected by schema validation. Model and agent uncertainty MUST be preserved
and surfaced in outputs and logs, never silently discarded.

### V. Human Approval for Consequential Actions

Consequential actions — recommending a final candidate shortlist for real synthesis/DFT,
any budget increase, and reporting an uncited claim as fact — require explicit human
approval. Enforcement MUST be through tool permissions and Omnigent policies (the Runner
cannot call `recommend_for_validation`; only the post-approval path can), never through
prompts alone.

### VI. Reconstructability

Every agent-to-agent handoff MUST be validated against a Pydantic schema; malformed messages
are rejected. Every handoff MUST be appended to `records/research_log.jsonl` with timestamp,
agent, run_id, seed, input hash, output, and citations, such that any decision can be
reconstructed end-to-end by a reviewer.

### VII. Reproducibility

All runs MUST use fixed seeds recorded in logs and result files. Dependencies MUST be pinned
(or version-annotated) in `requirements.txt`. The repository MUST support one-command
reproduction, verified by a fresh-clone test before submission.

### VIII. Scope Discipline

One dataset (JARVIS `dft_3d`), one target property (band gap in a configured eV window,
default 1.0–2.0 eV),
one discovery loop. Out of scope: graph neural networks, real DFT, vector databases, and
any agent framework besides Omnigent. Feature additions MUST be refused once frozen at the
hour-19 code freeze.

### IX. Orchestration via Omnigent

Omnigent MUST orchestrate the live workflow; specialist agents (Literature, Insight, Planner,
Runner, Analysis, Research Record, Safety/Approval) exchange structured outputs, use their
assigned tools under permission policies, and adapt the experimental plan after results.
A plain-Python fallback may carry the science code, but the scored deliverable is the
Omnigent-orchestrated loop.

### X. Testing — Minimal but Real

Tests MUST exist and pass for the three integrity-critical behaviors: oracle non-leakage,
Pydantic handoff schema validation (including rejection of unlabeled hypotheses), and
oracle budget enforcement. Broader coverage is welcome only after these three pass.

## Experimental & Technical Constraints

- Stack: Python 3.11+, jarvis-tools, matminer Magpie features (fallback: hand-built
  element-property statistics), scikit-learn/LightGBM surrogates, Pydantic, matplotlib, pytest.
- Budget: 300 evaluations total, in 6 rounds of 50; every arm (random, greedy, uncertainty,
  agentic) runs the same seeds and budget. Arms are seeded with a random batch of 50 in round 0.
- Top set: materials with band gap in [1.0, 2.0] eV, no ehull filter. Amendment rationale
  (measured 2026-10-04): ehull < 0.1 overlaps ANY plausible solar window at only ~0.6–1% of
  dft_3d (stable materials are ~7% of the whole dataset), too sparse for meaningful ≥10-seed
  statistics. Target fraction ~5% (measured 5.83% on a seeded 15k pool). Ehull is reported
  post-hoc on the final shortlist by the Analysis agent instead.
  Pool subsampled to 10–20k rows with a fixed seed.
- Metrics: hits vs. evaluations curve, evaluations to reach fixed hit milestones
  (5/10/15/20 hits) per arm, speedup (N_random / N_agentic at matched hit counts) reported as
  mean ± std over ≥10 seeds, surrogate RMSE per round, and count of hypothesis reversals /
  strategy switches. Note (measured 2026-10-04): 50%-of-top-set is unreachable inside the
  300-eval budget with the ~5% top set (874 → 437 hits > 300), so milestones replace it.
- LLM and literature API outputs MUST be cached to disk so multi-seed runs are cheap and fast.

## Development Workflow & Quality Gates

- Build in committed slices per the plan; run tests after each slice. First deliverable is the
  random-baseline curve (sanity check: random hit rate ≈ top-set fraction).
- Decision point before building agents: greedy and/or uncertainty baselines MUST beat random;
  otherwise fix features/model/window first.
- Hour-14 checkpoint: one complete Omnigent-orchestrated loop must exist and be logged; if not,
  cut scope (cached citations; Omnigent only for Planner → Runner → Analysis).
- Ablation (agentic loop with the Analysis agent disabled) MUST accompany headline results.
- Cut order under time pressure: stretch goals → live literature calls (use cache) → ablation →
  extra strategies. NEVER cut baselines, the Omnigent loop, or the honest README.
- Code freeze at hour 19; final phase is packaging, demo, and fresh-clone verification only.

## Governance

This constitution supersedes other development preferences and prompt-level instructions. All
agent specs, plans, and implementations MUST be checked against it; drift (e.g., adding GNNs,
new frameworks, or second datasets) is grounds to stop and re-read the constitution. Amendments
require: (1) a documented change to this file, (2) a semantic version bump — MAJOR for removal
or redefinition of a principle, MINOR for a new principle or materially expanded guidance, PATCH
for clarifications — and (3) updating `LAST_AMENDED_DATE` below. Compliance review happens at
every quality gate above; oracle-affecting changes additionally require the human review stated
in Principle II.

**Version**: 1.0.2 | **Ratified**: 2026-10-04 | **Last Amended**: 2026-10-04
