from src.schemas import Handoff


def validate_handoff(message: dict) -> str:
    Handoff.model_validate(message)
    return "VALIDATION: ok"
