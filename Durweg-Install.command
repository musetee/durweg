#!/usr/bin/env bash
# Durweg-Install.command: double-click on macOS to install Durweg (also runs on Linux).
# It runs install.sh of this Durweg version. A durweg-rc.json next to this file names a release
# candidate package instead ({"version", "tar", "tar_sha256", optional "guide"}): used for testing before a release.
VERSION="v1.1.2"
here="$(cd "$(dirname "$0")" && pwd)"
cd "$HOME" || exit 1
rc="$here/durweg-rc.json"
if [ -f "$rc" ]; then
    get() { /usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$rc" "$1" 2>/dev/null; }
    export DURWEG_VERSION="$(get version)" DURWEG_SOURCE="$here/$(get tar)" DURWEG_SHA256="$(get tar_sha256)"
    g="$(get guide)"; [ -n "$g" ] && export DURWEG_GUIDE="$g"      # the guide of a test version
    script="$(mktemp)"
    tar -xzOf "$DURWEG_SOURCE" "durweg-$DURWEG_VERSION/install.sh" > "$script" && bash "$script"
    status=$?
else
    export DURWEG_VERSION="$VERSION"
    if s="$(curl -fsSL --max-time 60 "https://raw.githubusercontent.com/musetee/durweg/$VERSION/install.sh")"; then
        bash -c "$s"; status=$?
    else
        echo "  Cannot download the installer from GitHub. Check the internet connection and try again."
        echo "  无法从 GitHub 下载安装程序。请检查网络连接后重试。"
        status=1
    fi
fi
echo
read -r -p "Press Enter to close / 按回车键关闭 ..." _
exit $status
