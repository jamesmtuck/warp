#!/usr/bin/env bash
# Warp bash integration
# Source this file from ~/.bashrc or ~/.bash_profile to enable Warp hooks.
# Example: source "$(warp --shell-path)/bash_integration.sh"
#
# Safety: all warp calls are wrapped in error-tolerant subshells.
# A failure in any warp function will NOT affect your shell session.

# Guard against double-loading
[[ -n "${WARP_BASH_LOADED:-}" ]] && return 0
WARP_BASH_LOADED=1

# Resolve warp executable
WARP_BIN="${WARP_BIN:-warp}"

# Generate a stable session ID for this shell session
WARP_SESSION_ID="${WARP_SESSION_ID:-$(date +%s)-$$}"
export WARP_SESSION_ID

# ---------------------------------------------------------------------------
# Internal state for timing and capture
# ---------------------------------------------------------------------------
_WARP_CMD_START=0
_WARP_LAST_CMD=""
_WARP_LAST_EXIT=0

# ---------------------------------------------------------------------------
# Capture hook: runs BEFORE each command (via DEBUG trap)
# ---------------------------------------------------------------------------
_warp_preexec() {
    # Record start time (seconds since epoch)
    _WARP_CMD_START=$(date +%s%3N 2>/dev/null || echo 0)
    # BASH_COMMAND contains the command about to run
    _WARP_LAST_CMD="${BASH_COMMAND}"
}

# ---------------------------------------------------------------------------
# Post-command hook: runs as part of PROMPT_COMMAND
# ---------------------------------------------------------------------------
_warp_precmd() {
    local exit_code=$?
    _WARP_LAST_EXIT="${exit_code}"

    # Skip if no command was run
    [[ -z "${_WARP_LAST_CMD}" ]] && return 0

    local duration_ms=0
    if [[ "${_WARP_CMD_START}" -gt 0 ]]; then
        local now
        now=$(date +%s%3N 2>/dev/null || echo 0)
        duration_ms=$(( now - _WARP_CMD_START ))
    fi

    # Capture the command in the background (failure-safe)
    (
        "${WARP_BIN}" capture \
            --exit-code "${_WARP_LAST_EXIT}" \
            --shell "bash" \
            --cwd "$(pwd)" \
            --session-id "${WARP_SESSION_ID}" \
            --duration-ms "${duration_ms}" \
            "${_WARP_LAST_CMD}" \
            2>/dev/null
    ) &
    disown 2>/dev/null

    _WARP_LAST_CMD=""
}

# ---------------------------------------------------------------------------
# Interactive history search: bound to Ctrl-R style key
# ---------------------------------------------------------------------------
_warp_search_widget() {
    local selected
    selected=$("${WARP_BIN}" interactive-search --print-only 2>/dev/null)
    if [[ -n "${selected}" ]]; then
        # Insert into readline buffer
        READLINE_LINE="${selected}"
        READLINE_POINT=${#READLINE_LINE}
    fi
}

# ---------------------------------------------------------------------------
# Interactive AI ask widget
# ---------------------------------------------------------------------------
_warp_ask_widget() {
    local request selected
    printf "\nWarp ask: " >&2
    read -r request
    if [[ -n "${request}" ]]; then
        selected=$("${WARP_BIN}" interactive-ask "${request}" --print-only 2>/dev/null)
        if [[ -n "${selected}" ]]; then
            READLINE_LINE="${selected}"
            READLINE_POINT=${#READLINE_LINE}
        fi
    fi
}

# ---------------------------------------------------------------------------
# Enable warp for bash
# ---------------------------------------------------------------------------
warp_enable_bash() {
    # Set up DEBUG trap for pre-exec timing (best-effort)
    trap '_warp_preexec' DEBUG 2>/dev/null || true

    # Prepend our post-command hook to PROMPT_COMMAND
    if [[ -z "${PROMPT_COMMAND}" ]]; then
        PROMPT_COMMAND="_warp_precmd"
    else
        PROMPT_COMMAND="_warp_precmd;${PROMPT_COMMAND}"
    fi

    # Bind Ctrl-F to warp interactive search (doesn't shadow Ctrl-R)
    bind -x '"\C-f": _warp_search_widget' 2>/dev/null || true
    # Bind Alt-A to warp AI ask
    bind -x '"\ea": _warp_ask_widget' 2>/dev/null || true
}

# Auto-enable
warp_enable_bash
