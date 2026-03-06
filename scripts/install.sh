#!/bin/sh
# install.sh - Install Note Watcher as a macOS LaunchAgent
#
# Detects the note-watcher executable, generates the LaunchAgent plist,
# installs it, and starts the daemon with crash recovery enabled.
#
# Usage: ./install.sh
#
# Safe to run multiple times (idempotent).

set -e

LABEL="com.notewatcher.daemon"
PLIST_NAME="${LABEL}.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="${LAUNCH_AGENTS_DIR}/${PLIST_NAME}"
LOG_DIR="$HOME/Library/Logs/note-watcher"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_TEMPLATE="${SCRIPT_DIR}/${PLIST_NAME}"

# Print message to stderr and exit
die() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

# Print informational message
info() {
    printf '==> %s\n' "$1"
}

# Detect the note-watcher executable path
detect_executable() {
    # 1. Check if note-watcher is on PATH
    if command -v note-watcher >/dev/null 2>&1; then
        command -v note-watcher
        return 0
    fi

    # 2. Check common pip install locations
    for candidate in \
        "$HOME/.local/bin/note-watcher" \
        "/usr/local/bin/note-watcher" \
        "$HOME/Library/Python/3.*/bin/note-watcher"; do
        # shellcheck disable=SC2086
        for path in $candidate; do
            if [ -x "$path" ]; then
                printf '%s' "$path"
                return 0
            fi
        done
    done

    # 3. Try to find via pip show
    pip_cmd=""
    if command -v pip3 >/dev/null 2>&1; then
        pip_cmd="pip3"
    elif command -v pip >/dev/null 2>&1; then
        pip_cmd="pip"
    fi

    if [ -n "$pip_cmd" ]; then
        pip_location="$($pip_cmd show note-watcher 2>/dev/null | sed -n 's/^Location: //p')"
        if [ -n "$pip_location" ]; then
            pip_bin="$(dirname "$pip_location")/bin/note-watcher"
            if [ -x "$pip_bin" ]; then
                printf '%s' "$pip_bin"
                return 0
            fi
        fi
    fi

    return 1
}

# --- Main ---

info "Installing Note Watcher LaunchAgent..."

# Check we're on macOS
if [ "$(uname -s)" != "Darwin" ]; then
    die "This script only works on macOS."
fi

# Check template exists
if [ ! -f "$PLIST_TEMPLATE" ]; then
    die "Plist template not found: ${PLIST_TEMPLATE}"
fi

# Detect note-watcher executable
info "Detecting note-watcher executable..."
NOTE_WATCHER_PATH="$(detect_executable)" || die \
    "Could not find note-watcher executable. Please install it first:
    pip install note-watcher
  or:
    pip install -e ."

info "Found note-watcher at: ${NOTE_WATCHER_PATH}"

# Create log directory
info "Creating log directory: ${LOG_DIR}"
mkdir -p "$LOG_DIR"

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS_DIR"

# If agent is already loaded, unload it first (idempotent)
if launchctl list "$LABEL" >/dev/null 2>&1; then
    info "Unloading existing agent..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Generate plist from template with correct paths
info "Generating plist with executable path..."
sed \
    -e "s|__NOTE_WATCHER_PATH__|${NOTE_WATCHER_PATH}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

# Load the agent
info "Loading LaunchAgent..."
launchctl load "$PLIST_DEST"

# Verify the agent started
sleep 1
if launchctl list "$LABEL" >/dev/null 2>&1; then
    info "Note Watcher LaunchAgent installed and running."
    info "  Label:  ${LABEL}"
    info "  Plist:  ${PLIST_DEST}"
    info "  Logs:   ${LOG_DIR}/"
    info "  Exec:   ${NOTE_WATCHER_PATH}"
    info ""
    info "The daemon will restart automatically on crash (KeepAlive)."
    info "To uninstall, run: ${SCRIPT_DIR}/uninstall.sh"
else
    printf 'Warning: Agent loaded but may not be running yet.\n' >&2
    printf 'Check logs at: %s\n' "$LOG_DIR" >&2
    exit 1
fi
