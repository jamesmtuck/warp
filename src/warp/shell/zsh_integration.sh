#!/usr/bin/env zsh
# Warp zsh integration
# Source this file from ~/.zshrc to enable Warp hooks.
# Example: source "$(warp --shell-path)/zsh_integration.sh"
#
# Safety: all warp calls are wrapped in error-tolerant subshells.
# A failure in any warp function will NOT affect your shell session.

# Guard against double-loading
[[ -n "${WARP_ZSH_LOADED:-}" ]] && return 0
WARP_ZSH_LOADED=1

# Resolve warp executable
WARP_BIN="${WARP_BIN:-warp}"

# Generate a stable session ID for this shell session
WARP_SESSION_ID="${WARP_SESSION_ID:-$(date +%s)-$$}"
export WARP_SESSION_ID

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_WARP_CMD_START=0
_WARP_LAST_CMD=""

# ---------------------------------------------------------------------------
# Helper: millisecond timestamp, safe on macOS and Linux
# On macOS, date +%s%3N outputs "<seconds>N" (%%N is unsupported), so we
# strip any non-numeric characters from the output.
# ---------------------------------------------------------------------------
_warp_ms_timestamp() {
    local ts
    ts=$(date +%s%3N 2>/dev/null || echo 0)
    ts="${ts//[^0-9]/}"
    echo "${ts:-0}"
}

# ---------------------------------------------------------------------------
# preexec: called by zsh before each command executes
# ---------------------------------------------------------------------------
_warp_preexec() {
    _WARP_LAST_CMD="$1"
    _WARP_CMD_START=$(_warp_ms_timestamp)
}

# ---------------------------------------------------------------------------
# precmd: called by zsh before each prompt
# ---------------------------------------------------------------------------
_warp_precmd() {
    local exit_code=$?

    # Skip if no command was captured
    [[ -z "${_WARP_LAST_CMD}" ]] && return 0

    local duration_ms=0
    if [[ "${_WARP_CMD_START}" -gt 0 ]]; then
        local now
        now=$(_warp_ms_timestamp)
        duration_ms=$(( now - _WARP_CMD_START ))
    fi

    # Capture in background — never block or crash the shell
    (
        "${WARP_BIN}" capture \
            --exit-code "${exit_code}" \
            --shell "zsh" \
            --cwd "${PWD}" \
            --session-id "${WARP_SESSION_ID}" \
            --duration-ms "${duration_ms}" \
            "${_WARP_LAST_CMD}" \
            2>/dev/null
    ) &!

    _WARP_LAST_CMD=""
}

# ---------------------------------------------------------------------------
# ZLE widget: interactive history search
# ---------------------------------------------------------------------------
_warp_search_widget() {
    local selected
    selected=$("${WARP_BIN}" interactive-search --print-only 2>/dev/null)
    if [[ -n "${selected}" ]]; then
        BUFFER="${selected}"
        CURSOR=${#BUFFER}
    fi
    zle reset-prompt
}

# ---------------------------------------------------------------------------
# ZLE widget: AI ask
# ---------------------------------------------------------------------------
_warp_ask_widget() {
    local request selected
    # Read from user without disturbing line editor
    zle -I
    printf "\nWarp ask: " >&2
    read -r request
    if [[ -n "${request}" ]]; then
        selected=$("${WARP_BIN}" interactive-ask "${request}" --print-only 2>/dev/null)
        if [[ -n "${selected}" ]]; then
            BUFFER="${selected}"
            CURSOR=${#BUFFER}
        fi
    fi
    zle reset-prompt
}

# ---------------------------------------------------------------------------
# Enable warp for zsh
# ---------------------------------------------------------------------------
warp_enable_zsh() {
    # Register hook functions with zsh's hook arrays
    autoload -Uz add-zsh-hook 2>/dev/null || true
    add-zsh-hook preexec _warp_preexec 2>/dev/null || true
    add-zsh-hook precmd  _warp_precmd  2>/dev/null || true

    # Register ZLE widgets
    zle -N _warp_search_widget 2>/dev/null || true
    zle -N _warp_ask_widget    2>/dev/null || true

    # Bind Ctrl-F to history search, Alt-A to AI ask
    bindkey '^F' _warp_search_widget 2>/dev/null || true
    bindkey '^[a' _warp_ask_widget   2>/dev/null || true
}

# Auto-enable
warp_enable_zsh
