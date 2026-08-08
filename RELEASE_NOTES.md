# v0.4.4

Date: 2026-08-08
Version: 0.4.4

This release strengthens timeout handling in note processing and keeps the default action and package version aligned with the published release.

## Bug Fixes

* Fixed note processing so a timed out command agent marks the instruction with `@error`, continues with later instructions in the same file, and makes `process --all` exit with a failure status when any file times out. Daemon mode now logs the timeout and keeps watching, while the note retains the `@error` marker.

## Additional Changes

* Updated the action and package default version to `0.4.4`, so the default install matches this release.