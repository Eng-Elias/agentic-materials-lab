#!/usr/bin/env bash
# Full benchmark reproduction: baselines -> 10-seed agentic -> ablation -> analysis.
set -euo pipefail
cd "$(dirname "$0")"

python experiments/run_baselines.py
python experiments/run_agentic.py --seeds 10
python experiments/run_agentic.py --seeds 10 --ablation
python experiments/analyze_results.py
python experiments/run_agentic.py --refutation-demo

echo "Done. See results/summary.csv, results/speedups.csv, results/curves.png"
echo "Refutation trace: records/refutation_example.jsonl"
