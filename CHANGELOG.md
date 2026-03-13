# Changelog

## v0.4.1

- Date: 2026-03-13
- Version: 0.4.1

### Summary

This release includes updates across Note Watcher behavior and documentation.

### Release notes (raw)

```json
{
  "Additional Changes": [
    "This release updates the package version to 0.4.1 to include the Arcade auth detection, error-marker behavior, and the new pre-flight check command. The distribution metadata and versioning were updated to `0.4.1` to reflect these changes."
  ],
  "New Features": [
    "You can now detect Arcade authentication URLs and clearly mark authentication failures so they are easier to spot during runs. The watcher/dispatcher now records auth failures as `@error` (not `@done`), and a new `check-arcade` CLI command was added to perform pre-flight token validation before execution."
  ]
}

```