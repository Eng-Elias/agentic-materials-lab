# Agentic Materials Discovery Lab

A closed-loop, budget-constrained benchmark in which specialist agents plan,
execute, and analyze simulated materials evaluations over the NIST JARVIS
`dft_3d` dataset — with honest measurement of whether agent orchestration
actually helps.

> **Hack-Nation × Databricks — Agentic Scientific Discovery challenge.**

---

## The question

> *Expensive evaluations are the bottleneck in materials discovery. Can a
> multi-agent system find high-performing materials with fewer evaluations
> than non-agentic baselines — and can it recover when its own hypotheses
> are wrong?*

## The bottleneck attacked

High-throughput screening (DFT, then wet lab) evaluates candidates one
expensive oracle call at a time. Random search wastes budget; greedy
exploitation wastes it differently — it over-samples a surrogate's favorite
region and never tests whether the guiding assumptions hold. This lab attacks
the bottleneck on two fronts:

1. **Efficiency** — measure evaluations-to-milestone for each search
   strategy under a hard oracle budget.
2. **Adaptivity** — demonstrate that the loop can detect a *refuted*
   hypothesis from evidence and change strategy, something a fixed
   acquisition function cannot do.

## Method

- **Dataset**: NIST JARVIS `dft_3d` (~93,902 entries), deterministically
  subsampled to a **15,000-material pool**.
- **Target**: materials with DFT band gap in **[1.0, 2.0] eV**. The pool's
  top set contains **874 members (5.83%)**.
- **Oracle**: private-label, budget-enforced (`budget = 300` evaluations per
  run). Agent code can never see labels until the oracle reveals them —
  the label column is physically separated from features
  (`src/oracle.py`).
- **Features**: composition-only Magpie-style descriptors (matminer), with
  a deterministic fallback featurizer.
- **Surrogate**: LightGBM regressor retrained each round on revealed labels.
- **Loop** (6 rounds × 50 evaluations after a 50-evaluation seed batch):
  Literature → Insight → Planner → Runner → Analysis → Record, with Safety
  gating consequential actions.
- **Baselines** (same pool, budget, seeds): random, greedy
  (pure exploitation), uncertainty (pure exploration).
- **Ablation**: agentic loop with the Analysis agent's strategy overrides
  disabled.

## Agents

| Agent | Decision it owns | Tools | Input → Output |
|---|---|---|---|
| **Literature** | Which cited claims are relevant | `search_lit` (disk-cached OpenAlex/arXiv) | question → cited `Claim`s |
| **Insight** | Hypothesis generation (labeled `AGENT-GENERATED`) | none | claims → `Hypothesis[]` (Pydantic-validated, ≥1 citation each) |
| **Planner** | Strategy choice per round (explore / exploit / hybrid / hypothesis-test) | `propose_experiments` | evidence + verdicts → `ExperimentSpec` |
| **Runner** | None — executes the approved batch only | `run_oracle` (budget-enforced) | `ExperimentSpec` → `RunResult` |
| **Analysis** | Hypothesis verdicts (`supported` / `refuted` / `inconclusive`) and strategy overrides | `analyze_results` | `RunResult` → `HypothesisVerdict[]` |
| **Record** | None — appends validated handoffs | `write_log` | handoffs → `records/research_log.jsonl` |
| **Safety** | Approval gate for consequential actions | `request_approval`, `recommend_for_validation` | escalation → `ApprovalRequest` |

Every inter-agent handoff is a Pydantic-validated `Handoff` object
(`src/schemas.py`) and is appended to an append-only JSONL research log.

## Human-approval gates and policies

Enforced at runtime by `src/permissions.py` — the policy files are the
single source of truth, not the prompts:

- `policies/tool_permissions.yaml` — per-agent tool allowlist;
  `deny_all_others: true`. Only `safety` may call
  `recommend_for_validation`, and only **after** human approval.
