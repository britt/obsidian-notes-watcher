# v0.4.4

Date: 2026-08-08
Version: 0.4.4

## Summary

This release improves note processing for agent timeouts and keeps the default action and package version aligned with release 0.4.4.

## Bug Fixes

* Fixed note processing so a command agent timeout writes an `@error` marker, keeps later instructions in the same file running, and makes `process --all` exit with a failure status when any file times out. Daemon mode now logs the timeout, swallows the error, and keeps the watcher running.

## Additional Changes

* Updated the action and package default version to `0.4.4`, so default installs match the release version.