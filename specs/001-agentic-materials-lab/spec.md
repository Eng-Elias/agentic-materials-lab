# Feature Specification: Agentic Materials Discovery Lab

**Feature Branch**: `001-agentic-materials-lab`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Build an agentic materials discovery lab. Read docs/PLAN.md for full detail; summarize rather than invent. WHAT: A closed-loop system where specialist agents search the NIST JARVIS dft_3d dataset for materials whose band gap falls in a target window (1.2-1.8 eV, optionally with ehull below 0.1 eV/atom), using as few simulated expensive evaluations as possible. WHY: Expensive evaluations are the bottleneck in materials discovery; measurable outcome is evaluations needed to find the top ~5% of candidates versus a random baseline (speedup = N_random / N_agentic at the same hit count, mean and std over at least 10 seeds)."

**Source of truth**: `Databricks: Agentic Scientific Discovery PLAN.md` (repository root) — this spec summarizes it and does not extend it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Objective and Measure Discovery Efficiency (Priority: P1)

A scientist sets the scientific objective (target band gap window 1.2-1.8 eV, optionally with
ehull below 0.1 eV/atom), the evaluation budget (300 evaluations in 6 rounds of 50), and the
candidate pool, then runs the core benchmark. Because true property labels exist but are
hidden, "revealing a label" simulates a costly DFT experiment and costs budget. The system
reports how many evaluations each search strategy (random, greedy, uncertainty) needs to find
the top ~5% of candidates over at least 10 fixed seeds.

**Why this priority**: This is the scientific core and the MVP. Baselines that run correctly
and reproduce already constitute a valid deliverable, and nothing downstream (agents,
orchestration) is meaningful without a validated oracle and baseline curves.

**Independent Test**: Run the baseline experiment end-to-end and verify the random arm's hit
rate matches the top-set fraction (~5%), results are reproducible under fixed seeds, and
unrevealed labels are provably unreachable (dedicated leak test passes).

**Acceptance Scenarios**:

1. **Given** a configured budget of 300 and a candidate pool with a defined top set, **When** the scientist runs the random/greedy/uncertainty arms for 10 seeds, **Then** the system produces per-arm hits-vs-evaluations results that are reproducible under the same seeds.
2. **Given** labels are initially hidden, **When** any agent, model, pipeline, or log requests a label, **Then** that label is obtainable only by spending budget through the enforced accountant, and any attempt to access an unrevealed label is rejected.
3. **Given** a batch request larger than the remaining budget or one containing already-revealed candidates, **When** the reveal is requested, **Then** it is refused and the budget is unchanged.

---

### User Story 2 - Watch the Agentic Discovery Loop (Priority: P2)

The scientist observes one complete orchestrated loop: Literature agent returns cited claims
about predictors of the target property → Insight agent proposes labeled, testable hypotheses →
Planner scores at least two experiment strategies and selects one with a stated rationale
(recording the rejected alternative) → Runner executes the batch under budget → Analysis agent
interprets results and issues hypothesis verdicts → the Research Record logs every handoff.

**Why this priority**: This is the orchestrated, agentic differentiator of the system, but it
depends on P1's validated science core. Orchestration is mandatory per project constitution
(Principle IX).

**Independent Test**: Run one complete loop for one seed and inspect the log: every stage's
structured message validates against the handoff contract and appears in the record with
run_id and seed.

**Acceptance Scenarios**:

1. **Given** evidence claims about the target property, **When** the scientist inspects them, **Then** every claim carries a real, verifiable citation (DOI or URL) drawn from an actual literature search response, and no uncited claim is presented as fact.
2. **Given** hypotheses are proposed, **When** the scientist inspects them, **Then** each is labeled AGENT-GENERATED and states a testable feature set, predicted direction, and supporting citations.
3. **Given** the planner must act each round, **When** it selects a batch strategy, **Then** its output includes the chosen strategy, rationale, expected learning, cost, and the rejected alternative(s) with reasons.
4. **Given** the runner has completed a batch, **When** the analysis agent reports, **Then** its report includes hypothesis verdicts (supported/refuted/inconclusive with evidence), a strategy recommendation, and any surprises.

---

### User Story 3 - Result Changes the Decision (Priority: P2)

When evidence contradicts a hypothesis, the scientist sees the analysis agent refute it
(e.g., a plausible-but-wrong guiding rule whose exploitation plateaus at or below random for
two consecutive rounds), the planner switch strategy in response, and the subsequent hit rate
recover — demonstrating a measurable "result changes the decision" moment.

**Why this priority**: This is the explicit demonstration that the feedback loop matters,
earning the discovery-acceleration part of the evaluation. It depends on P2's loop.

