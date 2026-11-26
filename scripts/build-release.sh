#!/usr/bin/env bash
# Builds a release archive that installs offline on Debian 13 x86_64 (docs/adr/0004).
# Contents: Python wheels (Linux x86_64, CPython 3.13) with a hash-pinned lock file,
# the compiled interface and the deploy scripts. Run it on your computer or in CI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/backend/pyproject.toml")"
OUT="$ROOT/dist"
STAGE="$(mktemp -d)/mypds-$VERSION"
PY="${PYTHON:-$ROOT/backend/.venv/bin/python}"
mkdir -p "$STAGE/wheels" "$STAGE/static" "$OUT"

echo "==> Interface"
(cd "$ROOT/frontend" && npm ci --silent && npm run build --silent)
cp -R "$ROOT/frontend/dist/." "$STAGE/static/"

echo "==> Back end (project wheel)"
"$PY" -m pip wheel --quiet --no-deps -w "$STAGE/wheels" "$ROOT/backend"

echo "==> Dependencies (manylinux x86_64 / CPython 3.13 wheels)"
"$PY" -m pip freeze --exclude-editable | grep -viE '^(mypds|pytest|pytest-asyncio|respx|ruff|iniconfig|pluggy|packaging|pygments)==' \
  > "$STAGE/requirements.in"
"$PY" -m pip download --quiet --only-binary=:all: --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 \
  --platform manylinux2014_x86_64 --platform linux_x86_64 --implementation cp --python-version 3.13 \
  -d "$STAGE/wheels" -r "$STAGE/requirements.in"

echo "==> Lock file with SHA-256 hashes"
: > "$STAGE/requirements.lock"
for whl in "$STAGE"/wheels/*.whl; do
  name="$(basename "$whl" | cut -d- -f1 | tr '_' '-')"
  ver="$(basename "$whl" | cut -d- -f2)"
  hash="$(shasum -a 256 "$whl" | cut -d' ' -f1)"
  echo "$name==$ver --hash=sha256:$hash" >> "$STAGE/requirements.lock"
done

cp -R "$ROOT/deploy" "$STAGE/deploy"
echo "$VERSION" > "$STAGE/VERSION"
# macOS tar adds Apple metadata (com.apple.provenance…) that GNU tar warns about on Debian: leave it out
if tar --version 2>/dev/null | grep -q bsdtar; then
  COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -C "$(dirname "$STAGE")" -czf "$OUT/mypds-$VERSION.tar.gz" "mypds-$VERSION"
else
  tar -C "$(dirname "$STAGE")" -czf "$OUT/mypds-$VERSION.tar.gz" "mypds-$VERSION"
fi
(cd "$OUT" && shasum -a 256 "mypds-$VERSION.tar.gz" > "mypds-$VERSION.tar.gz.sha256")
echo "==> $OUT/mypds-$VERSION.tar.gz"
cat "$OUT/mypds-$VERSION.tar.gz.sha256"
