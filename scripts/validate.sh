#!/usr/bin/env bash
#
# validate.sh — Validate an OpenClaw agent package for completeness and quality.
#
# Usage:
#   ./scripts/validate.sh <agent-dir>
#   ./scripts/validate.sh ./output/my-agent
#   ./scripts/validate.sh ./output/my-agent --strict
#

set -euo pipefail

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}ℹ${NC}  $*"; }
ok()    { echo -e "${GREEN}✓${NC}  $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
error() { echo -e "${RED}✗${NC}  $*"; }

# --- Parse arguments ---
AGENT_DIR=""
STRICT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --strict) STRICT=true; shift ;;
        --help|-h)
            cat <<EOF
${BOLD}OpenClaw Agent Validator${NC}

${BOLD}Usage:${NC}
  $0 <agent-directory> [--strict]

${BOLD}Options:${NC}
  --strict    Treat warnings as errors (non-zero exit on warnings)
  --help      Show this help

${BOLD}Checks performed:${NC}
  - Required files exist (soul.md, identity.md, memory.md, agents.md)
  - Files are non-empty
  - Template placeholders have been filled in
  - Minimum content depth (heading count, word count)
  - META.yaml exists and has required fields

EOF
            exit 0
            ;;
        -*) error "Unknown option: $1"; exit 1 ;;
        *)  AGENT_DIR="$1"; shift ;;
    esac
done

if [[ -z "$AGENT_DIR" ]]; then
    error "Agent directory is required."
    echo "Usage: $0 <agent-directory> [--strict]"
    exit 1
fi

if [[ ! -d "$AGENT_DIR" ]]; then
    error "Directory not found: $AGENT_DIR"
    exit 1
fi

echo ""
echo -e "${BOLD}Validating agent package: ${CYAN}$AGENT_DIR${NC}"
echo ""

ERRORS=0
WARNINGS=0

# --- Check: Required files ---
REQUIRED_FILES=("soul.md" "identity.md" "memory.md" "agents.md")
OPTIONAL_FILES=("tools.md" "skills-recommendation.md" "META.yaml")

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$AGENT_DIR/$file" ]]; then
        ok "Found $file"
    else
        error "Missing required file: $file"
        ((ERRORS++))
    fi
done

for file in "${OPTIONAL_FILES[@]}"; do
    if [[ -f "$AGENT_DIR/$file" ]]; then
        ok "Found $file (optional)"
    else
        warn "Missing optional file: $file"
        ((WARNINGS++))
    fi
done

# --- Check: Files are non-empty and have content ---
check_file_content() {
    local file="$1"
    local filepath="$AGENT_DIR/$file"
    local label="$file"

    if [[ ! -f "$filepath" ]]; then
        return
    fi

    local size
    size=$(wc -c < "$filepath" | tr -d ' ')
    local words
    words=$(wc -w < "$filepath" | tr -d ' ')
    local headings
    headings=$(grep -c '^##' "$filepath" 2>/dev/null || echo 0)

    # Check if file is basically empty
    if [[ "$size" -lt 50 ]]; then
        error "$label is nearly empty ($size bytes)"
        ((ERRORS++))
        return
    fi

    # Check for unfilled template placeholders
    local placeholders
    placeholders=$(grep -c '<!-- .*-->' "$filepath" 2>/dev/null || echo 0)
    local filled_sections
    filled_sections=$((headings > 0 ? headings : 0))

    if [[ "$placeholders" -gt 0 && "$words" -lt 100 ]]; then
        warn "$label appears to still contain unfilled template placeholders ($placeholders found, only $words words)"
        ((WARNINGS++))
    fi

    # Word count thresholds
    if [[ "$words" -lt 50 ]]; then
        warn "$label has very little content ($words words) — consider adding more depth"
        ((WARNINGS++))
    elif [[ "$words" -ge 100 ]]; then
        ok "$label has good content depth ($words words, $headings sections)"
    else
        info "$label has basic content ($words words)"
    fi
}

echo ""
echo -e "${BOLD}Content checks:${NC}"

for file in "${REQUIRED_FILES[@]}" "${OPTIONAL_FILES[@]}"; do
    check_file_content "$file"
done

# --- Check: META.yaml ---
echo ""
echo -e "${BOLD}Metadata checks:${NC}"

META_FILE="$AGENT_DIR/META.yaml"
if [[ -f "$META_FILE" ]]; then
    # Check required fields
    for field in "name" "type" "version"; do
        if grep -q "^${field}:" "$META_FILE" 2>/dev/null; then
            ok "META.yaml has '$field' field"
        else
            warn "META.yaml missing '$field' field"
            ((WARNINGS++))
        fi
    done
else
    info "No META.yaml found (optional but recommended)"
fi

# --- Check: soul.md specific checks ---
echo ""
echo -e "${BOLD}Quality checks:${NC}"

quality_check() {
    local file="$1"
    local pattern="$2"
    local label="$3"
    local filepath="$AGENT_DIR/$file"

    if [[ ! -f "$filepath" ]]; then
        return
    fi

    if grep -qi "$pattern" "$filepath" 2>/dev/null; then
        ok "$label"
    else
        warn "$label — not found in $file"
        ((WARNINGS++))
    fi
}

quality_check "soul.md" "belief\|非.谈" "soul.md mentions beliefs or non-negotiables"
quality_check "identity.md" "voice\|语" "identity.md mentions voice characteristics"
quality_check "memory.md" "expert\|expertise\|专" "memory.md mentions expertise areas"
quality_check "agents.md" "sample\|example\|示例" "agents.md contains sample interactions"

# --- Summary ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ "$ERRORS" -eq 0 && "$WARNINGS" -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}All checks passed!${NC} Agent package looks good."
elif [[ "$ERRORS" -eq 0 ]]; then
    echo -e "${YELLOW}${BOLD}Passed with $WARNINGS warning(s).${NC} Consider addressing the warnings above."
else
    echo -e "${RED}${BOLD}Failed: $ERRORS error(s), $WARNINGS warning(s).${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Exit code
if [[ "$ERRORS" -gt 0 ]]; then
    exit 1
elif [[ "$STRICT" == true && "$WARNINGS" -gt 0 ]]; then
    exit 1
else
    exit 0
fi
