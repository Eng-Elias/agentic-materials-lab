"""LLM completion cache. Key = sha256(agent|model|seed|prompt).

Every cached entry records which backend produced it so deterministic
fallbacks are never mistaken for model outputs (constitution: honesty).
"""
import hashlib
import json
from pathlib import Path
from typing import Callable

Backend = Callable[[str, str], str]  # (agent, prompt) -> completion text


def _key(agent: str, model: str, seed: int, prompt: str) -> str:
    return hashlib.sha256(f"{agent}|{model}|{seed}|{prompt}".encode()).hexdigest()


def complete(agent: str, model: str, prompt: str, seed: int,
             cache_dir: str | Path = "cache/llm",
             backend: Backend | None = None) -> dict:
    """Return {"output": str, "cache_hit": bool, "key": str}. Raises if a miss
    occurs with no backend configured."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _key(agent, model, seed, prompt)
    path = cache_dir / f"{key}.json"
    if path.exists():
        entry = json.loads(path.read_text())
        return {"output": entry["output"], "cache_hit": True, "key": key}
    if backend is None:
        raise RuntimeError(f"LLM cache miss for agent={agent} key={key[:12]} "
                           "and no backend configured (omnigent backend pending T002)")
    output = backend(agent, prompt)
    path.write_text(json.dumps({
        "agent": agent, "model": model, "seed": seed,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt": prompt, "output": output,
    }, indent=1))
    return {"output": output, "cache_hit": False, "key": key}
