# Building the Agentic Materials Discovery Lab with Spec Kit

A round-by-round guide with commands and copy-paste prompts. It assumes you have `PLAN.md` (the project plan) open as your source of truth.

> **Verify first.** Spec Kit changes quickly. Command names, flags and supported agents below are from memory. Run `specify --help` and `specify check`, and read the repo README (github.com/github/spec-kit) before relying on exact syntax. Newer versions name the slash commands `/speckit.*`; older ones used `/constitution`, `/specify`, and so on. Use whichever your install shows.

---

## How the Rounds Fit the 24 Hours

| Round | Hours | Goal | Output |
|---|---|---|---|
| 0 | 0-1 | Omnigent running + Spec Kit installed | Two agents exchanging JSON; repo initialized |
| 1 | 1-2 | Constitution + spec | `constitution.md`, `spec.md` |
| 2 | 2-3 | Plan + tasks | `plan.md`, `tasks.md` |
| 3 | 3-8 | Implement the science core (no agents yet) | Oracle, data, surrogate, baselines |
| 4 | 8-14 | Implement Omnigent agents + first full loop | End-to-end loop logged |
| 5 | 14-19 | Discovery moment, multi-seed runs, ablation | Speedup numbers + curves |
| 6 | 19-24 | Package, demo, submit | README, demo, final push |

**Rule:** Time-box Rounds 1-2 to about 2 hours total. If Spec Kit slows you down, fall back to working from `PLAN.md`.

---

## Round 0: Setup (Hour 0-1)

### 0.1 Get Omnigent working FIRST (30% of score)
- Databricks route: sign in, open `<workspace-url>/omnigent`, New session, Sandbox.
- Or open-source: install Omnigent from GitHub, run `omnigent`, select your model/harness.
- **Pass/fail test:** two agents exchange a structured JSON message through Omnigent. If this fails, ask mentors immediately.

### 0.2 Install Spec Kit
```bash
# requires uv and Python 3.11+
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify check
```

### 0.3 Initialize the project
```bash
mkdir agentic-materials-lab && cd agentic-materials-lab
git init
specify init . --here --ai <your-agent>
```
- Replace `<your-agent>` with a value from `specify init --help` (check whether `opencode` is listed). If your tool (opencode, Devin) isn't supported, pick any supported option to generate the files, then paste the generated prompts manually into your tool.
- Commit: `git add -A && git commit -m "init spec kit"`

### 0.4 Add your source documents
```bash
mkdir -p docs
cp /path/to/PLAN.md docs/PLAN.md
cp /path/to/Databricks__Agentic_Scientific_Discovery.pdf docs/challenge-brief.pdf
```

### 0.5 Add dependencies file
Create `requirements.txt`:
```
jarvis-tools
matminer
scikit-learn
lightgbm
pydantic
pandas
numpy
matplotlib
requests
duckdb
pytest
```
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "from jarvis.db.figshare import data; d=data('dft_3d'); print(len(d))"
```
If that import or call fails, check the jarvis-tools docs for the current loader name.

**Exit criteria:** Omnigent two-agent test passes, JARVIS loads, repo committed.

---

## Round 1: Constitution and Specification (Hour 1-2)

### 1.1 Constitution
Run `/speckit.constitution` (or `/constitution`) with this prompt:

```
Create a project constitution for an agentic scientific discovery lab built in 24 hours for a hackathon. Principles:

1. SCIENTIFIC HONESTY: Report only measured results. Never claim a speedup that was not observed. State that this is a retrospective benchmark using held-out labels from NIST JARVIS, not a new physical discovery.
2. ORACLE INTEGRITY: Unrevealed labels must never be reachable by any agent, model, feature pipeline or log. All label access goes through a budget-enforced oracle. A pytest must assert this.
3. CITATIONS: Every factual claim from an agent must carry a real, verifiable citation (DOI or URL) from an actual API response. No uncited claims reported as fact.
4. LABELING: All agent-generated hypotheses are labeled AGENT-GENERATED. Uncertainty is preserved and surfaced.
5. HUMAN APPROVAL: Consequential actions (recommending candidates for synthesis or DFT, increasing the budget) require human approval, enforced through tool permissions and Omnigent policies, not just prompts.
6. RECONSTRUCTABILITY: Every handoff between agents is validated against a Pydantic schema and appended to records/research_log.jsonl with run_id and seed.
7. REPRODUCIBILITY: Fixed seeds, pinned requirements, one-command reproduction.
8. SCOPE DISCIPLINE: One dataset (JARVIS dft_3d), one target property, one discovery loop. Out of scope: GNNs, real DFT, vector databases, extra agent frameworks beyond Omnigent.
9. ORCHESTRATION: Omnigent must orchestrate the live workflow. Specialist agents exchange structured outputs, use tools, and adapt their plan after experimental results.
10. TESTING: Minimal but real: oracle-leak test, schema validation test, budget-enforcement test.
```

**Review:** Read it once. Delete anything vague. Commit.

### 1.2 Specification
Run `/speckit.specify` with:

```
Build an agentic materials discovery lab. Read docs/PLAN.md for full detail; summarize rather than invent.

