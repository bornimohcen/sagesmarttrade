Title: [AI-PROPOSED] <short description>

Description:
- What changed:
- Rationale:
- Tests run: (unit tests, lint)
- Backtest results: baseline vs experiment (attach experiment_report.json if applicable)
- Canary plan: allocate 1% of capital for 72 hours, metrics to watch: PnL, drawdown, avg slippage
- Rollback criteria: e.g., negative return > X% in 24h OR drawdown > Y%

Checklist:
- [ ] Labeled as `ai-proposed`
- [ ] No secrets or credentials in code or logs
- [ ] Includes tests and/or reproducible evaluation
- [ ] Passes `scripts/verify_installation.py` (no secret leakage)
- [ ] Passes `scripts/startup_check.py`
- [ ] Risk limits unchanged or explicitly justified and approved
- [ ] Kill-switch behavior unaffected and verified

Requires: @human_approver

