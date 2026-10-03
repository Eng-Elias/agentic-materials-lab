import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.schemas import Handoff


def validate_handoff(message: dict) -> str:
    Handoff.model_validate(message)
    return "VALIDATION: ok"
