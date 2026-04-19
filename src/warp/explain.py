"""Rule-based command explanation for warp."""
from __future__ import annotations

import re
from typing import Optional

from warp.safety import analyze_command_risk


# Verb explanations
_VERB_DOCS: dict[str, str] = {
    "ls": "List directory contents.",
    "cd": "Change the current directory.",
    "pwd": "Print the current working directory.",
    "echo": "Print text to standard output.",
    "cat": "Concatenate and print file contents.",
    "grep": "Search for patterns in text.",
    "rg": "Ripgrep: fast recursive text search.",
    "find": "Search for files in a directory hierarchy.",
    "fd": "A faster, user-friendly alternative to find.",
    "rm": "Remove (delete) files or directories.",
    "cp": "Copy files or directories.",
    "mv": "Move or rename files.",
    "mkdir": "Create directories.",
    "touch": "Create empty files or update timestamps.",
    "chmod": "Change file permissions.",
    "chown": "Change file ownership.",
    "sudo": "Execute a command with elevated (root) privileges.",
    "git": "Distributed version control system.",
    "docker": "Manage Docker containers and images.",
    "kubectl": "Interact with a Kubernetes cluster.",
    "ssh": "Connect to a remote host via Secure Shell.",
    "scp": "Securely copy files over SSH.",
    "rsync": "Sync files locally or over SSH efficiently.",
    "tar": "Archive utility (create/extract .tar files).",
    "gzip": "Compress files using gzip.",
    "curl": "Transfer data from/to URLs.",
    "wget": "Non-interactive network downloader.",
    "ps": "Report a snapshot of current processes.",
    "top": "Display dynamic real-time process information.",
    "htop": "Interactive process viewer.",
    "kill": "Send a signal to a process.",
    "pkill": "Kill processes by name.",
    "df": "Report disk space usage.",
    "du": "Estimate file and directory disk usage.",
    "dd": "Convert and copy files at block level (disk-level).",
    "mkfs": "Build a Linux filesystem (format a device).",
    "mount": "Mount a filesystem.",
    "umount": "Unmount a filesystem.",
    "awk": "Pattern-scanning and text-processing language.",
    "sed": "Stream editor for filtering and transforming text.",
    "sort": "Sort lines of text.",
    "uniq": "Filter duplicate lines.",
    "wc": "Count words, lines, and characters.",
    "head": "Print the first lines of files.",
    "tail": "Print the last lines of files.",
    "less": "View file contents page by page.",
    "more": "View file contents page by page (basic).",
    "diff": "Compare files line by line.",
    "patch": "Apply a diff/patch file.",
    "make": "Build automation tool.",
    "python": "Run a Python script or interactive interpreter.",
    "python3": "Run a Python 3 script.",
    "pip": "Install Python packages.",
    "npm": "Node.js package manager.",
    "node": "Run a Node.js script.",
    "go": "Go toolchain (build, run, test).",
    "cargo": "Rust package manager and build tool.",
    "apt": "Debian/Ubuntu package manager.",
    "apt-get": "Debian/Ubuntu package manager (classic).",
    "yum": "RPM-based package manager.",
    "dnf": "Fedora/RHEL package manager.",
    "brew": "macOS/Linux package manager (Homebrew).",
    "systemctl": "Control systemd services.",
    "journalctl": "Query the systemd journal.",
    "cron": "Daemon to execute scheduled commands.",
    "crontab": "Manage scheduled cron jobs.",
    "env": "Set environment variables or print current environment.",
    "export": "Set and export environment variables.",
    "source": "Execute commands from a file in the current shell.",
    "alias": "Create command aliases.",
    "history": "Show shell command history.",
    "man": "Display the manual page for a command.",
    "which": "Locate a command in PATH.",
    "type": "Indicate how a command name is interpreted.",
    "xargs": "Build and execute command lines from standard input.",
    "tee": "Read stdin and write to stdout and files.",
    "printf": "Format and print data.",
    "read": "Read a line from stdin.",
    "test": "Evaluate conditional expressions.",
    "true": "Return a successful exit status.",
    "false": "Return a failing exit status.",
    "sleep": "Pause for a given duration.",
    "date": "Display or set the system date/time.",
    "basename": "Strip directory and suffix from filenames.",
    "dirname": "Strip the last component of a path.",
    "realpath": "Resolve symlinks and print the canonical path.",
    "ln": "Create hard or symbolic links.",
    "stat": "Display file or filesystem status.",
    "file": "Determine the type of a file.",
    "strings": "Print printable characters from binary files.",
    "xxd": "Make a hex dump or reverse it.",
    "od": "Dump files in octal and other formats.",
    "tr": "Translate or delete characters.",
    "cut": "Remove sections from each line.",
    "paste": "Merge lines of files.",
    "join": "Join lines of two files on a common field.",
    "column": "Columnate lists.",
    "jq": "Command-line JSON processor.",
    "yq": "Command-line YAML/JSON processor.",
    "nc": "Netcat: read/write network connections.",
    "netstat": "Print network connections, routing tables, interface statistics.",
    "ss": "Investigate sockets.",
    "ip": "Show/manipulate routing, devices, policy routing.",
    "ifconfig": "Configure or display network interfaces.",
    "ping": "Send ICMP ECHO_REQUEST to network hosts.",
    "traceroute": "Print the route packets take to a host.",
    "nmap": "Network exploration and security scanning.",
    "openssl": "OpenSSL command-line tool for TLS and cryptography.",
    "gpg": "GNU Privacy Guard for encryption/signing.",
    "base64": "Encode or decode base64 data.",
    "md5sum": "Compute and check MD5 checksums.",
    "sha256sum": "Compute and check SHA-256 checksums.",
    "zip": "Package and compress files.",
    "unzip": "Extract compressed files from ZIP archives.",
    "7z": "7-Zip archiver.",
    "ffmpeg": "Multimedia framework for converting and processing media.",
    "convert": "ImageMagick image conversion tool.",
    "strace": "Trace system calls and signals.",
    "ltrace": "Trace library calls.",
    "gdb": "GNU Debugger.",
    "valgrind": "Memory error detector and profiler.",
    "ldd": "Print shared library dependencies.",
    "nm": "List symbols from object files.",
    "objdump": "Display information from object files.",
    "readelf": "Display information about ELF files.",
    "watch": "Execute a program periodically, showing output fullscreen.",
    "time": "Measure program execution time.",
    "timeout": "Run a command with a time limit.",
    "nohup": "Run a command immune to hangups.",
    "nice": "Run a command with modified scheduling priority.",
    "ionice": "Set or get process I/O scheduling class and priority.",
    "screen": "Terminal multiplexer.",
    "tmux": "Terminal multiplexer (modern).",
    "vim": "Vi IMproved text editor.",
    "nano": "Simple terminal-based text editor.",
    "emacs": "Extensible text editor.",
    "bat": "Cat clone with syntax highlighting.",
    "exa": "Modern replacement for ls.",
    "lsd": "Next-gen ls command.",
    "zoxide": "Smarter cd command.",
    "fzf": "Command-line fuzzy finder.",
    "ripgrep": "Fast recursive grep.",
    "delta": "Syntax-highlighting pager for git and diff output.",
}

