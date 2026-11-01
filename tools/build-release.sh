#!/usr/bin/env bash
# Build the files of a Durweg release from a commit (default HEAD) into dist/:
#   bash tools/build-release.sh v1.0.0-rc1 [commit]
# durweg-<version>.tar.gz and .zip (top folder durweg-<version>/), each with a .sha256 file,
# and the double-click launchers (Durweg-Install.bat, Durweg-Install.command zipped). Prints the
# commit and the sha256 values for the release notes / the acceptance report.
set -euo pipefail
VERSION="${1:?version, e.g. v1.0.0-rc1}"
COMMIT="$(git rev-parse "${2:-HEAD}")"
cd "$(git rev-parse --show-toplevel)"
# every place that names the version agrees with the release (plan 4.6)
v="${VERSION#v}"
check_version() {   # file, the text that must be in it at that commit
    git show "$COMMIT:$1" | grep -qF -- "$2" || { echo "$1 does not say $2 (release $VERSION)" >&2; exit 1; }
}
check_version durweg/__init__.py "__version__ = \"$v\""
check_version install.sh "v$v}"
check_version Durweg-Install.bat "\$Version = 'v$v'"
check_version Durweg-Install.command "VERSION=\"v$v\""
check_version .claude-plugin/plugin.json "\"version\": \"$v\""
mkdir -p dist
git archive --format=tar.gz --prefix="durweg-$VERSION/" -o "dist/durweg-$VERSION.tar.gz" "$COMMIT"
git archive --format=zip --prefix="durweg-$VERSION/" -o "dist/durweg-$VERSION.zip" "$COMMIT"
# the installer's packages never carry the plugin's files (.gitattributes export-ignore; CP-R-001)
if tar -tzf "dist/durweg-$VERSION.tar.gz" | grep -qE '/(\.claude-plugin|\.gitattributes)(/|$)' ||
   python3 -c 'import sys, zipfile; sys.exit(not any(".claude-plugin" in n or n.endswith(".gitattributes") for n in zipfile.ZipFile(sys.argv[1]).namelist()))' "dist/durweg-$VERSION.zip"; then
    echo "the release packages contain .claude-plugin or .gitattributes" >&2; exit 1
fi
for f in "dist/durweg-$VERSION.tar.gz" "dist/durweg-$VERSION.zip"; do
    python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest(), sys.argv[1].split("/")[-1])' "$f" > "$f.sha256"
done
for f in Durweg-Install.bat Durweg-Install.command; do
    [ -f "$f" ] && git show "$COMMIT:$f" > "dist/$f"
done
[ -f dist/Durweg-Install.command ] && (cd dist && chmod +x Durweg-Install.command && rm -f Durweg-Install-macOS.zip && python3 -c '
import zipfile, os
z = zipfile.ZipFile("Durweg-Install-macOS.zip", "w")
i = zipfile.ZipInfo("Durweg-Install.command"); i.external_attr = 0o100755 << 16
z.writestr(i, open("Durweg-Install.command", "rb").read()); z.close()')
echo "commit $COMMIT"
cat dist/*.sha256
