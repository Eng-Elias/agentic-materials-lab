import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG = Path("records/research_log.jsonl")


def input_hash(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class ResearchRecord:
    def __init__(self, path: str | Path = DEFAULT_LOG):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, agent: str, run_id: str, seed: int, input_payload, output, citations=None) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "run_id": run_id,
            "seed": seed,
            "input_hash": input_hash(input_payload),
            "output": output,
            "citations": list(citations or []),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return entry

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
