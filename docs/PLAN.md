# Agentic Materials Discovery Lab: 24-Hour Build Plan

**Challenge:** Hack-Nation x Databricks, Challenge 03, Agentic Scientific Discovery
**Required platform:** Omnigent (30% of score, so it must orchestrate the live workflow)
**Tools you have:** opencode Go, Devin AI (use them to scaffold code while you design handoffs)

---

## 1. The Project in One Paragraph

Build a closed-loop AI lab where specialist agents hunt for high-performing materials in the NIST JARVIS dataset using as few "expensive evaluations" as possible. Property labels are hidden, and "revealing a label" simulates running a costly experiment (DFT). Agents review literature, propose labeled hypotheses, plan experiments under a budget, run them, analyze results, and change strategy when evidence contradicts a hypothesis. The headline metric is **evaluations needed to find the top 5% of candidates vs. a random baseline**. Report whatever speedup you actually measure.

> **Honesty note (put this in your README):** This is a retrospective benchmark. Labels already exist in JARVIS, so it demonstrates *discovery efficiency*, not a new physical discovery. The next real step would be DFT or lab validation of the top candidates.

---

## 2. Scientific Setup

| Item | Choice |
|---|---|
| **Question** | Can an agentic active-learning loop find top-5% materials for a target property with several-fold fewer evaluations than random screening? |
| **Dataset** | NIST JARVIS `dft_3d` (~76k materials) via `jarvis-tools`; start with a subsample of ~10-20k for speed |
| **Target (pick ONE)** | Option A: band gap in a target window (e.g., 1.2-1.8 eV, solar-relevant). Option B: lowest formation energy / stable (ehull near 0). **Recommended: A**, since it makes a more interesting story |
| **"Experiment"** | Reveal the true label for a batch of chosen candidates. Costs 1 budget unit each |
| **Budget** | e.g., 300 total evaluations, in 6 rounds of 50 |
| **Success outcome** | Count of top-5% candidates found at each budget level |
| **Baselines** | (1) Random sampling, (2) Greedy surrogate only, (3) Uncertainty sampling only |
| **Your method** | Agent-planned adaptive strategy (switches between exploit/explore based on analysis) |

### Bottleneck attacked
Too many expensive evaluations are wasted on unpromising candidates. "Faster" = **fewer evaluations to reach the same hit count** (speedup = N_random / N_agentic at the same hit count).

---

## 3. Architecture

```
                        +----------------------------+
                        |   Omnigent orchestration   |
                        | tasks, tools, handoffs,    |
                        | policies, permissions      |
                        +--------------+-------------+
                                       |
   +-----------+   +-----------+   +---+-------+   +-----------+
   | Literature|-->|  Insight  |-->|  Planner  |-->|  Runner   |
   |   agent   |   |   agent   |   |  (budget) |   | (experim.)|
   +-----------+   +-----------+   +-----+-----+   +-----+-----+
         ^                               ^               |
         |                               |               v
   +-----+------+                  +-----+-----+   +-----------+
   | Knowledge  |<-----------------| Analysis  |<--| Results   |
   | / research |                  |   agent   |   |           |
   |  record    |                  +-----+-----+   +-----------+
   +------------+                        |
                                  +------v------+
                                  | Safety agent|--> human approval gate
                                  +-------------+
```

**The discovery loop:** Question -> Evidence -> Hypothesis -> Experiment -> Result -> Updated decision.

---

## 4. Agent Specifications

> Write these as actual spec files in `agents/` (the brief requires submitting agent specs and policies).

### 4.1 Literature Agent
- **Owns:** What does published evidence say about predictors of the target property?
- **Tools:** OpenAlex API, arXiv API (optional: Europe PMC is not needed here)
- **Input:** Target property + dataset feature list
- **Output (JSON):** `claims: [{claim, source_title, doi_or_url, confidence}]`
- **Rule:** No claim without a citation. Mark uncertainty explicitly.

### 4.2 Insight Agent
- **Owns:** Which hypotheses are worth testing?
- **Tools:** Read-only access to dataset summary stats + literature output
- **Input:** Cited claims, feature descriptions
- **Output:** 3 hypotheses, each labeled `AGENT-GENERATED`, with `{id, statement, testable_feature_set, predicted_direction, supporting_citation_ids}`
- **Example:** "H1: Electronegativity difference between constituent elements correlates positively with band gap."

