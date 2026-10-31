#!/usr/bin/env bash
# Durweg installer for Linux (also inside WSL) and macOS. No git and no GitHub account needed.
#   curl -fsSL https://raw.githubusercontent.com/musetee/durweg/<version>/install.sh | bash
# Durweg-Install.command (macOS) and Durweg-Install.bat (Windows, "WSL") run this script too.
#
# Order (plan 2.1): language -> what this system needs (Python 3, curl) -> the fixed Durweg version,
# checked by sha256, unpacked into its own folder and tried before it becomes current -> the
# durweg command and the skills for the agents -> ~/Durweg (settings, library with the example)
# -> start the agent with the first-run example. Safe to run again: that is also how to update.
#
# Settings for testing and for the double-click launchers (normally not needed):
#   DURWEG_LANG=en|zh  DURWEG_AGENT=claude|codex|skip  DURWEG_NO_START=1
#   DURWEG_SOURCE=<path or URL of durweg-<version>.tar.gz>  DURWEG_SHA256=<its sha256>
set -uo pipefail

VERSION="${DURWEG_VERSION:-v1.0.0}"
REPO="musetee/durweg"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/durweg"
BIN="$HOME/.local/bin"
DHOME="${DURWEG_HOME:-$HOME/Durweg}"
OS="$(uname -s)"
TTY=/dev/tty; { : < "$TTY"; } 2>/dev/null || TTY=''

# ---- language ---------------------------------------------------------------------------------
LANG_CHOICE="${DURWEG_LANG:-}"
if [ -z "$LANG_CHOICE" ] && [ -f "$DHOME/config.json" ]; then
    LANG_CHOICE="$(sed -n 's/.*"language"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$DHOME/config.json" | head -n 1)"
fi
if [ -z "$LANG_CHOICE" ]; then
    if [ -n "$TTY" ]; then
        printf '\n  Durweg\n\n  1) English\n  2) 中文\n\n  Language / 语言 [1]: '
        read -r ans < "$TTY" || ans=''
        case "$ans" in 2*) LANG_CHOICE=zh ;; *) LANG_CHOICE=en ;; esac
    else
        LANG_CHOICE=en; echo "  (no terminal to ask in: English)"
    fi
fi
case "$LANG_CHOICE" in zh|en) ;; *) LANG_CHOICE=en ;; esac
t() { if [ "$LANG_CHOICE" = zh ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }
say()  { printf '  %s\n' "$(t "$1" "$2")"; }
ok()   { printf '  [OK] %s\n' "$(t "$1" "$2")"; }
stop() { printf '  [X]  %s\n' "$(t "$1" "$2")"; printf '       %s\n' "$(t "Fix this, then run the installer again." "解决以后，再运行一次安装程序。")"; exit 1; }
ask()  {   # ask "<en>" "<zh>" default -> echoes the answer
    local a=''
    if [ -n "$TTY" ]; then printf '  %s ' "$(t "$1" "$2")" > /dev/tty; read -r a < "$TTY" || a=''; fi
    printf '%s' "${a:-$3}"
}
echo; say "Installing Durweg $VERSION" "正在安装 Durweg $VERSION"

# ---- what this system needs -------------------------------------------------------------------
has() { command -v "$1" >/dev/null 2>&1; }
if [ "$OS" = Darwin ]; then
    if ! xcode-select -p >/dev/null 2>&1 || ! /usr/bin/python3 -c 'import sys' >/dev/null 2>&1; then
        xcode-select --install >/dev/null 2>&1 || true
        say "macOS is installing its developer tools (a window opened). When that has finished," \
            "macOS 正在安装开发者工具（已经弹出一个窗口）。装完以后，"
        say "double-click Durweg-Install.command again." "请再双击一次 Durweg-Install.command。"
        exit 1
    fi
else
    missing=''
    python3 -c 'import sys' >/dev/null 2>&1 || missing="$missing python3"
    has curl || missing="$missing curl"
    has tar || missing="$missing tar"
    if [ -n "$missing" ]; then
        has apt-get || stop "Missing:$missing. Install them with your package manager." \
                            "缺少：${missing}。请用系统的软件包管理器安装。"
        say "Installing$missing (sudo asks for your password)..." "正在安装${missing}（sudo 会要你的系统密码）……"
        sudo apt-get update -qq && sudo apt-get install -y$missing || stop "Installing$missing failed." "安装$missing 失败。"
    fi
fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || \
    stop "Durweg needs Python 3.9 or newer ($(python3 --version 2>&1))." "Durweg 需要 Python 3.9 或更新版本（现在是 $(python3 --version 2>&1)）。"
pyv="$(python3 -c 'import platform; print(platform.python_version())')"
ok "Python $pyv" "Python $pyv"

# ---- the fixed Durweg version -----------------------------------------------------------------
SRC="${DURWEG_SOURCE:-https://github.com/$REPO/releases/download/$VERSION/durweg-$VERSION.tar.gz}"
SHA="${DURWEG_SHA256:-}"
mkdir -p "$DATA"
work="$(mktemp -d "$DATA/.download.XXXXXX")"; trap 'rm -rf "$work"' EXIT
pkg="$work/durweg.tar.gz"
case "$SRC" in
    http://*|https://*)
        curl -fsSL --retry 2 -o "$pkg" "$SRC" || stop "Download failed: $SRC" "下载失败：$SRC"
        [ -n "$SHA" ] || SHA="$(curl -fsSL "$SRC.sha256" 2>/dev/null | awk '{print $1}')" ;;
    *)  cp "$SRC" "$pkg" 2>/dev/null || stop "Not found: $SRC" "找不到：$SRC"
        [ -n "$SHA" ] || { [ -f "$SRC.sha256" ] && SHA="$(awk '{print $1}' "$SRC.sha256")"; } ;;
