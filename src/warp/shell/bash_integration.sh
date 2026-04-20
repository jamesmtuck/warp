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

# History-navigation offset for the arrow-key prediction widgets.
# 0 = at the live (empty) prompt; N = N steps back in history.
_WARP_HIST_OFFSET=0

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

    # Reset history offset so down-arrow is ready to predict at the new prompt
    _WARP_HIST_OFFSET=0

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
# Helper: extract the command text from a `history` output line.
# Input format: "   NNN  command text"
# ---------------------------------------------------------------------------
_warp_hist_line_text() {
    sed 's/^ *[0-9][0-9]* *//' <<< "$1"
}

# ---------------------------------------------------------------------------
# Up-arrow widget: navigate backwards in history (replaces readline default).
# We track position in _WARP_HIST_OFFSET so the down-arrow widget knows
# whether we are mid-navigation or at the live prompt.
# ---------------------------------------------------------------------------
_warp_up_widget() {
    local -a all_hist
    mapfile -t all_hist < <(HISTTIMEFORMAT= history 2>/dev/null)
    local hist_count=${#all_hist[@]}
    [[ "${hist_count}" -eq 0 ]] && return

    if [[ "${_WARP_HIST_OFFSET}" -lt "${hist_count}" ]]; then
        (( _WARP_HIST_OFFSET++ ))
        local idx=$(( hist_count - _WARP_HIST_OFFSET ))
        READLINE_LINE=$(_warp_hist_line_text "${all_hist[$idx]}")
        READLINE_POINT=${#READLINE_LINE}
    fi
}

# ---------------------------------------------------------------------------
# Down-arrow widget: navigate forward in history, or insert top prediction.
#
# Behaviour:
#   _WARP_HIST_OFFSET > 1  →  move forward one step (show next history entry)
#   _WARP_HIST_OFFSET = 1  →  return to live (empty) prompt
#   _WARP_HIST_OFFSET = 0  →  already at live prompt: insert top prediction
# ---------------------------------------------------------------------------
_warp_down_widget() {
    if [[ "${_WARP_HIST_OFFSET}" -gt 1 ]]; then
        # Navigate forward through history
        (( _WARP_HIST_OFFSET-- ))
        local -a all_hist
        mapfile -t all_hist < <(HISTTIMEFORMAT= history 2>/dev/null)
        local hist_count=${#all_hist[@]}
        local idx=$(( hist_count - _WARP_HIST_OFFSET ))
        READLINE_LINE=$(_warp_hist_line_text "${all_hist[$idx]}")
        READLINE_POINT=${#READLINE_LINE}
    elif [[ "${_WARP_HIST_OFFSET}" -eq 1 ]]; then
        # One more step forward returns to the live (empty) prompt
        _WARP_HIST_OFFSET=0
        READLINE_LINE=""
        READLINE_POINT=0
    else
        # Already at the live prompt: insert the top predicted command
        if [[ -z "${READLINE_LINE}" ]]; then
            local predicted
            predicted=$("${WARP_BIN}" next --top 2>/dev/null)
            if [[ -n "${predicted}" ]]; then
                READLINE_LINE="${predicted}"
                READLINE_POINT=${#READLINE_LINE}
            fi
        fi
    fi
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

    # Bind ↑/↓ arrows for history navigation + prediction at the live prompt
    bind -x '"\e[A": _warp_up_widget'   2>/dev/null || true  # Up arrow
    bind -x '"\e[B": _warp_down_widget' 2>/dev/null || true  # Down arrow

    # Bind Ctrl-F to warp interactive search (doesn't shadow Ctrl-R)
    bind -x '"\C-f": _warp_search_widget' 2>/dev/null || true
    # Bind Alt-A to warp AI ask
    bind -x '"\ea": _warp_ask_widget' 2>/dev/null || true
}

# Auto-enable
warp_enable_bash
