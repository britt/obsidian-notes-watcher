# Changelog

## v0.4.1 - Arcade authentication handling

- Date: 2026-03-13
- Version: 0.4.1

### Summary

This release includes updated Arcade authentication handling and a pre-flight validation command.

### New Features

- Added Arcade authentication URL detection, recorded authentication failures with `@error` instead of `@done`, and introduced the `note-watcher check-arcade` command for pre-flight token validation.

### Additional Changes

- Updated distribution metadata and versioning to `0.4.1` to ship Arcade auth detection, `@error` markers, and the `check-arcade` pre-flight command.