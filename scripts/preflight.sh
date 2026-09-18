#!/usr/bin/env bash
#
# Pre-commit scan. Run from the repository root before every commit:
#
#   bash scripts/preflight.sh
#
# Checks seven failure classes. Exits non-zero if any hard failure is found.
# Warnings are printed but do not block.

set -uo pipefail

FAILURES=0
WARNINGS=0

# Files to scan: tracked source, config, docs and notebooks. Excludes the
# repository's own tooling so that the pattern lists below do not match
# themselves.
FILES=$(git ls-files 2>/dev/null \
  | grep -Ev '^(scripts/preflight\.sh|docs/NUMBERS\.md|docs/DATA\.md)$' \
  || true)

if [ -z "$FILES" ]; then
  echo "No tracked files yet. Run 'git add .' first, or this scan sees nothing."
  FILES=$(find . -type f \
    \( -name '*.py' -o -name '*.ipynb' -o -name '*.yaml' -o -name '*.json' \
       -o -name '*.md' -o -name '*.txt' -o -name '*.sh' \) \
    -not -path './.git/*' \
    -not -name 'preflight.sh' \
    -not -name 'NUMBERS.md' \
    -not -name 'DATA.md')
fi

report() {
  local severity="$1" label="$2" hits="$3"
  if [ -n "$hits" ]; then
    if [ "$severity" = "FAIL" ]; then
      echo "FAIL  $label"
      FAILURES=$((FAILURES + 1))
    else
      echo "WARN  $label"
      WARNINGS=$((WARNINGS + 1))
    fi
    echo "$hits" | sed 's/^/        /'
  else
    echo "ok    $label"
  fi
}

echo "=== preflight ==================================================="

# 1. Hardcoded Drive paths. Everything must go through cwd.paths.find_root.
# src/cwd/paths.py is excluded by design: searching the Drive mount point is
# that module's entire purpose, and it is a search base, not a hardcoded path.
HITS=$(grep -rn "/content/drive/MyDrive" $FILES 2>/dev/null \
  | grep -v 'src/cwd/paths\.py' || true)
report FAIL "no hardcoded Drive paths outside paths.py" "$HITS"

# 2. Email addresses. One personal address is expected in CITATION.cff; any
#    institutional address in code or history is not.
HITS=$(grep -rnE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(edu|com|org|net)' $FILES 2>/dev/null \
  | grep -v 'CITATION.cff' \
  | grep -vE 'facebookresearch|github\.com' || true)
report WARN "no stray email addresses" "$HITS"

# 3. Credentials and API keys.
HITS=$(grep -rniE '(api_key|apikey|secret|password|token)[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{8,}' $FILES 2>/dev/null || true)
report FAIL "no credentials" "$HITS"

# 4. Coordinates and site identifiers. A road name plus a county plus a date
#    locates a private parcel, which is why the paper gives the county only.
# The site name must not appear anywhere. docs/DATA.md documents the naming
# convention without using the real name and is excluded above.
HITS=$(grep -rniE '(nyroad|nyrd)' $FILES 2>/dev/null || true)
report FAIL "no site name in any file" "$HITS"

# Coordinate COLUMN NAMES are allowed in prose and docstrings, since the code
# has to name the columns it strips. They are a failure in any data file.
HITS=$(grep -rniE '(centroid_easting|centroid_northing)' $FILES 2>/dev/null \
  | grep -E '\.(csv|tsv|json|geojson)[:=]' || true)
report FAIL "no coordinate columns in data files" "$HITS"

# UTM-looking coordinate pairs: six-digit easting with a seven-digit northing.
HITS=$(grep -rnE '\b[23][0-9]{5}\.[0-9]+\b.*\b3[0-9]{6}\.[0-9]+\b' $FILES 2>/dev/null || true)
report FAIL "no literal UTM coordinate pairs" "$HITS"

# 5. Oversized files. GitHub rejects anything over 100 MB and warns above 50.
HITS=$(find . -type f -size +10M -not -path './.git/*' 2>/dev/null || true)
report WARN "no files over 10 MB" "$HITS"

# 6. Notebook outputs. Committed output embeds base64 images in git history
#    permanently.
NB=$(echo "$FILES" | grep '\.ipynb$' || true)
HITS=""
if [ -n "$NB" ]; then
  for f in $NB; do
    if grep -q '"output_type"' "$f" 2>/dev/null; then
      HITS="${HITS}${f}"$'\n'
    fi
  done
fi
report FAIL "notebooks have no stored output" "$(echo "$HITS" | sed '/^$/d')"

# 7. Superseded numbers. See the last section of docs/NUMBERS.md.
SUPERSEDED='42\.8|38\.5|35\.8|25\.4|1\.52|17\.1 m3|37\.4 m3|22\.2 m3|19\.0 m3|upper bound|MIN_SIDE'
HITS=$(grep -rnE "$SUPERSEDED" $FILES 2>/dev/null || true)
report WARN "no superseded numbers" "$HITS"

echo "================================================================"
echo "failures: $FAILURES   warnings: $WARNINGS"

if [ "$FAILURES" -gt 0 ]; then
  echo
  echo "Do not commit until the failures above are resolved."
  exit 1
fi

if [ "$WARNINGS" -gt 0 ]; then
  echo
  echo "Warnings do not block a commit, but read each one before proceeding."
fi

echo "Preflight passed."
