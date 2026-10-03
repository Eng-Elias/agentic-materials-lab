# Agent Spec: Knowledge / Research-Record Agent

- **Decision owned**: The shared append-only record.
- **Tools allowed**: `append_record` (src/record.py). Read-only elsewhere.
- **Input**: every handoff between agents.
- **Output**: JSONL lines `{timestamp (ISO-8601 UTC), agent, run_id, seed, input_hash (sha256 canonical), output, citations}` in `records/research_log.jsonl`.
- **Rules**:
  - Append-only: no edit or delete path exists.
  - Every handoff is logged — including rejected/invalid handoffs (logged with a validation error marker by the harness, never silently dropped).
  - Anyone must be able to reconstruct any decision from the record alone.
