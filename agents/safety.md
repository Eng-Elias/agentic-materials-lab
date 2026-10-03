# Agent Spec: Safety / Approval Agent

- **Decision owned**: Flagging and gating consequential actions.
- **Tools allowed**: `request_approval`, policy checker over `policies/*.yaml`; sole caller of `recommend_for_validation` (post-approval path only).
- **Input**: final-candidate shortlists, any budget-change intent, any claim about to be reported without a citation.
- **Output schema**: `ApprovalRequest` `{action ∈ recommend_for_validation|budget_increase|report_uncited_claim, justification}` → `ApprovalDecision` `{action, approved, approver}`.
- **Rules**:
  - Enforcement is by tool permissions and policies, not prompts. Other agents cannot self-approve.
  - Everything consequential pauses the workflow until a human answers; request and decision are both logged.
  - A denied approval leaves zero side effects.
