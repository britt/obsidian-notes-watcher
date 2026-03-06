#!/bin/sh
# uninstall.sh - Uninstall Note Watcher LaunchAgent
#
# Stops the daemon, removes the plist, and optionally cleans up logs.
#
# Usage: ./uninstall.sh [--clean]
#
# Options:
#   --clean    Also remove the log directory
#
# Safe to run even if the agent is not installed.

set -e

LABEL="com.notewatcher.daemon"
PLIST_NAME="${LABEL}.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="${LAUNCH_AGENTS_DIR}/${PLIST_NAME}"
LOG_DIR="$HOME/Library/Logs/note-watcher"

CLEAN_LOGS=0

# Print message to stderr and exit
die() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

# Print informational message
info() {
    printf '==> %s\n' "$1"
}

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --clean)
            CLEAN_LOGS=1
            ;;
        --help|-h)
            printf 'Usage: %s [--clean]\n' "$0"
            printf '\nOptions:\n'
            printf '  --clean    Also remove the log directory (%s)\n' "$LOG_DIR"
            exit 0
            ;;
        *)
            die "Unknown option: ${arg}. Use --help for usage."
            ;;
    esac
done

# --- Main ---

info "Uninstalling Note Watcher LaunchAgent..."

# Unload the agent if it's currently loaded
if launchctl list "$LABEL" >/dev/null 2>&1; then
    info "Stopping daemon..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    info "Daemon stopped."
else
    info "Daemon is not currently running."
fi

# Remove the plist file
if [ -f "$PLIST_DEST" ]; then
    info "Removing plist: ${PLIST_DEST}"
    rm -f "$PLIST_DEST"
    info "Plist removed."
else
    info "Plist not found (already removed)."
fi

# Optionally remove log directory
if [ "$CLEAN_LOGS" -eq 1 ]; then
    if [ -d "$LOG_DIR" ]; then
        info "Removing log directory: ${LOG_DIR}"
        rm -rf "$LOG_DIR"
        info "Logs removed."
    else
        info "Log directory not found (already removed)."
    fi
else
    info "Log directory preserved: ${LOG_DIR}"
    info "  (Use --clean to remove logs)"
fi

info "Note Watcher LaunchAgent uninstalled."
