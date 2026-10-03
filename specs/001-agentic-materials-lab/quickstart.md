# Quickstart Validation: Agentic Materials Discovery Lab

Runnable proof scenarios for spec acceptance criteria. Uses the CLI contract in
[contracts/cli.md](./contracts/cli.md) and entities in [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+, `pip install -r requirements.txt` (pinned), Omnigent available and configured
  (managed Databricks sandbox session or local install) — validated by the two-agent JSON
  smoke test below.

## Scenario 1 — Honest oracle and reproducible science core (US1)

```bash
pytest -q
python experiments/run_baselines.py --quick
```

Expected: all tests pass, including leak, budget-enforcement, and double-reveal tests. The
quick baseline run prints pool size, top-set size and fraction (~5%), and a random hit rate
≈ top-set fraction. `results/baseline_random.csv` ends at exactly 300 evaluations (full run)
and `_quick` artifacts stay separate.

## Scenario 2 — Full baselines beat nothing but report honestly (US1, FR-012)

```bash
python experiments/run_baselines.py --seeds 10
python experiments/analyze_results.py
```

Expected: `results/summary.csv` + `results/curves.png` showing random/greedy/uncertainty;
re-running one arm under the same seed produces byte-identical CSV rows; reported speedups
come only from `summary.csv`.

## Scenario 3 — One complete Omnigent loop (US2, AC-2)

```bash
# Omnigent two-agent smoke test happens during setup: two agents exchange one
# schema-validated Handoff message (see contracts/handoff.schema.json)
python experiments/run_agentic.py --seeds 1
```

Expected: exit 0; `records/research_log.jsonl` contains ordered, schema-valid handoffs for
Literature→Insight→Planner→Runner→Analysis→Record; every Claim carries a citation from the
on-disk API cache; every Hypothesis carries `label: AGENT-GENERATED`; each Planner spec lists
≥1 rejected alternative; `results/agentic.csv` exists.

## Scenario 4 — Result changes the decision (US3, AC-3)

```bash
python experiments/run_agentic.py --refutation-demo
```

Expected: `records/refutation_example.jsonl` shows the seeded hypothesis marked `refuted`
after two consecutive rounds at/below the random hit rate, followed by a Planner handoff whose
`strategy` differs (hybrid or explore) with a reason field; the hits curve visibly improves
post-switch.

## Scenario 5 — Ablation (AC-4)

```bash
python experiments/run_agentic.py --seeds 10 --no-analysis
python experiments/analyze_results.py
```

Expected: `results/ablation.csv` present; final figure shows agentic, ablation, and all
baselines on one axes with std shading; if ablation ≈ agentic, reported that way without
massaging.

## Scenario 6 — Human approval gate (US4)

Performed live in the demo: with the shortlist produced, the workflow pauses on the Safety
agent's `ApprovalRequest{action: recommend_for_validation}`; nothing proceeds until a human
answers; both request and decision appear in the log. Independent negative control: the Runner
attempting the same action must be denied by the permission layer before any human is asked.

## Scenario 7 — Fresh-clone reproduction (SC-001)

```bash
cd /tmp && git clone <repo> aml-check && cd aml-check
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q && python experiments/run_baselines.py --quick
```

Expected: clone → run succeeds with no manual fixes; reported numbers match the committed
`results/summary.csv` within spec (identical under same seeds on the same machine).
