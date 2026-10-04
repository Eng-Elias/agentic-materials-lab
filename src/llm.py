"""LLM completion cache + provider dispatch.

Cache key = sha256(agent|model|seed|prompt). Every entry records which
backend produced it so deterministic fallbacks are never mistaken for
model outputs (constitution: honesty).

Providers (env):
  LLM_PROVIDER   engine (default) | openai | anthropic
  LLM_MODEL      model name (required for real providers)
  LLM_BASE_URL   endpoint; defaults: https://api.openai.com/v1,
                 https://api.anthropic.com
  LLM_API_KEY    shared key override; else OPENAI_API_KEY /
                 ANTHROPIC_API_KEY
Provider-specific base URLs also honoured: OPENAI_BASE_URL,
ANTHROPIC_BASE_URL. `openai` works with any OpenAI-compatible
/chat/completions endpoint (OpenAI, Databricks serving, vLLM, Ollama, ...).
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Callable

import requests

Backend = Callable[[str, str], str]  # (agent, prompt) -> completion text

DEFAULT_MODEL = "deterministic-engine-v1"


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
                           "and no backend configured")
    output = backend(agent, prompt)
    path.write_text(json.dumps({
        "agent": agent, "model": model, "seed": seed,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt": prompt, "output": output,
    }, indent=1))
    return {"output": output, "cache_hit": False, "key": key}


# --- provider backends -------------------------------------------------------

def _openai_backend(base_url: str, api_key: str, model: str) -> Backend:
    def call(agent: str, prompt: str) -> str:
        r = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model,
                  "messages": [{"role": "system", "content": f"You are the {agent} agent."},
                               {"role": "user", "content": prompt}],
                  "temperature": 0},
            timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    return call


def _anthropic_backend(base_url: str, api_key: str, model: str) -> Backend:
    def call(agent: str, prompt: str) -> str:
        r = requests.post(
            f"{base_url.rstrip('/')}/v1/messages",
            headers={"x-api-key": api_key,
                     "anthropic-version": "2023-06-01"},
            json={"model": model, "max_tokens": 4096,
                  "system": f"You are the {agent} agent.",
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))
    return call


def provider_from_env() -> tuple[str, str, Backend | None]:
    """Return (provider, model, backend). 'engine' -> deterministic caller
    supplied by run code; real providers -> HTTP backend."""
    provider = os.environ.get("LLM_PROVIDER", "engine").lower()
    if provider == "engine":
        return provider, DEFAULT_MODEL, None
    model = os.environ.get("LLM_MODEL")
    key = os.environ.get("LLM_API_KEY")
    if provider == "openai":
        base = os.environ.get("LLM_BASE_URL") or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1")
        key = key or os.environ.get("OPENAI_API_KEY")
        if not (model and key):
            raise RuntimeError("LLM_PROVIDER=openai needs LLM_MODEL and "
                               "LLM_API_KEY/OPENAI_API_KEY")
        return provider, model, _openai_backend(base, key, model)
    if provider == "anthropic":
        base = os.environ.get("LLM_BASE_URL") or os.environ.get(
            "ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        key = key or os.environ.get("ANTHROPIC_API_KEY")
        if not (model and key):
            raise RuntimeError("LLM_PROVIDER=anthropic needs LLM_MODEL and "
                               "LLM_API_KEY/ANTHROPIC_API_KEY")
        return provider, model, _anthropic_backend(base, key, model)
    raise RuntimeError(f"unknown LLM_PROVIDER={provider!r} "
                       "(expected engine|openai|anthropic)")
