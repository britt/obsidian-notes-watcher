# Issue #28: GitHub Action fails on overlapping pushes with @mentions

## Acceptance criteria (restated from the issue)

1. Pushing an `@mention` while an action run from a *prior* `@mention` push is
   still in progress must not cause the later run to fail.
2. Both instructions must end up processed and committed — no instruction is
   silently lost or double-processed in a way that corrupts the note.
3. The fix must not abandon or cancel an in-progress agent run (losing partial
   work) to achieve (1).

## Root cause

`action.yml`'s "Commit results" step already rebases before pushing
(#15), but that only fixes *unrelated* commits landing on `main` mid-run.
Issue #28 is two runs of the *same* workflow racing:

- `actions/checkout` pins each run to the exact SHA that triggered it
  (`github.sha`), not the branch tip. So when push B fires while push A's
  run is still going, run B's checkout still shows mention 1 as raw/unprocessed
  (run A hasn't committed its result yet).
- Without a `concurrency` group, runs A and B execute their "Process notes"
  step in parallel. Both see mention 1 as unprocessed and both dispatch an
  agent for it, in addition to run B dispatching for mention 2.
- When both try to commit, run A pushes first. Run B's `git pull --rebase`
  then has to replay run B's local commit (which independently reprocessed
  mention 1) on top of run A's already-pushed commit (which also processed
  mention 1). Both edited the same lines of the note differently, so the
  rebase hits a real content conflict and fails — which fails the job.

Two independent gaps, both required to close the race:

- **No concurrency control**: overlapping workflow runs are allowed to
  execute (and race to push) at the same time.
- **Stale processing input**: even a run that starts later doesn't re-sync
  to the branch tip before processing, so it can't see that another run
  already finished mention 1.

## Fix

1. `examples/github-action/.github/workflows/note-watcher.yml`: add a
   `concurrency` group keyed on the ref with `cancel-in-progress: false`, so
   overlapping runs on the same branch queue instead of racing. `false` is
   required — cancelling an in-progress run would abandon an agent mid-edit
   (violates acceptance criterion 3).
2. `action.yml`: in the "Process notes" step, `git pull --ff-only` before
   running `note-watcher process --all`. Combined with (1), a queued run now
   starts only after the prior run's commit has landed, and this pull syncs
   the checkout to see it — so it only dispatches for the mention(s) that are
   actually still unprocessed. Processing is already idempotent (verified by
   existing VERIFICATION_PLAN scenarios 5/6: a `@done`-marked instruction is
   skipped), so this is safe.
3. `README.md`: document the concurrency requirement in the "Setting up the
   GitHub Actions workflow" section, since anyone hand-writing their own
   workflow (not copying the example) needs to add it themselves — same
   treatment already given to the `permissions: contents: write` requirement.

## Files touched

- `examples/github-action/.github/workflows/note-watcher.yml`
- `action.yml`
- `README.md`
- `VERIFICATION_PLAN.md` (new scenario)

## Assumptions

- "the action fails" in the issue refers to the job exiting non-zero (visible
  as a red X), which the rebase-conflict path in the root cause above
  produces. No other failure mode was reported in the issue or comments.
- A per-ref concurrency group (`note-watcher-${{ github.ref }}`) is the
  correct granularity — different branches/vaults pushing concurrently are
  unrelated and shouldn't queue behind each other.
- Live verification against real GitHub Actions infrastructure (real
  secrets, real runners) is out of scope for this environment; verification
  instead uses a local git simulation of the race (real git, no mocks) plus
  a new manual VERIFICATION_PLAN scenario for a developer with a live test
  vault, consistent with how existing scenarios 3 and 6 already require
  manual execution.
