#!/usr/bin/env bash
# Install the workflow platform on this computer, wherever it was cloned:
#   bash tools/install.sh            link ~/.local/bin/wf and the skill run-workflow into each agent
#   bash tools/install.sh --remove   remove the links this script made
# Claude Code reads ~/.claude/skills, Codex ${CODEX_HOME:-~/.codex}/skills, Antigravity
# ~/.gemini/config/skills. Links, not copies: `git pull` here updates every agent.
set -euo pipefail
WP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
remove=''
[ "${1:-}" = "--remove" ] && remove=1
[ -z "${1:-}" ] || [ -n "$remove" ] || { echo "usage: bash tools/install.sh [--remove]"; exit 2; }

link() {   # link <target> <link path>
    local src="$1" dst="$2"
    if [ -n "$remove" ]; then
        if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then rm "$dst"; echo "[OK] removed $dst"; fi
        return 0
    fi
    mkdir -p "$(dirname "$dst")"
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then echo "[OK] $dst (already linked)"
    elif [ -L "$dst" ] || [ -e "$dst" ]; then echo "[!]  $dst exists and is not our link; left unchanged"
    else ln -s "$src" "$dst"; echo "[OK] $dst -> $src"; fi
}

link "$WP/bin/wf" "$HOME/.local/bin/wf"
for dir in "$HOME/.claude/skills" "${CODEX_HOME:-$HOME/.codex}/skills" "$HOME/.gemini/config/skills"; do
    [ -d "$(dirname "$dir")" ] || continue          # that agent is not installed
    link "$WP/skills/run-workflow" "$dir/run-workflow"
done
[ -n "$remove" ] || case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "[!]  add ~/.local/bin to PATH";; esac