- `policies/approval_rules.yaml` — actions that always require a human:
  externalizing a validation shortlist, exceeding the oracle budget, and
  publishing unverified claims (`default_when_unclear: deny`).

## Results

*All numbers from `results/summary.csv` and `results/speedups.csv`;
10 seeds, budget 300, 6 rounds. Regenerate with `./reproduce.sh`.*

![Learning curves](results/curves.png)

### Final hits (budget 300, mean ± std, n = 10 seeds)

| Arm | Final hits | Evals to 10 hits | Evals to 25 hits |
|---|---|---|---|
| random | 17.5 ± 3.3 | 180.0 ± 35.0 | never reached |
| greedy | **55.9 ± 14.4** | **130.0 ± 25.8** | **195.0 ± 28.4** (10/10) |
| uncertainty | 21.1 ± 5.3 | 165.0 ± 47.4 | 287.5 ± 25.0 (4/10) |
| **agentic** | 22.3 ± 7.0 | 170.0 ± 48.3 | 266.7 ± 57.7 (3/10) |
| ablation | 22.3 ± 7.0 | 170.0 ± 48.3 | 266.7 ± 57.7 (3/10) |

The 50%-of-top-set milestone (437 hits) was **never reached by any arm**
within the 300-evaluation budget.

### Speedup vs. agentic (`evals_arm / evals_agentic`, >1 = agentic faster)

| Milestone | Arm | Speedup (mean ± std) | n | Verdict |
|---|---|---|---|---|
| 5 hits | random | 1.067 ± 0.344 | 10 | agentic faster |
| 10 hits | random | 1.132 ± 0.352 | 10 | agentic faster |
| 10 hits | greedy | **0.833 ± 0.327** | 10 | **agentic slower** |
| 10 hits | uncertainty | 0.988 ± 0.220 | 10 | agentic slower |
| 25 hits | greedy | **0.778 ± 0.192** | 3 | **agentic slower** |
| 25 hits | uncertainty | 1.111 ± 0.347 | 3 | agentic faster |

### Ablation

Agentic ≡ ablation on this benchmark (identical trajectories): in the
normal ten-seed run no refutation event occurred, so the Analysis agent's
override path — the behavior the ablation removes — never fired. The
ablation's value is demonstrated by the refutation scenario below, not by
these numbers.

### What this honestly means

**On raw hit efficiency, the agentic arm loses to greedy.** Once the seed
batch trains the surrogate, pure exploitation dominates this pool, and the
hybrid/explore components the agents mix in dilute hit count. The agents
beat random narrowly (1.13× at the 10-hit milestone) and are roughly
comparable to uncertainty. We report this as measured — the benchmark's
purpose is to *measure* discovery efficiency, not to manufacture a win.

The agentic advantage the system *does* demonstrate is adaptive recovery —
see below.

## The refutation example (designed scenario)

`--refutation-demo` seeds a deliberately plausible-but-wrong hypothesis:

> **H1** — "SMALL electronegativity difference (near-covalent bonding)
> determines membership in the target band-gap window" → the planner's
> `exploit` arm ranks candidates by *lowest* electronegativity range.

Measured trace (`records/refutation_example.jsonl`):

- Rounds 1–2: guided-arm hit rate **[0.02, 0.02]** vs. random baseline
  **0.057** — below random for 2 consecutive rounds.
- Round 2 analysis: **H1 → `refuted`** with the evidence string recorded;
  recommendation `switch_to_hybrid`.
- Round 3: planner switches to `hybrid`; cumulative hits recover
  (exploit 3 → 4, hybrid 8).
- Refutation is **terminal**: later logs state *"H1 remains REFUTED;
  prior evidence stands"* — a stale hypothesis cannot silently
  un-refute itself.

This is the behavior no fixed acquisition function has: **the system
detected that its own guiding hypothesis was wrong, recorded the evidence,
and changed strategy.**

## Reproducing

```bash
pip install -r requirements.txt
./reproduce.sh        # baselines + 10-seed agentic + ablation + analysis
```

