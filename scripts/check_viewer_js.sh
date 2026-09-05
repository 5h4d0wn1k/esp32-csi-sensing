#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTML="$ROOT/tools/csi_3d_viewer.html"
TMP_JS="$(mktemp /tmp/viewer_js.XXXXXX.js)"
trap 'rm -f "$TMP_JS"' EXIT

python3 - "$HTML" "$TMP_JS" <<'PY'
import re, sys
html = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'<script type="module">(.*)</script>\s*</body>', html, re.S)
if not m:
    sys.exit("module <script> block not found in viewer HTML")
open(sys.argv[2], "w", encoding="utf-8").write(m.group(1))
PY

if node --check "$TMP_JS"; then
    echo "PASS: tools/csi_3d_viewer.html module JS is syntactically valid"
else
    echo "FAIL: node --check rejected the extracted viewer JS" >&2
    exit 1
fi
