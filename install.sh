#!/usr/bin/env bash
# Durweg bootstrap for a new Linux / WSL computer (apt). Run it after the three entry commands in
# README.md (install git and gh, log in to GitHub, clone this repository):
#   bash ~/durweg/install.sh
# It only does what has to happen before an agent can run the setup workflow:
#   1. checks GitHub access to both private repositories;  2. Python 3 and curl;
#   3. the setup workflow (musetee/aiagents at a fixed, reviewed commit) in ~/aiagents;
#   4. wf and its agent skill;  5. Claude Code;  6. tells you how to start the setup workflow.
# Safe to run again: what is there already is kept. Stops at the first problem and says what to do.
set -uo pipefail

AIAGENTS_REPO="${DURWEG_AIAGENTS_REPO:-musetee/aiagents}"
AIAGENTS_COMMIT="${DURWEG_AIAGENTS_COMMIT:-__SET_AT_RELEASE__}"   # reviewed commit of branch durweg-setup
DURWEG_REPO="${DURWEG_REPO:-musetee/durweg}"
AIAGENTS_DIR="${DURWEG_AIAGENTS_DIR:-$HOME/aiagents}"
RUNS="$HOME/durweg-runs"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say()  { printf '  %s\n' "$*"; }
ok()   { printf '  [OK] %s\n' "$*"; }
stop() { printf '  [X]  %s\n' "$1"; [ -n "${2:-}" ] && printf '       %s\n' "$2"; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }
AGAIN="Then run again: bash $HERE/install.sh"

echo; say "Durweg: set up the base for the setup workflow"; echo

# 1. GitHub access (both repositories are private)
case "$AIAGENTS_COMMIT" in
    *[!0-9a-f]*|'') stop "This install.sh is not a release (no fixed setup-workflow version)." \
                         "Get the released install.sh: git -C $HERE pull" ;;
esac
has gh || stop "gh (GitHub CLI) is missing." "Install it: sudo apt-get install -y gh. $AGAIN"
gh auth status >/dev/null 2>&1 || stop "You are not logged in to GitHub." \
    "Run: gh auth login --hostname github.com --git-protocol https --web && gh auth setup-git. $AGAIN"
gh repo view "$DURWEG_REPO" >/dev/null 2>&1 || stop "No access to $DURWEG_REPO." \
    "Ask its owner for access, or check the GitHub account you logged in with (gh auth status). $AGAIN"
gh api "repos/$AIAGENTS_REPO/commits/$AIAGENTS_COMMIT" >/dev/null 2>&1 || stop \
    "No access to $AIAGENTS_REPO at $AIAGENTS_COMMIT." \
    "Ask its owner for access, or check the network. $AGAIN"
ok "GitHub access to $DURWEG_REPO and $AIAGENTS_REPO"

# 2. Python 3 and curl
missing=''
python3 -c 'import sys' >/dev/null 2>&1 || missing="$missing python3"
has curl || missing="$missing curl"
if [ -n "$missing" ]; then
    has apt-get || stop "Missing:$missing, and apt-get is not available." "Install them, then: $AGAIN"
    say "Installing$missing (sudo asks for your password)..."
    sudo apt-get update -qq && sudo apt-get install -y$missing || stop "Installing$missing failed." "$AGAIN"
fi
ok "Python 3 and curl"

# 3. The setup workflow at the fixed commit
if [ -d "$AIAGENTS_DIR/.git" ]; then
    [ -z "$(git -C "$AIAGENTS_DIR" status --porcelain --untracked-files=all)" ] || stop \
        "$AIAGENTS_DIR has local changes; it is not touched." "Move it away or commit the changes. $AGAIN"
    git -C "$AIAGENTS_DIR" cat-file -e "$AIAGENTS_COMMIT^{commit}" 2>/dev/null || \
        git -C "$AIAGENTS_DIR" fetch -q origin || stop "Could not update $AIAGENTS_DIR." "$AGAIN"
elif [ -e "$AIAGENTS_DIR" ]; then
    stop "$AIAGENTS_DIR exists and is not a git clone; it is not touched." "Move it away. $AGAIN"
else
    gh repo clone "$AIAGENTS_REPO" "$AIAGENTS_DIR" -- -q || stop "Cloning $AIAGENTS_REPO failed." "$AGAIN"
fi
git -C "$AIAGENTS_DIR" checkout -q --detach "$AIAGENTS_COMMIT" 2>/dev/null || stop \
    "$AIAGENTS_DIR has no commit $AIAGENTS_COMMIT." "$AGAIN"
ok "Setup workflow: $AIAGENTS_DIR at ${AIAGENTS_COMMIT:0:10}"

# 4. wf and the skill run-workflow
bash "$HERE/tools/install.sh" | sed 's/^/  /' || stop "Installing wf failed." "$AGAIN"
export PATH="$HOME/.local/bin:$PATH"
rc="$HOME/.bashrc"
grep -Fq '.local/bin' "$rc" 2>/dev/null || { printf '\nexport PATH="$HOME/.local/bin:$PATH"  # added by durweg\n' >> "$rc"; ok "Added ~/.local/bin to PATH in $rc"; }
wf --help >/dev/null 2>&1 || stop "wf does not run." "$AGAIN"
ok "wf"

# 5. Claude Code
if ! claude --version >/dev/null 2>&1; then
    say "Installing Claude Code (the download may show no progress)..."
    curl -fsSL https://claude.ai/install.sh | bash || stop "Installing Claude Code failed." "$AGAIN"
fi
claude --version >/dev/null 2>&1 || stop "claude does not run after installing." \
    "Open a new terminal and run again: bash $HERE/install.sh"
ok "Claude Code: $(claude --version 2>&1 | head -n 1)"

# 6. Next
mkdir -p "$RUNS"
echo
say "Next: open a NEW terminal, run: claude"
say "(the first start asks you to log in), and give it this text:"
echo
echo "    Run the Durweg setup workflow with wf: wf start $AIAGENTS_DIR setup --runs $RUNS"
echo "    then follow the skill setup-agents step by step."
echo