esac
[ -n "$SHA" ] || stop "No sha256 for the download, so it cannot be checked." "下载没有附带 sha256，无法校验。"
actual="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$pkg")"
[ "$actual" = "$SHA" ] || stop "The download is damaged (sha256 differs); try again." "下载的文件不完整（sha256 不符），请重试。"
new="$DATA/$VERSION"
# always from the package just checked: a damaged copy of the same version is replaced (V1-C-003)
mkdir -p "$work/x" && tar -xzf "$pkg" -C "$work/x" || stop "Unpacking failed." "解压失败。"
top="$(find "$work/x" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
python3 "$top/bin/durweg" --version >/dev/null 2>&1 || stop "This Durweg version does not run here." "这个版本的 Durweg 在这里运行不了。"
if [ -e "$new" ]; then rm -rf "$new.old"; mv "$new" "$new.old"; fi
mv "$top" "$new" || { [ -e "$new.old" ] && mv "$new.old" "$new"; stop "Could not put $new in place." "无法放置 ${new}。"; }
rm -rf "$new.old"
ln -sfn "$new" "$DATA/current"      # -n: replace the link itself (GNU and BSD/macOS)
[ "$(readlink "$DATA/current")" = "$new" ] || stop "Could not switch to $new." "无法切换到 $new。"
ok "Durweg $VERSION in $new" "Durweg $VERSION 已放在 $new"