### 4.3 Experiment Planner
- **Owns:** Which test to run next, given budget?
- **Tools:** Surrogate model query (predictions + uncertainty), budget tracker
- **Input:** Hypotheses, current budget, current surrogate state, prior round results
- **Output:** `experiment_spec: {round, strategy, batch_ids, rationale, expected_learning, cost}` plus the **rejected alternative(s)** and why
- **Must:** Evaluate at least 2 candidate strategies each round and score them on expected learning, feasibility, cost.
- **Strategies:** `exploit` (top predicted in target window), `explore` (highest uncertainty), `hybrid` (UCB / expected improvement), `hypothesis_test` (batch chosen to discriminate a hypothesis)

### 4.4 Experiment Runner
- **Owns:** Execute the experiment faithfully.
- **Tools:** `reveal_labels(ids)` (the oracle, only callable through the budget tracker), surrogate training (scikit-learn / LightGBM)
- **Input:** `experiment_spec`
- **Output:** `{batch_ids, true_values, hits_in_batch, cumulative_hits, budget_remaining, run_id, seed}`
- **Rule:** Cannot exceed budget. Oracle access is enforced by tool permissions.

### 4.5 Analysis Agent
- **Owns:** What did we learn, and does it contradict any hypothesis?
- **Tools:** Stats (correlation, SHAP / feature importance), comparison against baseline curve
- **Input:** Run result, hypotheses, baseline
- **Output:** `{hypothesis_verdicts: [{id, supported|refuted|inconclusive, evidence}], strategy_recommendation, surprises}`
- **Key behavior:** If the result is surprising (e.g., exploit strategy plateaus), it **reopens an earlier assumption** and tells the planner.

### 4.6 Knowledge / Research-Record Agent
- **Owns:** The shared record.
- **Tools:** Append-only writer to `records/research_log.jsonl`
- **Output:** Every handoff logged with `{timestamp, agent, input_hash, output, citations, run_id}`. Anyone can reconstruct any decision.

### 4.7 Safety / Approval Agent
- **Owns:** Flagging consequential actions.
- **Tools:** Policy checker, human-approval request
- **Triggers approval for:** (a) final candidate shortlist recommended for real synthesis/DFT, (b) any budget increase, (c) any claim lacking citation that is about to be reported as fact
- **Enforcement:** Through Omnigent tool permissions and policies, not only prompts. The Runner cannot call "recommend_for_synthesis"; only the post-approval path can.

---

## 5. Handoff Contract (structured JSON, versioned)

```json
{
  "run_id": "2026-10-03-r03",
  "round": 3,
  "from": "analysis_agent",
  "to": "planner",
  "payload": {
    "hypothesis_verdicts": [{"id": "H1", "verdict": "refuted", "evidence": "..."}],
    "strategy_recommendation": "switch_to_explore",
    "reason": "Greedy hit rate fell below random in last 2 rounds"
  },
  "citations": ["lit_004"],
  "uncertainty": "medium"
}
```

Validate every handoff with a Pydantic schema. Reject malformed messages.

---

## 6. Experimental Design

### 6.1 Data prep
1. Load JARVIS `dft_3d` via `jarvis.db.figshare.data("dft_3d")` (verify the exact function and field names after install).
2. Keep rows with valid band gap. Subsample 10-20k for speed.
3. Define `top_set` = materials whose gap falls within the target window AND (optionally) ehull < 0.1 eV/atom. Aim for roughly 5% of the pool.
4. Featurize with **matminer** `Magpie` composition features (fast, no structure needed). Fallback: simple element-property statistics if matminer install fails.
5. Hide labels in an `Oracle` class. Only the budget-tracked `reveal()` method returns them.

### 6.2 Surrogate model
- LightGBM or RandomForest. Uncertainty: RF tree variance, or quantile / ensemble spread.
- Retrain after every round.

### 6.3 Strategies compared (same seeds, same budget)
| Arm | Description |
|---|---|
| Random | Baseline |
| Greedy | Always pick top predicted in target window |
| Uncertainty | Always pick highest-variance |
| **Agentic** | Planner selects strategy per round based on Analysis agent feedback |

### 6.4 Metrics
- **Hits found vs. evaluations spent** (the main curve)
- **Evaluations to find 50% of top set**, per arm
- **Speedup** = N_random / N_agentic (mean +/- std over >= 10 seeds)
- Surrogate RMSE per round
- Number of hypothesis reversals / strategy switches

### 6.5 The "result changes the decision" moment (engineer this deliberately)
Seed one plausible but wrong hypothesis (e.g., a simple electronegativity rule). Let Round 1-2 greedy exploitation based on it plateau. Analysis agent refutes it, planner switches to explore/hybrid, and hit rate recovers. Capture this in the demo.

---

## 7. Repository Structure