_FLAG_DOCS: dict[str, str] = {
    "-r": "recursive",
    "-R": "recursive",
    "-f": "force (no prompts)",
    "-v": "verbose",
    "-i": "interactive (prompt before overwrite) or case-insensitive search",
    "-n": "dry run or line number",
    "-l": "long format or list files only",
    "-a": "all files (including hidden) or append",
    "-h": "human-readable sizes",
    "-p": "preserve or parents",
    "-d": "directory",
    "-e": "expression or extended regex",
    "-q": "quiet",
    "-s": "silent or symbolic",
    "--dry-run": "simulate without making changes",
    "--force": "force the operation",
    "--all": "include all items",
    "--verbose": "show verbose output",
    "--recursive": "recurse into subdirectories",
    "--help": "display help information",
}


def _explain_flags(flags: list[str]) -> list[str]:
    """Return human-readable explanations for known flags."""
    explanations = []
    for flag in flags:
        if flag in _FLAG_DOCS:
            explanations.append(f"{flag}: {_FLAG_DOCS[flag]}")
    return explanations


def _extract_flags(command: str) -> list[str]:
    """Extract flag tokens from a command."""
    return re.findall(r"(?:^|\s)(--?[a-zA-Z][a-zA-Z0-9-]*)", command)


def explain_command(command: str) -> dict:
    """Explain a shell command in plain English.

    Returns a dict with keys: verb, explanation, flags, pipeline, warnings, risk_level, safer_preview.
    """
    cmd = command.strip()
    if not cmd:
        return {
            "verb": None,
            "explanation": "Empty command.",
            "flags": [],
            "flag_explanations": [],
            "has_pipeline": False,
            "has_redirect": False,
            "warnings": [],
            "risk_level": "low",
            "safer_preview": None,
        }

    from warp.normalize import extract_verb, normalize_command
    verb = extract_verb(cmd)
    flags = _extract_flags(cmd)
    flag_explanations = _explain_flags(flags)

    # Verb explanation
    verb_doc = _VERB_DOCS.get(verb or "", "") if verb else ""

    # Pipeline / redirect awareness
    has_pipeline = "|" in cmd
    has_redirect = bool(re.search(r"(?<![<>])>", cmd))

    # Compose explanation
    parts: list[str] = []
    if verb_doc:
        parts.append(verb_doc)
    else:
        parts.append(f"Runs the command `{verb}`." if verb else "Unknown command.")

    if flag_explanations:
        parts.append("Flags: " + "; ".join(flag_explanations) + ".")

    if has_pipeline:
        parts.append("Uses a pipeline to pass output between commands.")
    if has_redirect:
        parts.append("Uses shell redirection to write output to a file.")

    explanation = " ".join(parts)

    # Risk analysis
    risk_level, warnings, safer_preview = analyze_command_risk(cmd)

    return {
        "verb": verb,
        "explanation": explanation,
        "flags": flags,
        "flag_explanations": flag_explanations,
        "has_pipeline": has_pipeline,
        "has_redirect": has_redirect,
        "warnings": warnings,
        "risk_level": risk_level,
        "safer_preview": safer_preview,
    }