or step by step:

```bash
python experiments/run_baselines.py            # random / greedy / uncertainty
python experiments/run_agentic.py --seeds 10   # agentic loop (engine backend)
python experiments/run_agentic.py --seeds 10 --ablation
python experiments/analyze_results.py          # curves.png, summary.csv, speedups.csv
python experiments/run_agentic.py --refutation-demo
```

Quick check: `python experiments/run_agentic.py --quick` · tests: `pytest -q` (45 passing).

### Real-LLM mode (optional)

The default `--backend engine` is a deterministic Python loop — no LLM
calls, fully reproducible. To have Insight and Planner reason with a real
model (provider outputs are disk-cached for reproducibility), set:

```bash
cp .env.example .env   # fill in one provider block
```

`LLM_PROVIDER=openai` works with **any `/chat/completions`- or
`/responses`-compatible endpoint** (OpenAI, OpenCode Zen, Databricks
serving, vLLM, Ollama); `LLM_PROVIDER=anthropic` uses the Messages API.
LLM-written text is schema-validated and falls back to deterministic
output if malformed. Measured numbers in this README come from the
deterministic engine backend; provider/model provenance is recorded in
every cached call.

### Omnigent orchestration

`omnigent/workflow.yml` + `omnigent/agents/*.yaml` declare the same
seven agents for the Omnigent orchestrator (smoke-tested live: a
schema-validated `Handoff` exchanged via the `claude-sdk` harness on an
OpenCode Zen gateway — `omnigent run omnigent/smoke/handoff_smoke.yml`).
Scientific truth (oracle, budget, scoring) stays in Python under both
backends; agents never mutate oracle state.

## Limitations

- **Retrospective benchmark**: the oracle replays existing DFT labels;
  no new physics is computed or discovered.
- **Proxy oracle**: "expensive evaluation" is simulated — cost model is a
  budget counter, not wall-clock or dollars.
- **Composition features only**: no structure, no graph embeddings; the
  surrogate sees a small descriptor space, which is exactly why greedy is
  so strong here.
- **Designed refutation scenario**: H1 is intentionally misleading to
  exercise the verdict machinery; it is not a claim that real literature
  suggests it.
- **Single dataset / single target window**; one pool size and budget.
- **No novel material is claimed.** All reported numbers are benchmark
  statistics.

## Validation still needed

Any candidate this system would nominate is, at best, a *computational
hypothesis*: DFT re-verification (the pool labels are themselves PBE-level,
which systematically underestimates band gaps), then wet-lab synthesis and
measurement. Nothing here has undergone either.

## The next experiment — justified by what the lab learned

The data says exploitation wins when the surrogate is already accurate —
so the bottleneck is not "search harder" but **"learn a better surrogate
per evaluation."** Next experiment: replace composition-only features with
structure-aware embeddings (e.g., a pretrained GNN such as
ALIGNN/CHGNet off the same JARVIS entries) and re-run the identical
10-seed benchmark. Prediction: greedy's advantage shrinks as the
surrogate's blind spots grow, and the Analysis agent's evidence-driven
strategy switching — worthless when greedy is optimal — becomes the
deciding factor.

## What 10× would actually require

A 10× discovery-efficiency claim at scale needs: (a) a multi-fidelity
oracle (cheap screen → expensive confirm), since single-fidelity
acquisition saturates; (b) structure-aware features; (c) a larger top-set
fraction or a relaxed success metric — with a 5.83% top set, 437 hits in
300 draws is information-theoretically unreachable for any policy; (d)
real cost models (wall-clock, $/eval) rather than a uniform budget; and
(e) prospective evaluation on candidates the loop has never seen labels
for. The current scaffold already separates these concerns, so each can
be upgraded independently.

## Citations

All literature claims are backed by DOI-verified, disk-cached sources —
see `docs/CITATIONS.md` for the full table and the T034 audit record
(all 14 DOIs resolve; none removed).