**Independent Test**: Run the reproducible designed scenario (fixed seed) and inspect the
trace: the refutation is logged with evidence for two consecutive below-baseline rounds, the
strategy change is logged with reasons, and the hit curve visibly responds afterward.

**Acceptance Scenarios**:

1. **Given** an exploit strategy guided by a misleading hypothesis, **When** the hit rate falls to or below random for two consecutive rounds, **Then** the analysis agent marks the hypothesis REFUTED with quantitative evidence and recommends a strategy change.
2. **Given** a refutation recommendation, **When** the planner acts in the next round, **Then** it selects a different strategy (hybrid or explore), logs the reason, and the recovered hit rate is visible in results.

---

### User Story 4 - Human Approval for Consequential Actions (Priority: P2)

The scientist must personally approve: any recommendation of candidates for real-world
synthesis or DFT validation, any budget increase, and any intent to report an uncited claim
as fact. These actions are blocked by enforced permissions/policies (not prompts) until
approved.

**Why this priority**: Core responsibility requirement, enforced structurally. Must exist for
the demo and submission regardless of scale.

**Independent Test**: Attempt each consequential action without approval and verify it is
denied by the permission/policy layer; then approve and observe only the post-approval path
performing the action.

**Acceptance Scenarios**:

1. **Given** the runner agent, **When** it attempts any consequential action (e.g., recommend for validation), **Then** the permission layer denies it because such capability is not granted to that agent.
2. **Given** a final shortlist exists, **When** a human approves it, **Then** the recommendation proceeds via the approved path and both the request and decision are recorded.

---

### User Story 5 - Reconstruct Every Decision as a Reviewer (Priority: P3)

A reviewer replays any decision end-to-end from the append-only research record: every handoff
with timestamp, agent, run_id, seed, input hash, output, and citations; every strategy
rejection; every verdict; every approval.

**Why this priority**: Auditability supports scientific rigor scoring, but the loop can run
with simpler logging first; full fidelity is layered on.

**Independent Test**: Pick any logged strategy decision and reconstruct its full decision
context from the record alone.

**Acceptance Scenarios**:

1. **Given** any completed run, **When** the reviewer filters the record by run_id, **Then** the complete ordered chain of handoffs, verdicts, rejections, and approvals is present and self-consistent.

---

### Edge Cases

- Budget exhaustion mid-round: remaining budget must be honored exactly; reveals never overspend; run ends cleanly at zero.
- Top-set fraction far from ~5%: pool/window configuration must warn and be adjustable before runs.
- Refutation scenario does not trigger naturally: reported honestly as a designed scenario in the README rather than misrepresented as emergent.
- Literature services unavailable or rate-limited: cached responses are used; no claim is fabricated, and uncited material is blocked from being reported as fact.
- Agentic arm does not beat the best non-agentic baseline: reported exactly as measured, with analysis of why.
- Malformed agent handoff message: rejected by contract validation, never silently logged or acted upon.
- Ablation disabled: with the analysis agent's feedback removed, the planner cannot adapt — accepted and recorded as the ablation arm, not treated as an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the scientist configure the scientific objective: target property, target window (default band gap 1.2-1.8 eV with optional stability filter), evaluation budget (default 300, in 6 rounds of 50), and pool size (default subsample of 10-20k with fixed seed).
- **FR-002**: The system MUST maintain property labels behind an enforced accountant ("oracle"): reveals cost one budget unit each, over-budget and duplicate reveals are refused, and no code path exposes unrevealed labels — verified by an automated leak test.
- **FR-003**: The system MUST define the top set (~5% of pool) from the objective and report pool size, top-set size, and fraction before experimentation.
- **FR-004**: The system MUST run four comparable search arms under identical seeds and budgets: random, greedy (top predicted-in-window), uncertainty (highest-model-variance), and agentic (planner-adaptive). All arms begin with a random seeding batch of 50 so predictions start with data.
- **FR-005**: The system MUST retrain its predictive model after every round using all revealed (features, label) data, and expose both a prediction and an uncertainty per candidate.
- **FR-006**: Each round, the planner MUST score at least two candidate strategies (from: exploit, explore, hybrid/UCB, hypothesis-test) on expected learning, feasibility, and cost, select one, and record the rejected alternative(s) and reasons.
- **FR-007**: Every inter-agent message MUST conform to a versioned, validated handoff contract; malformed messages MUST be rejected.
- **FR-008**: Every handoff MUST be appended to an append-only research record with timestamp, agent, run_id, seed, input hash, output, and citations.
- **FR-009**: Every literature claim MUST carry a citation traceable to a cached real search response (DOI or URL); the system MUST prevent uncited claims from being reported as fact without approved override.
- **FR-010**: Hypotheses MUST carry the AGENT-GENERATED label, a testable feature set, a predicted direction, and citation links; unlabeled hypotheses MUST be rejected by validation.
- **FR-011**: Consequential actions (candidate recommendations for real synthesis/DFT, budget increases, reporting uncited claims as fact) MUST be blocked by enforced permissions/policies pending human approval; the runner MUST NOT possess such capabilities.
- **FR-012**: The system MUST measure, per arm: hits vs evaluations curve, evaluations to reach 50% of the top set, and speedup (random evaluations / agentic evaluations at the same hit count) as mean ± std over ≥10 seeds; plus predictive error per round and strategy-switch counts.
- **FR-013**: The system MUST support an ablation arm: the agentic loop with analysis feedback disabled, recorded distinctly.
- **FR-014**: The system MUST produce a results table and hits-vs-evaluations plot including all arms and the ablation.
- **FR-015**: The README MUST state limitations (retrospective benchmark, proxy/simulated experiment, composition features only, designed refutation scenario) and the validation still needed (DFT, then wet lab). Only measured numbers may be reported.
- **FR-016**: The system MUST reproduce with pinned dependencies under one command from a fresh clone.