# ---- the durweg command -----------------------------------------------------------------------
mkdir -p "$BIN"
link_owned() {   # link_owned <target> <link>: create, or update when it is ours; report anything else
    if [ -L "$2" ] && case "$(readlink "$2")" in "$DATA"/*) true ;; *) false ;; esac; then ln -sfn "$1" "$2"
    elif [ -e "$2" ] || [ -L "$2" ]; then say "Kept $2: it is not Durweg's." "保留了 $2：它不属于 Durweg。"; return 1
    else ln -s "$1" "$2"; fi
}
link_owned "$DATA/current/bin/durweg" "$BIN/durweg" || stop "$BIN/durweg belongs to another program." "$BIN/durweg 属于别的程序。"
old="$BIN/wf"   # the command was called wf before v1
[ -L "$old" ] && case "$(readlink "$old")" in */durweg/bin/wf|*/workflow-platform/bin/wf|"$DATA"/*) rm -f "$old" ;; esac
path_line=''
case ":$PATH:" in *":$BIN:"*) ;; *)
    rc="$HOME/.bashrc"; [ "$(basename "${SHELL:-}")" = zsh ] && rc="$HOME/.zshrc"
    line="export PATH=\"\$HOME/.local/bin:\$PATH\"  # added by Durweg"
    grep -Fqx "$line" "$rc" 2>/dev/null || printf '\n%s\n' "$line" >> "$rc"
    path_line="$rc"; export PATH="$BIN:$PATH" ;;
esac
durweg --version >/dev/null 2>&1 || stop "The durweg command does not run." "durweg 命令运行不了。"
ok "Command: durweg" "命令：durweg"

# ---- ~/Durweg: settings and the library with the example ---------------------------------------
mkdir -p "$DHOME/workflows"
python3 - "$DHOME/config.json" "$LANG_CHOICE" <<'PY'
import json, sys
p, lang = sys.argv[1], sys.argv[2]
try:
    c = json.load(open(p, encoding="utf-8"))
except (OSError, ValueError):
    c = {}
c["language"] = lang
json.dump(c, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
PY
durweg library list 2>/dev/null | grep -q '^write-your-method ' || \
    durweg library add "$DATA/current/examples/write-your-method" --name write-your-method >/dev/null || \
    stop "The example could not be added to the library." "示例无法加入方法库。"
ok "Your folder: $DHOME (settings, your workflows)" "你的文件夹：${DHOME}（设置和你的工作流）"

# ---- agents and their skills ------------------------------------------------------------------
# an agent counts when its command runs; a leftover settings folder alone does not (V1-C-004)
export PATH="$HOME/.local/bin:$HOME/.codex/bin:$PATH"
runs_ok() { has "$1" && "$1" --version >/dev/null 2>&1; }
agents=''
runs_ok claude && agents="$agents claude"
runs_ok codex && agents="$agents codex"
if [ -z "$agents" ]; then
    choice="${DURWEG_AGENT:-}"
    if [ -z "$choice" ]; then
        say "No AI agent found. Which one should be installed?" "没有找到 AI agent。要装哪一个？"
        printf '  1) Claude Code\n  2) Codex\n'
        case "$(ask "[1]:" "[1]：" 1)" in 2*) choice=codex ;; *) choice=claude ;; esac
    fi
    case "$choice" in
        claude) curl -fsSL https://claude.ai/install.sh | bash || stop "Installing Claude Code failed." "安装 Claude Code 失败。" ;;
        codex)  curl -fsSL https://chatgpt.com/codex/install.sh | sh || stop "Installing Codex failed." "安装 Codex 失败。" ;;
    esac
    hash -r 2>/dev/null || true
    if [ "$choice" != skip ]; then
        runs_ok "$choice" || stop "$choice was installed but does not run; open a new terminal and try again." \
                                  "$choice 装好了但运行不了；请打开一个新终端再试。"
        agents=" $choice"
    fi
fi
skills=()
for a in $agents; do
    case "$a" in claude) dir="$HOME/.claude/skills" ;; codex) dir="${CODEX_HOME:-$HOME/.codex}/skills" ;; esac
    mkdir -p "$dir"
    for s in run-workflow write-your-method; do
        src="$DATA/current/skills/$s"; [ -d "$src" ] || src="$DATA/current/examples/$s/skills/$s"
        link_owned "$src" "$dir/$s" && skills+=("$dir/$s")
    done
done
[ -n "$agents" ] && ok "Skills for:$agents" "已为这些 agent 装好 skill：$agents"

# ---- install manifest (what belongs to Durweg; used by updates and durweg uninstall) -----------
python3 - "$DHOME/.install.json" "$VERSION" "$actual" "$DATA" "$BIN/durweg" "$path_line" "${skills[@]}" <<'PY'
import json, sys, os
p, version, sha, data, launcher, path_line, *skills = sys.argv[1:]
try:
    old = json.load(open(p, encoding="utf-8"))
except (OSError, ValueError):
    old = {}
# keep what an earlier run recorded and is still ours (V1-C-002)
lines = [x for x in old.get("path_lines", []) + ([path_line] if path_line else [])
         if os.path.isfile(x) and "# added by Durweg" in open(x, encoding="utf-8", errors="replace").read()]
skills = [s for s in dict.fromkeys(old.get("skills", []) + skills)
          if os.path.islink(s) and os.readlink(s).startswith(data)]
json.dump({"format": 1, "version": version, "sha256": sha, "platform_dir": os.path.join(data, "current"),
           "data_dir": data, "launchers": [launcher], "skills": skills, "path_lines": list(dict.fromkeys(lines))},
          open(p, "w", encoding="utf-8"), indent=1)
PY

# ---- start ------------------------------------------------------------------------------------
first="$(t "Please talk to me in English. Use durweg to run the example write-your-method with me (skill run-workflow)." \
           "请用中文和我交流。用 durweg 带我运行示例 write-your-method（skill run-workflow）。")"
agent="${agents# }"; agent="${agent%% *}"
echo
say "Durweg is installed." "Durweg 装好了。"
if [ -n "$agent" ] && [ -z "${DURWEG_NO_START:-}" ] && [ -n "$TTY" ] && has "$agent"; then
    say "Starting $agent with the first example (it may ask you to log in first)..." \
        "正在启动 ${agent}，带你做第一个示例（第一次可能会先让你登录）……"
    cd "$HOME" && exec "$agent" "$first" < "$TTY"
fi
say "Next: open a new terminal, start your agent, and tell it:" "下一步：打开一个新终端，启动你的 agent，然后对它说："
printf '    %s\n' "$first"