```
agentic-materials-lab/
├── README.md
├── PLAN.md
├── requirements.txt
├── agents/
│   ├── literature.md        # spec: decision owned, tools, I/O schema
│   ├── insight.md
│   ├── planner.md
│   ├── runner.md
│   ├── analysis.md
│   ├── record.md
│   └── safety.md
├── policies/
│   ├── tool_permissions.yaml  # which agent may call which tool
│   └── approval_rules.yaml
├── omnigent/
│   └── workflow definition / config (per Omnigent docs)
├── src/
│   ├── data.py              # load + featurize JARVIS
│   ├── oracle.py            # budget-enforced label reveal
│   ├── surrogate.py         # model + uncertainty
│   ├── strategies.py        # exploit / explore / hybrid / hypothesis_test
│   ├── tools_lit.py         # OpenAlex / arXiv wrappers
│   ├── schemas.py           # Pydantic handoff schemas
│   └── record.py            # JSONL writer
├── experiments/
│   ├── run_baselines.py     # random / greedy / uncertainty, N seeds
│   ├── run_agentic.py       # full Omnigent-orchestrated loop
│   └── analyze_results.py   # curves, speedup, tables
├── records/
│   └── research_log.jsonl
├── results/
│   ├── curves.png
│   └── summary.csv
└── demo/
    └── script.md
```

---

## 8. Hour-by-Hour Timeline

### Phase 0: Hours 0-1, Setup and de-risk
- [ ] **Get Omnigent running first.** Choose managed Databricks (`<workspace-url>/omnigent` -> New session -> Sandbox) or open-source from GitHub. Read the docs for how to define multiple agents, tools, handoffs, and policies.
- [ ] Confirm you can make **two agents exchange structured output** through Omnigent. If this fails, escalate immediately (Discord/mentors).
- [ ] Create the repo, virtual env, and install: `jarvis-tools matminer scikit-learn lightgbm pydantic pandas matplotlib requests`
- [ ] Verify the JARVIS download works.
- [ ] Check LLM API access and rate limits for your chosen model.

### Phase 1: Hours 1-4, Science foundation
- [ ] Finalize question, target window, budget, metrics (Section 2).
- [ ] `data.py`: load, filter, featurize, define the top set. Print pool size and top-set size.
- [ ] `oracle.py`: budget-enforced reveal.
- [ ] `run_baselines.py`: random baseline curve over 10 seeds. **This is your first deliverable.**
- [ ] Sanity check: random hit rate ~5%.
- [ ] *Delegate to Devin/opencode:* data loader, oracle, surrogate, baseline runner (give them the signatures in this plan).

### Phase 2: Hours 4-9, Non-agent loop works
- [ ] `surrogate.py` and `strategies.py` implemented. Greedy and uncertainty arms run end-to-end.
- [ ] Confirm greedy and/or uncertainty beat random (otherwise debug the features/model before adding agents).
- [ ] `schemas.py` handoff contracts and `record.py` logger.

### Phase 3: Hours 9-14, Omnigent agents
- [ ] Implement the 7 agents with specs in `agents/`.
- [ ] Wire handoffs in Omnigent: Literature -> Insight -> Planner -> Runner -> Analysis -> Record, with Safety gating.
- [ ] Define tool permissions (Runner only gets the oracle; Safety gates the recommend action).
- [ ] Run **one complete loop** (even rough). Log it.
- [ ] **Checkpoint at hour 14: one end-to-end loop must exist.** If not, cut scope (e.g., drop the Literature API and use a pre-fetched citation set).

### Phase 4: Hours 14-19, The discovery moment and rigor
- [ ] Engineer the hypothesis-refutation -> strategy-switch example (Section 6.5).
- [ ] Run the agentic arm across >= 10 seeds (cache LLM outputs where possible to control cost and time).
- [ ] `analyze_results.py`: curves, speedup table, error bars.
- [ ] Add a control: agentic loop with the Analysis agent disabled (ablation), to show the feedback matters.
- [ ] Verify every literature claim has a real, working citation link.

### Phase 5: Hours 19-22, Package
- [ ] README: question, method, results, honest limitations, validation still needed, how to reproduce.
- [ ] Final figures (hits vs. evaluations, speedup bars).
- [ ] Document policies and human-approval gates.
- [ ] Write "what would reach 10x at scale" (see Section 10).

### Phase 6: Hours 22-24, Demo and submit
- [ ] Record the 2-minute demo (script below). Do a second take.
- [ ] Final repo push. Fresh-clone test on a clean environment.
- [ ] Submit: repo, agent specs and policies, demo, cited evidence, code and results, measured improvement, next experiment.

