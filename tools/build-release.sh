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
mkdir -p dist
git archive --format=tar.gz --prefix="durweg-$VERSION/" -o "dist/durweg-$VERSION.tar.gz" "$COMMIT"
git archive --format=zip --prefix="durweg-$VERSION/" -o "dist/durweg-$VERSION.zip" "$COMMIT"
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
