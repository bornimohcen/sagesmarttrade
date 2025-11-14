Phase 0 Setup (Prep & Safety)

1) Secrets
- Copy `config/secrets.env.example` to `config/secrets.env` and fill real values.
- Do not commit `config/secrets.env` (it is ignored in `.gitignore`).

2) Installation check
- Run: `python3 scripts/verify_installation.py`
- Expected: required keys are reported as present, with their values masked.

3) Startup health check
- Run: `python3 scripts/startup_check.py`
- Expected: `OK: startup_check passed.`
- Optional network check: `python3 scripts/startup_check.py --check-network`

4) Kill-switch
- Emergency stop: `python3 scripts/emergency_stop.py --reason "testing"`
- Check status: `python3 scripts/kill_switch_status.py`
- Resume trading: `python3 scripts/emergency_resume.py`

5) Governance policy
- Review `AI_POLICY.md` and confirm adherence.
- For any AI-generated PR, add label `ai-proposed` and use `.github/PULL_REQUEST_TEMPLATE.md`.

6) CI / GitHub Secrets (optional at this stage)
- Create GitHub Secrets for production credentials if you plan to run CI.