### Key Entities

- **Candidate Material**: A dataset entry with composition-derived features and a hidden true property value; identified by a stable id.
- **Oracle/Accountant**: The sole custodian of labels and budget consumption; never exposes unrevealed values.
- **Claim/Citation**: A factual statement plus its verifiable source, cached from a real search response.
- **Hypothesis**: An AGENT-GENERATED, testable prediction over a feature set with citations and a verdict history (supported/refuted/inconclusive).
- **Experiment Spec**: A planner's per-round decision: strategy, batch ids, rationale, expected learning, cost, and rejected alternatives.
- **Run Result**: A runner's executed batch: revealed values, hits, cumulative hits, budget remaining, run_id, seed.
- **Handoff**: A validated, logged inter-agent message forming the auditable discovery loop.
- **Research Record**: The append-only log enabling full decision reconstruction.

### Out of Scope

- New physical discovery claims (retrospective benchmark only)
- Graph neural networks or structure-based models
- Real DFT execution or wet-lab work
- Multiple datasets or a second target property
- Any agent framework other than the mandated orchestrator

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer completes full reproduction — baselines, the agentic loop, and all result figures — from a fresh clone with one command, at most one environment-setup step, and no manual data fixes, using only pinned dependencies and fixed seeds.
- **SC-002**: All five arms' curves (random, greedy, uncertainty, agentic, ablation) over ≥10 seeds, plus strategy-switch counts and the 50%-of-top-set evaluations metric per arm, are produced and internally consistent with the logged record.
- **SC-003**: Speedup (random vs. agentic at equal hit count) is reported as mean ± std over ≥10 seeds exactly as measured — including if it is ≤ 1 — and every arm's deviation between repeated same-seed runs is zero.
- **SC-004**: 100% of agent handoffs in the logged record validate against the handoff contract; 0 malformed messages are acted upon.
- **SC-005**: The oracle leak test, budget-enforcement test, and handoff-contract test pass; 0 unrevealed labels are reachable through any agent, model output, or log (verified by test).
- **SC-006**: 100% of factual claims presented to the scientist carry verifiable citations that resolve; 0 fabricated citations are present.
- **SC-007**: The designed refutation scenario is reproducible on its fixed seed: the hypothesis is marked refuted after two consecutive below-baseline rounds, a strategy change follows, and the recovery is visible in the curve.
- **SC-008**: A scientist can audit any single experiment decision end-to-end from the record alone within 5 minutes.

## Assumptions

- The JARVIS `dft_3d` dataset is downloadable publicly and a 10-20k-row subsample is sufficient to expose measurable differences among strategies.
- "Expensive evaluation" is simulated by budget-costly label revelation; this retrospective proxy is stated honestly rather than claimed as a new physical discovery.
- The default target window (1.2-1.8 eV) yields roughly a 5% top-set fraction; if the observed fraction deviates substantially, the window is adjusted before runs and noted.
- Composition-only (no structure) features are sufficient for the predictive model to beat random; otherwise the window/features are tuned before agents are built (explicit decision gate before hour 9).
- Cached literature responses replace live calls under failure/rate limits without loss of claim verifiability.
- "At least 10 seeds" is the minimum; more is acceptable when runtime allows thanks to caching.
- One scientist operating the lab is the primary user; reviewers read artifacts (README, results, log) afterwards.
- The plan referenced as `docs/PLAN.md` is authored at the repository root as `Databricks: Agentic Scientific Discovery PLAN.md`.
