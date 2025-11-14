AI Agent Governance Policy

Purpose
- Protect capital, ensure transparency, and prevent unauthorized actions.
- Define clear operational rules for any code or config changes proposed by the AI agent.

Core Principles
- Generate-only: the agent only generates changes as files/branches/PRs. It never merges or deploys directly.
- No auto-merge: all PRs created by the agent must be labeled `ai-proposed` and require at least one human approval.
- Secret safety: no secrets are stored in the repository. Locally they come from `config/secrets.env`; in CI they come from GitHub Secrets.
- Kill-switch: all components must check the emergency stop state before executing and must stop immediately when it is enabled.
- Full audit trail: every decision or change proposed by the agent should have recorded rationale, input signals, and confidence.

PR Rules for AI-generated Changes
1) PRs must be labeled: `ai-proposed`.
2) Attach relevant results/reports (backtests, paper trading, `experiment_report.json` when applicable).
3) Include tests and explanation: what changed, why, and how it was validated.
4) No secrets in code, logs, or configs (enforced both automatically and manually).
5) No changes to risk limits or capital allocation without explicit section, justification, and human approval.

Human Gates
- Gate A: approve this policy and verify kill-switch behavior before any automated trading development starts.
- Gate B: before the first live execution: engineering review + clear canary plan + rollback mechanism.

Operational Safety
- Parameters like `max_daily_loss_pct` and risk limits live in reviewable configuration files.
- Any change to stop rules or budgets requires dual confirmation (human review + authentication).

Merge and Deployment
- Merges are performed manually after review.
- Deployments should use canary rollout with a small portion of capital and immediate rollback if metrics degrade.

Required Checks
- `verify_installation`: confirms secrets exist without printing their values.
- `startup_check`: fails if secrets are missing, account is not ACTIVE, or kill-switch is enabled.
