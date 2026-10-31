# Gridiron Edge Pro — development agent instructions

## Mission
Implement ROADMAP.md in small, reviewable increments. Never fabricate betting odds, injuries, forecasts, or model validation.

## Autonomous workflow
1. Read ROADMAP.md and current source files; select the earliest actionable unchecked task.
2. Create a dedicated feature branch. Never push directly to main.
3. Make one coherent improvement with tests, input validation and user-facing caveats.
4. Run `python -m compileall -q app.py historical_model.py season_data.py` and relevant tests.
5. Open a pull request with summary, evidence, screenshots if UI changes, limitations, and rollback notes.
6. Require a documented owner acceptance before merging. For owner-authored PRs with no available independent reviewer, the owner may explicitly authorize merge in the PR conversation after inspecting the diff, reviewing risks and confirming successful required CI checks. This is an owner sign-off, NOT an independent GitHub approval. If branch protection requires an independent approval, do not bypass it; obtain an eligible reviewer. Never self-approve or fabricate a review. Stop for explicit approval before changing external service credentials, buying APIs, or enabling live betting functionality.
7. After documented owner acceptance and merge, verify GitHub Actions and Render LIVE before marking the ROADMAP item done.

## Technical constraints
- Python 3.11, Streamlit, pandas, numpy, requests; Render free service.
- ESPN public endpoints are best effort and may be incomplete. Display source and timestamp.
- Caliente lines are NOT connected; never label imported/manual odds as live.
- Experimental model outputs are NOT calibrated. Avoid claims of profitability.
- Avoid look-ahead bias, evaluate by chronological splits and report uncertainty.
- Optimize for Android mobile, accessibility and resilient fallbacks.
- Never expose tokens or personal data in commits, logs, PRs, or the UI.
- Do not modify deployment settings, paid services, or secrets without explicit approval.

## Acceptance
A task is complete only after passing checks, documented owner acceptance (and any GitHub-required independent review), deployment verification, and ROADMAP update.