WHAT: A closed-loop system where specialist agents search the NIST JARVIS dft_3d dataset for materials whose band gap falls in a target window (1.2-1.8 eV, optionally with ehull below 0.1 eV/atom), using as few simulated expensive evaluations as possible.

WHY: Expensive evaluations are the bottleneck in materials discovery. The measurable outcome is evaluations needed to find the top ~5% of candidates versus a random baseline (speedup = N_random / N_agentic at the same hit count, mean and std over at least 10 seeds).

USER STORIES:
- As a scientist, I set the objective, target window and evaluation budget.
- As a scientist, I see cited literature claims and labeled agent-generated hypotheses.
- As a scientist, I see the planner compare at least two experiment strategies and choose one with a stated rationale.
- As a scientist, I watch the runner reveal a batch of labels under a budget, and see the analysis agent interpret the result.
- As a scientist, when a hypothesis is refuted, I see the planner change strategy and the hit rate respond.
- As a scientist, I must approve any recommendation for real-world synthesis or validation.
- As a reviewer, I can reconstruct every decision from the research log.

AGENTS (each owns one decision): Literature, Insight, Planner, Runner, Analysis, Research Record, Safety/Approval. Details in docs/PLAN.md section 4.

ACCEPTANCE CRITERIA:
- Random, greedy and uncertainty baselines run over at least 10 seeds.
- One complete Omnigent-orchestrated loop: Question, Evidence, Hypothesis, Experiment, Result, Updated decision.
- A documented example where analysis refutes a hypothesis and the planner switches strategy.
- Ablation: agentic loop with the Analysis agent disabled.
- Results table and hits-vs-evaluations plot.
- README states limitations and the validation still needed (DFT, then wet lab).

NON-GOALS: new physical discovery claims, GNNs, real DFT, multiple datasets.
```

### 1.3 Clarify (optional, 10 minutes max)
Run `/speckit.clarify`. Answer from `docs/PLAN.md`. Skip questions that are out of scope.

**Exit criteria:** `constitution.md` and `spec.md` committed.

---

## Round 2: Plan and Tasks (Hour 2-3)

### 2.1 Technical plan
Run `/speckit.plan` with:

```
Tech stack: Python 3.11+, Omnigent for orchestration, jarvis-tools for data, matminer Magpie composition features (fallback: hand-built element-property statistics), scikit-learn RandomForest (tree variance as uncertainty) or LightGBM, pydantic for schemas, requests for OpenAlex and arXiv with on-disk caching, JSONL for the research record, matplotlib for plots, pytest.

Repository structure:
agents/ (one spec .md per agent: decision owned, tools, input schema, output schema)
policies/ (tool_permissions.yaml, approval_rules.yaml)
omnigent/ (workflow config)
src/ (data.py, oracle.py, surrogate.py, strategies.py, tools_lit.py, schemas.py, record.py)
experiments/ (run_baselines.py, run_agentic.py, analyze_results.py)
records/ results/ demo/ tests/

Key design decisions:
- Oracle class holds labels privately; reveal(ids) decrements the budget and returns values; there is no other access path.
- Strategies: exploit, explore, hybrid (UCB), hypothesis_test.
- Planner scores at least two strategies per round on expected learning, feasibility and cost, and records the rejected alternative.
- Handoffs are Pydantic models, validated on every exchange.
- Cache all LLM and API outputs to disk so multi-seed runs are fast and cheap.
- Runner only has the oracle tool; only a post-approval path can call recommend_for_validation.

Follow the constitution. Keep within the stated scope.
```

### 2.2 Tasks
Run `/speckit.tasks`. Then **edit the list by hand:**
- Cut anything outside scope.
- Make sure tasks are ordered: oracle and baselines first, agents second.
- Mark safe parallel tasks (e.g., schemas and baselines can run in parallel).

### 2.3 Analyze (optional)
Run `/speckit.analyze` once to catch spec/plan/task inconsistencies. Fix only the serious ones.

**Exit criteria:** `plan.md` and `tasks.md` committed. Total Rounds 1-2 under about 2 hours.

---

## Round 3: Science Core, No Agents Yet (Hour 3-8)

Implement in small slices. Run `/speckit.implement` per slice (or paste the tasks into your coding agent). **Commit after each slice and run the tests.**

### Slice 3.1: Data and oracle
```
/speckit.implement Implement only the tasks for src/data.py and src/oracle.py.

