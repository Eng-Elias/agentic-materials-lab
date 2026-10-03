from pathlib import Path

from ruamel.yaml import YAML

POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"


class PermissionDenied(PermissionError):
    pass


_yaml = YAML(typ="safe")
_PERM = _yaml.load((POLICIES_DIR / "tool_permissions.yaml").read_text())
RULES = _yaml.load((POLICIES_DIR / "approval_rules.yaml").read_text())

GRANTS: dict[str, set[str]] = {k: set(v) for k, v in _PERM["permissions"].items()}
GATED_ACTIONS = set(RULES["gated_actions"])


def allowed(agent: str, tool: str) -> bool:
    return tool in GRANTS.get(agent, set())


def require(agent: str, tool: str):
    if _PERM.get("deny_all_others", True) and not allowed(agent, tool):
        raise PermissionDenied(f"agent '{agent}' may not call tool '{tool}'")


def require_approval_authorized(agent: str, action: str) -> bool:
    if action not in GATED_ACTIONS:
        raise ValueError(f"unknown gated action: {action}")
    return agent == "safety"


# --- Omnigent policy adapters ---
# Handler signature note: Omnigent guards inspect tool-call events before execution.
# make_permission_policy returns a callable(constext) raising PermissionDenied unless the
# agent is granted the tool. Verify the exact kwarg names against the Omnigent runtime
# during the T002 smoke test; the factory shape matches the documented
# `type: function / factory_params` contract (docs/AGENT_YAML_SPEC.md, ## Policies).

def make_permission_policy(agent: str):
    def guard(**event):
        tool = event.get("tool_name") or event.get("tool") or event.get("name")
        if tool is not None:
            require(agent, str(tool))
    guard.__name__ = f"permission_guard_{agent}"
    return guard


def make_approval_policy():
    def guard(**event):
        tool = event.get("tool_name") or event.get("tool") or event.get("name")
        agent = event.get("agent")
        if tool == "recommend_for_validation" and agent != "safety":
            raise PermissionDenied(
                "recommend_for_validation may only run on the safety post-approval path"
            )
    return guard
