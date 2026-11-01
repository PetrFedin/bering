# Bering V26 | GitHub runner recovery: evidence and no-cost path

**2026-10-31** | **Status: not restored** | Current main protected=false

## Verified evidence

- Repo: `PetrFedin/bering` (private). Main at commit
  `e6dcc74cee46b327c399a1a0a5d4f8f282831d0f`, API `protected=false`.
- Last V25 head before V26 branch: commit
  `e5220086a5999d17c7ec7dcc6b6aa170773f4924`.
- GitHub Actions V25 job `v25-source-and-settlement-qa` at
  https://github.com/PetrFedin/bering/actions/runs/41198358944 :
  `conclusion=failure`, `runner_id=0`, `steps=[]` (failed **before** Python, Git
  checkout, build or workflow actions could execute).
- Another V25 run
  https://github.com/PetrFedin/bering/actions/runs/41198362423 returned
  `failure`, with API job reported completed and no actual executable steps.
- Attempt to fetch V25 job logs returned `404 BlobNotFound`. Missing logs and
  missing runner do **not** establish a Python defect, a subscription problem
  or a unique infrastructure cause.
- GitHub Status officially records a separate Actions/Pages/Webhooks incident
  on **2026-10-30 17:50-19:23 UTC**:
  https://www.githubstatus.com/history . The checked V25 failures were on
  2026-10-31; a prior-day incident is **not proof** that it caused those runs.
- The available GitHub connector cannot access Actions settings, hosted-runner
  administration or account billing endpoints (requests rejected as unsupported
  endpoint). As a result those settings have not been inspected or altered.

## Human-admin diagnostic checklist (no paid services required)

1. Open the failing run URL while logged into the repository owner account.
   Inspect the job's top-level failure banner and Checks annotations, copying
   exact redacted text into issue #7. Examine whether the job was rejected by
   a rule, spending limit, repository setting or temporary service failure.
2. Check repository Settings > Actions > General. Record whether workflows are
   enabled and whether checkout/setup-python actions are permitted. Do not
   relax the token's permission scope to fix an unproven infrastructure issue.
3. Check account Settings > Billing and licensing for Actions included usage,
   any spend-stop/budget/verification warning and account restrictions. Do
   **not** activate a pay-as-you-go budget just to run the test suite; use the
   free included availability where permitted.
4. If there is no explanatory banner and settings are healthy, open GitHub
   Support with the **two exact V25 run IDs**, timestamps, job IDs, `runner_id=0`,
   empty steps and 404 logs. Include the GitHub Status date distinction.
5. Once the diagnosed issue is fixed, run one **minimal** manual probe from an
   authorized account. Verify `Set up job`, runner image and a visible success.
   Do not rerun every workflow repeatedly until the minimal probe works.
6. Use `workflow_dispatch` for V26 test workflow (not every push), and only
   then run V26 and the full V16→V25 quality chain on the same pinned commit.
7. Set enforceable main protection, mandatory PR and independent review.
   Add required Actions checks only when they reliably start and report GREEN;
   do not permanently block main with checks that cannot execute.

## Free offline development path, not a replacement for hosted CI

In an authorized local checkout of the V26 topic branch with Python 3.11+:

```
python scripts/offline_qa_v26.py --repo . --receipt /tmp/bering-v26-local-receipt.json
python quality/fuzz_v26.py
```

This runs 200 local unit cases spanning V24, V25 and V26; verifies the
unverified financial and document baselines stay HOLD; and reports local
sha256 hashes. If a full Git checkout exists, its actual HEAD and clean-state
are reported. In a **partial** local source snapshot, the full integrated
commercial gate is reported as NOT_RUN, not silently claimed PASS.

**Never use local PASS, a public port forecast, or a syntactic file hash as a
substitute for GitHub CI GREEN or independent commercial evidence.**

GitHub documentation:
- https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs

Open blockers: #7 hosted runner, #18 protection, #1 historical originals,
#4 pilot additionality. No branch merged and no billable resources authorized.