data.py: load JARVIS dft_3d, drop rows without a band gap, subsample 15000 rows with a fixed seed, featurize with matminer Magpie (fallback to element-property stats), define the top set as band gap in [1.2, 1.8] eV (and ehull < 0.1 if available), and print pool size and top-set size and fraction.

oracle.py: class Oracle holding labels privately. Methods: reveal(ids) -> values, which decrements the budget and raises if the budget is exceeded or an id was already revealed; budget_remaining(); hits_found(). No method may return unrevealed labels or the full label array.

Write tests/test_oracle.py: (1) budget cannot be exceeded, (2) unrevealed labels are not accessible via public attributes or methods, (3) double-reveal is rejected. Features passed to models must never include the target column.
```
**Check:** Top-set fraction is roughly 5%. If far off, adjust the window.

### Slice 3.2: Random baseline
```
/speckit.implement Implement experiments/run_baselines.py with the random baseline only. 10 seeds, budget 300, rounds of 50. Output results/baseline_random.csv with columns seed, round, evaluations, cumulative_hits. Also plot mean hits vs evaluations with std shading to results/baseline_random.png.
```
**Check:** Random hit rate is about the top-set fraction. **This is your first deliverable.**

### Slice 3.3: Surrogate and strategies
```
/speckit.implement Implement src/surrogate.py and src/strategies.py. Surrogate: RandomForestRegressor trained on revealed (features, labels); predict returns mean and std across trees. Strategies: exploit (highest probability or closeness to the target window), explore (highest uncertainty), hybrid (UCB-style combining both), each taking (pool_ids_not_revealed, surrogate, batch_size) and returning batch ids. Add greedy and uncertainty arms to run_baselines.py using the same seeds, budget and rounds. The first round for every arm is a random batch of 50 to seed the surrogate.
```
**Check:** Greedy and/or uncertainty beat random. If not, tune features, model and window **now**, before building agents. Decision point at about hour 9.

### Slice 3.4: Schemas, record, tests
```
/speckit.implement Implement src/schemas.py (Pydantic models for Citation, Hypothesis with an AGENT-GENERATED label field, ExperimentSpec, RunResult, AnalysisVerdict, Handoff) and src/record.py (append-only JSONL writer that logs timestamp, agent, run_id, seed, input hash, output, citations). Add tests/test_schemas.py: malformed handoffs are rejected; hypotheses without the label are rejected.
```

**Exit criteria:** Baselines (random, greedy, uncertainty) over 10 seeds, with a curve and passing tests.

---

## Round 4: Omnigent Agents and the First Full Loop (Hour 8-14)

> Omnigent specifics (how agents, tools and policies are declared) come from its docs. Read them before this round and paste the relevant syntax into your prompts.

### Slice 4.1: Literature tool and agent specs
```
/speckit.implement (1) Implement src/tools_lit.py: query OpenAlex (and arXiv as backup) for papers on predictors of band gap in inorganic materials, return title, authors, year, DOI/URL; cache responses to disk; never fabricate entries. (2) Write agents/*.md specs for all 7 agents using the template: decision owned, tools allowed, input schema, output schema, rules. Content is in docs/PLAN.md section 4.
```
**Manual step:** Pre-fetch and cache citations now, and click-check that the links are real.

### Slice 4.2: Policies
```
/speckit.implement Write policies/tool_permissions.yaml and policies/approval_rules.yaml. Permissions: Literature (search APIs only), Insight (read dataset stats and literature output, no oracle), Planner (surrogate queries and budget read, no oracle), Runner (oracle reveal and surrogate training only), Analysis (read results only), Record (append to log only), Safety (approval requests; sole path to recommend_for_validation). Approval required for: shortlist recommendation, any budget increase, reporting a claim without a citation.
```

### Slice 4.3: Omnigent workflow
```
/speckit.implement Create the Omnigent workflow in omnigent/ following the Omnigent docs [paste the relevant syntax here]. Wire: Literature -> Insight -> Planner -> Runner -> Analysis -> Record, with Safety gating the recommend step. Each handoff must validate against src/schemas.py and log through src/record.py. The Planner must score at least two strategies each round and record the rejected one. Enforce tool permissions from policies/tool_permissions.yaml.
```

### Slice 4.4: First end-to-end loop
```
/speckit.implement Create experiments/run_agentic.py that runs one complete loop for one seed through Omnigent: round 0 random seed batch, then at least 3 rounds of plan -> run -> analyze -> update. Save the research log to records/research_log.jsonl and the result to results/agentic_seed0.csv.
```

**Checkpoint at hour 14: one end-to-end loop exists and is logged.** If not, cut scope: drop live literature calls and use the cached citation set, or run Omnigent for only the highest-value handoffs (Planner -> Runner -> Analysis) and keep the rest deterministic.

---

## Round 5: Discovery Moment, Rigor, Results (Hour 14-19)

### Slice 5.1: Engineer the "result changes the decision" moment
```
/speckit.implement Add a seeded scenario where the Insight agent's top hypothesis is a plausible but misleading rule (for example, electronegativity difference alone predicts band gap). The planner initially uses an exploit strategy guided by it. Analysis must detect that the hit rate falls to or below random for two consecutive rounds, mark the hypothesis REFUTED with evidence, and recommend switching to hybrid or explore. The planner must then switch and log the reason. Make this reproducible with a fixed seed, and save a trace to records/refutation_example.jsonl.
```
If the refutation doesn't occur naturally, adjust the seeded hypothesis. Report it honestly as a designed scenario in the README.

### Slice 5.2: Multi-seed runs and ablation
```
/speckit.implement Extend run_agentic.py to run 10 seeds, with caching of LLM outputs. Add an ablation flag --no-analysis that disables the Analysis agent feedback so the planner cannot adapt. Output results/agentic.csv and results/ablation.csv.
```

### Slice 5.3: Analysis and plots
```
/speckit.implement Implement experiments/analyze_results.py. Produce: (1) hits vs evaluations for random, greedy, uncertainty, agentic and ablation with std shading; (2) evaluations needed to reach 50% of the top set, per arm; (3) speedup = N_random / N_agentic with mean and std; (4) results/summary.csv. Report numbers exactly as measured, including if agentic does not beat the best non-agentic baseline.
```

### Slice 5.4: Citation audit (manual)
Open every citation in the log and README and confirm it resolves. Remove any that don't.

**Exit criteria:** Speedup numbers with error bars, ablation, curves, refutation trace. **Freeze features and code at hour 19.**

---

## Round 6: Package, Demo, Submit (Hour 19-24)

### Slice 6.1: README
```
/speckit.implement Write README.md: question, bottleneck attacked, method, agent table (decision owned, tools, I/O), human approval gates and policies, results (embed plots, speedup table with mean and std and N seeds, ablation), the refutation example, limitations (retrospective benchmark, proxy oracle, composition features only, designed scenario), validation still needed (DFT then wet lab), the next experiment justified by what the lab learned, a section on what would be needed to approach 10x at scale, citations, and one-command reproduction instructions. Use only numbers from results/summary.csv.
```

### Slice 6.2: Demo script
Write `demo/script.md` using this structure and record it (aim for 2 minutes, two takes):

| Time | Content |
|---|---|
| 0:00-0:15 | Question and bottleneck |
| 0:15-0:40 | Omnigent handoffs live: Literature, Insight, Planner |
| 0:40-1:05 | Runner reveals a batch; budget counter and hits |
| 1:05-1:30 | Analysis refutes a hypothesis; planner switches strategy |
| 1:30-1:50 | Curve vs random; measured speedup |
| 1:50-2:00 | Safety agent flags the shortlist for approval; next experiment |

### Slice 6.3: Final checks
```bash
pytest -q
# fresh clone test
cd /tmp && git clone <your-repo-url> test-clone && cd test-clone
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python experiments/run_baselines.py --quick   # add a quick flag if useful
```

### Submission checklist
- [ ] Public repo with README and reproduction instructions
- [ ] `agents/` specs and `policies/` committed
- [ ] Omnigent workflow config committed
- [ ] `records/research_log.jsonl` from a real run
- [ ] Results: curves, speedup table (mean and std, N seeds), ablation
- [ ] Every claim cited, hypotheses labeled, uncertainty preserved
- [ ] Limitations and required validation stated
- [ ] Next experiment stated
- [ ] 2-minute demo uploaded
- [ ] Fresh-clone test passed

---

## Working Tips

- **One slice per implement call.** Giant prompts produce giant, hard-to-debug diffs. Commit after every slice.
- **Re-read the constitution** if your coding agent starts drifting (for example, adding GNNs or new frameworks).
- **Review everything that touches the oracle yourself.** A label leak invalidates the whole result.
- **Parallelize:** while one agent session builds `src/` science code, run another on agent specs and policies. They touch different files.
- **If Spec Kit stalls you,** drop the slash commands and paste the slice prompts above directly into opencode or Devin. The prompts work on their own.
- **Cut order if time runs short:** stretch goals, then the live literature calls (use cache), then the ablation, then extra strategies. Never cut the baselines, the Omnigent loop, or the honest README.
