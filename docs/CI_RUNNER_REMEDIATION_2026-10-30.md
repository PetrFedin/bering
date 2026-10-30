# P0 · GitHub Actions runner — diagnostic and recovery record

**Date:** 2026-10-30. **Repository:** PetrFedin/bering (private).  
**Status:** BLOCKED_BEFORE_FIRST_STEP / ROOT_CAUSE_UNKNOWN / NO_GREEN_CI.

## Facts verified via GitHub API

| Run | Event / workflow | Head SHA | Job result |
| --- | --- | --- | --- |
| [40539570411](https://github.com/PetrFedin/bering/actions/runs/40539570411) | Minimal echo/Python runner probe, no checkout | 11704d07cbe534bb650209c9e34e0ffc36720798 | failure, runner_id=0, steps=[] |
| [40977769784](https://github.com/PetrFedin/bering/actions/runs/40977769784) | V22 importer synthetic unit tests | 15675e2d669a0c4b7cfe4e421aa7150407c929c0 | failure, runner_id=0, steps=[] |

A fresh attempt to download V22 job log ID 123809939329 returned 404 BlobNotFound. These are **pre-execution failures**: none of our Python, checkout, ZIP scanning or unit-test steps ran. Do not change business logic or dependencies as a guess.

The V22 SHA check-run result reported **one annotation** for test-importer-only and two for research-qa; the available connector could not read the annotation contents. Those annotations must be inspected in the authenticated GitHub web UI; do not infer their message.

## Ordered no-cost diagnostic procedure

1. Open [V22 failed run](https://github.com/PetrFedin/bering/actions/runs/40977769784) in an authorized GitHub browser. Inspect the job page, check annotations and any pre-start failure banner; save the exact message (redact private information) in issue #7.
2. Open [repository Actions settings](https://github.com/PetrFedin/bering/settings/actions). Check whether Actions is enabled; inspect allowed GitHub-authored actions and any full-SHA pinning policy. Leave the workflow GITHUB_TOKEN scoped to **contents: read**; write permission is not needed for testing.
3. As the repository owner, inspect account [Billing & licensing](https://github.com/settings/billing) or the current billing pages for the private repo's **free Actions minutes, budgets/spending stops and verification notices**. Record observed values before changing anything; GitHub documentation confirms private repositories have account-level entitlements, but the quota **has NOT been verified as the cause for this repository**.
4. If settings and included usage are healthy, check current [GitHub Actions service status](https://www.githubstatus.com/) and ask GitHub Support to inspect runner-dispatch telemetry. Include both run IDs, head SHAs, job ID, conclusion, runner_id=0, steps=[], and missing logs.
5. After the root problem has actually been resolved, run ONE minimal hosted-runner probe to obtain real steps, visible logs and a successful conclusion.
6. Only then rerun the V22 unit-test workflow and the full source/financial admission workflow on a pinned SHA with *authorized* originals imported. Preserve the successful run URLs and review notes in the repository.
7. **Do not merge** the chain of draft PRs into main or mark the investment pilot PASS because a simple runner probe turns green. Each gate has independent conditions.

## Authoritative GitHub documentation

- [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- [GitHub Actions billing: private minutes and usage](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

## Responsibility and evidence limits

The available GitHub connector can inspect workflows, jobs and status, but cannot access the account's billing or repository Actions-policy settings nor the check-run annotation endpoint. Therefore **root cause remains unknown**. No payment method, paid runner, repo visibility change or security-sensitive setting was modified.

**Current decision:** CI HOLD, originals import HOLD, all P1/P2/P3 investment gates HOLD.