---

## 9. Two-Minute Demo Script

| Time | Content |
|---|---|
| 0:00-0:15 | **Question + bottleneck.** "Expensive evaluations are the bottleneck; can agents find good materials with fewer?" |
| 0:15-0:40 | **Agent handoffs live in Omnigent.** Literature (cited claims) -> Insight (3 labeled hypotheses) -> Planner (chose strategy A over B, with reasoning) |
| 0:40-1:05 | **Experiment runs.** Runner reveals a batch; show budget counter and hits |
| 1:05-1:30 | **The surprise.** Analysis refutes H1; planner switches strategy; hit rate recovers |
| 1:30-1:50 | **Result.** Curve vs. random baseline + measured speedup (e.g., "3.4x +/- 0.6 fewer evaluations") |
| 1:50-2:00 | **Next step.** Safety agent flags the shortlist for human approval; DFT validation proposed; path to 10x |

---

## 10. Path to 10x (for the write-up)

State plainly what you measured, then explain what would be needed at scale:
- Replace the oracle with real DFT jobs (parallelized on Databricks compute) so evaluations are genuinely expensive.
- Larger candidate pools (millions, from Materials Project / generative models) where random search is hopeless and the gap widens.
- Batch-parallel experiments and better surrogates (graph neural networks on structure).
- Multi-property objectives (gap + stability + toxicity).
- Literature agents that continuously update priors.

Do **not** claim 10x unless you measured it.

---

## 11. Scoring Alignment

| Criterion | Weight | How this plan earns it |
|---|---|---|
| Omnigent orchestration | 30% | 7 specialist agents, structured handoffs, tool permissions, policies, parallel work, live demo through Omnigent |
| Breakthrough potential | 25% | Credible path from benchmark to real materials screening; clear scaling story |
| Discovery acceleration and learning | 20% | Measured speedup with error bars; result visibly changes the next decision |
| Scientific rigor | 15% | Baselines, multi-seed, ablation, citations, uncertainty labeled, reproducible code |
| Creativity and responsibility | 10% | Labeled agent hypotheses, human approval gate, honest limitations |

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Omnigent setup eats hours | Do it first (Phase 0). Keep a plain-Python fallback for the science code so only orchestration is at risk |
| Surrogate doesn't beat random | Start with composition features, tune early, pick a target window with enough signal. Check at hour 9 |
| Agentic arm shows no speedup | Report honestly. Show the analysis of why and what was learned. Strength of evidence beats a big multiplier |
| LLM calls too slow/costly for 10 seeds | Cache agent outputs, use a cheaper model for Insight/Analysis, parallelize seeds |
| Literature API flakiness | Pre-fetch and cache citations at hour 1; verify DOIs/URLs manually |
| Hallucinated citations | Literature agent only returns items from real API results; Safety agent blocks uncited claims |
| matminer install problems | Fallback to hand-built element-property features |
| Scope creep | One dataset, one property, one loop. Freeze features at hour 19 |

---

## 13. Using Devin and opencode Effectively

- **Give them specs, not vague goals.** Paste the relevant section (function signatures, I/O schemas) from this plan.
- **Good delegation:** data loader, oracle with budget enforcement, Pydantic schemas, baseline runner, plotting, README skeleton, unit tests.
- **Keep for yourself:** agent decision logic, handoff design, the engineered refutation scenario, Omnigent wiring decisions, final claims.
- **Run several in parallel:** one agent on `src/` science code while another drafts agent specs and policies.
- **Always review** generated code that touches the oracle. A leak (labels visible to the model) would invalidate the whole result. Add a test that asserts unrevealed labels are unreachable.

---

## 14. Final Submission Checklist

- [ ] Repo public with clear README and one-command reproduction
- [ ] `agents/` specs and `policies/` committed
- [ ] Omnigent workflow config committed, with the live loop shown in the demo
- [ ] `records/research_log.jsonl` from a real run
- [ ] Results: curves, speedup table (mean +/- std, N seeds), ablation
- [ ] Every factual claim cited; agent hypotheses labeled; uncertainty preserved
- [ ] Limitations stated: retrospective benchmark, proxy oracle, validation needed (DFT then wet lab)
- [ ] Next experiment stated and justified by what the lab learned
- [ ] 2-minute demo uploaded
- [ ] Fresh-clone test passed

---

## 15. Stretch Goals (only if ahead of schedule)

- Second target property to show generality
- Parallel independent hypothesis-test branches in Omnigent
- Real DFT-lite check (e.g., a fast ML interatomic potential) on the top 3 candidates
- Simple dashboard displaying the research log and curve live
