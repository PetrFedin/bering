# Bering Corridor · V22 — controlled import of source originals

**Date:** 2026-10-30. **Branch:** audit/v22-originals-importer-20261030.  
**Status:** IMPORTER_LOCAL_TESTS_PASS / GITHUB_SOURCE_IMPORT_BLOCKED / GITHUB_RUNNER_NOT_CERTIFIED / INVESTMENT_HOLD.

This stage continues V21 and does **not** replace its 42-file Git-blob audit, 493-formula fingerprint, 223-output independent tie-out or commercial pilot admission.

## Exact current boundary

- The V20 originals import ZIP (Bering_V20_GitHub_Originals_Import_Pack_2026-10-27.zip) has SHA-256:
  284f14b29b3849c03450ae0d5b77eba5632696fc066750e4ed5f8792543a7f98.
- Its internal manifest (provenance/V20_IMPORT_SHA256.json) has SHA-256:
  cc97918f23c8590189e078f9e09a54682404943bfc675a4b47e1c334702b945a.
- The committed provenance/V20_IMPORT_SHA256SUMS.txt lists 42 expected source hashes.
- **The ZIP's 42 source files are not yet committed to GitHub.** The ZIP is unavailable to the current import session. No reconstructed text can replace the original byte-identical XLSX/DOCX sources.
- GitHub Actions minimal runner probe failed before its first step (runner_id=0, steps=[]); cause unknown: [run 40539570411](https://github.com/PetrFedin/bering/actions/runs/40539570411).

## New import control

The read-only preflight in scripts/audits/import_originals_v22.py:

1. Requires an existing Git checkout and validates the entire ZIP byte digest against the pinned V20 package.
2. Rejects ZIP path traversal, symlinks/special entries, duplicate archive members, individual members over 30 MiB or a total declared uncompressed size over 160 MiB.
3. Validates the exact internal 42-row JSON manifest, its SHA-256, all 42 committed SHA256SUMS ledger paths and per-file byte digest and size.
4. Refuses a changed existing destination file, unsafe parent symlinks and overwrites. Additional unlisted ZIP members are reported but never copied.
5. Requires explicit --apply, a named topic branch other than main/master and written reviewer attestation outside Git for redistribution rights and personal-data screening.
6. Uses staging, exclusive-create and post-write verification; on handled errors removes newly written files.
7. Does not stage, commit, push, merge or verify a remote GitHub tree. It cannot authenticate contracts, prove legal rights or recalculate Excel.

## Test receipt

**21 of 21 local synthetic fixture tests PASSED** on 2026-10-30. Synthetic fixtures are not Bering source files. Coverage: dry run, authorized local import, idempotence, changed package, changed manifest, altered original, missing ZIP file, harmless unlisted file, path traversal, duplicate member, ZIP symlink, unsafe manifest, ledger mismatch, overwritten original prevention, destination symlink, no approval, approval within repo, false approval, wrong attested ZIP, main-branch rejection, nested ZIP prefix and invalid hash.

Reproduce on an authorized checkout:

~~~bash
python -m unittest discover -s tests -p 'test_import_originals_v22.py' -v
python scripts/audits/import_originals_v22.py \
  --repo . --zip /outside/repo/Bering_V20_GitHub_Originals_Import_Pack_2026-10-27.zip \
  --report /outside/repo/bering-v22-preflight.json
~~~

If the ZIP wraps its members in one top-level directory, supply --prefix foldername/ after examining the actual contents. Do not change SHA pins to make a different archive pass.

A reviewer must personally approve the source rights and privacy review, evidenced by a JSON file *outside the Git checkout*. Example schema with deliberately unapproved values:

~~~json
{
  "approved": false,
  "redistribution_rights_reviewed": false,
  "personal_data_screened": false,
  "zip_sha256": "284f14b29b3849c03450ae0d5b77eba5632696fc066750e4ed5f8792543a7f98",
  "reviewer": ""
}
~~~

Only after truthful external verification and authorization:

~~~bash
python scripts/audits/import_originals_v22.py --repo . \
  --zip /outside/repo/Bering_V20_GitHub_Originals_Import_Pack_2026-10-27.zip \
  --approval-json /outside/repo/bering-v22-rights-review.json --apply
~~~

## Mandatory post-import stages

1. Inspect git status, scan the materials for non-public/sensitive information, and commit explicitly authorized originals to a separate PR. Do not change historical originals.
2. Fetch the pushed GitHub SHA in an independent checkout. Verify all 42 actual committed Git blobs via scripts/audits/verify_git_origins.py and run scripts/audits/release_admission_v21.py on the same SHA.
3. Repair hosted GitHub Actions and obtain GREEN logs and independent review on that exact SHA before touching main.
4. Separately collect contracts, dated quotes, invoices, waybills and 24-month OD data for P1/P2/P3; prove genuinely **incremental group contribution margin** before considering commercial PASS.

## Residual risks

- Byte identity is not documentary authenticity, redistribution permission, numerical accuracy or contractual evidence.
- Abrupt power failure during --apply may leave some correctly hashed new files; a repeated preflight detects unexpected modifications.
- Archive size limits are conservative; exceeding them requires an explicit tested code change, not a bypass.
- Malicious macros or confidential content inside the original documents require independent screening prior to upload.
- The actual V20 ZIP, remote Actions result, complete Excel recalculation, external financial audit and all three pilot documents **remain unverified**.

**Release decision:** HOLD. V22 is an importer engineering PR only.


## 2026-10-30 GitHub runner recheck — confirmed FAIL before steps

The newly created synthetic-only V22 workflow **ran as a GitHub event but failed before any step executed**:

- [V22 run 40977769784](https://github.com/PetrFedin/bering/actions/runs/40977769784)
- Exact SHA: 15675e2d669a0c4b7cfe4e421aa7150407c929c0
- Job: test-importer-only; conclusion=failure, runner_id=0, steps=[].
- Fetching the job log returned 404 BlobNotFound; there are no Python, checkout, or dependency execution logs.
- This matches the previous pre-step [runner probe 40539570411](https://github.com/PetrFedin/bering/actions/runs/40539570411), but **does not establish the underlying reason**. Possible Actions account/repository policy and billing/usage conditions must be checked in authorized GitHub settings, not guessed.
- **Do not mark GitHub CI GREEN or call the V22 importer remotely tested.** The 21 passing tests are local synthetic tests only.
