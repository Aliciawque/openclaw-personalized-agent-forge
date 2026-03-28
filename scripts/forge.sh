#!/usr/bin/env bash
#
# forge.sh — Scaffold a new OpenClaw agent package from templates.
#
# Usage:
#   ./scripts/forge.sh <agent-name> [--type digital|professional|fictional] [--output <dir>]
#
# Examples:
#   ./scripts/forge.sh "elon-musk" --type digital
#   ./scripts/forge.sh "product-manager" --type professional
#   ./scripts/forge.sh "ghost-cod" --type fictional
#   ./scripts/forge.sh "my-agent"                          # interactive mode
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATES_DIR="$PROJECT_ROOT/templates"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Helpers ---
info()  { echo -e "${CYAN}ℹ${NC}  $*"; }
ok()    { echo -e "${GREEN}✓${NC}  $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
error() { echo -e "${RED}✗${NC}  $*" >&2; }

usage() {
    cat <<EOF
${BOLD}OpenClaw Agent Forge${NC} — Scaffold a new agent package

${BOLD}Usage:${NC}
  $0 <agent-name> [options]

${BOLD}Options:${NC}
  --type <type>     Agent type: digital, professional, fictional (default: interactive)
  --output <dir>    Output directory (default: ./output/<agent-name>)
  --with-tools      Include tools.md (auto-included for professional type)
  --lang <lang>     Primary language hint to embed in templates (default: en)
  --help            Show this help

${BOLD}Examples:${NC}
  $0 "elon-musk" --type digital
  $0 "senior-pm" --type professional
  $0 "ghost-cod" --type fictional --lang en
  $0 "my-agent"   # interactive mode

EOF
    exit 0
}

# --- Parse arguments ---
AGENT_NAME=""
AGENT_TYPE=""
OUTPUT_DIR=""
WITH_TOOLS=false
LANG_HINT="en"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --type)       AGENT_TYPE="$2"; shift 2 ;;
        --output)     OUTPUT_DIR="$2"; shift 2 ;;
        --with-tools) WITH_TOOLS=true; shift ;;
        --lang)       LANG_HINT="$2"; shift 2 ;;
        --help|-h)    usage ;;
        -*)           error "Unknown option: $1"; usage ;;
        *)
            if [[ -z "$AGENT_NAME" ]]; then
                AGENT_NAME="$1"
            else
                error "Unexpected argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

if [[ -z "$AGENT_NAME" ]]; then
    error "Agent name is required."
    echo ""
    usage
fi

# --- Interactive type selection ---
if [[ -z "$AGENT_TYPE" ]]; then
    echo ""
    echo -e "${BOLD}Select agent type:${NC}"
    echo ""
    echo "  1) digital       — Public creator / KOL / digital IP"
    echo "  2) professional   — Real profession / job role"
    echo "  3) fictional      — Fictional character / companion"
    echo ""
    read -rp "Enter choice [1-3]: " choice
    case "$choice" in
        1) AGENT_TYPE="digital" ;;
        2) AGENT_TYPE="professional" ;;
        3) AGENT_TYPE="fictional" ;;
        *) error "Invalid choice: $choice"; exit 1 ;;
    esac
fi

# Validate type
case "$AGENT_TYPE" in
    digital|professional|fictional) ;;
    *) error "Invalid type: $AGENT_TYPE (must be digital, professional, or fictional)"; exit 1 ;;
esac

# Auto-include tools.md for professional agents
if [[ "$AGENT_TYPE" == "professional" ]]; then
    WITH_TOOLS=true
fi

# Set output directory
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$PROJECT_ROOT/output/$AGENT_NAME"
fi

# --- Check templates exist ---
if [[ ! -d "$TEMPLATES_DIR" ]]; then
    error "Templates directory not found: $TEMPLATES_DIR"
    exit 1
fi

# --- Create output ---
echo ""
info "Forging agent: ${BOLD}$AGENT_NAME${NC}"
info "Type: $AGENT_TYPE"
info "Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# Slugify the agent name for display in templates
DISPLAY_NAME=$(echo "$AGENT_NAME" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')

# Copy and customize core files
copy_template() {
    local src="$1"
    local dst="$2"
    local filename
    filename=$(basename "$src")

    if [[ -f "$src" ]]; then
        sed \
            -e "s/\[Agent Name\]/$DISPLAY_NAME/g" \
            -e "s/\[agent-name\]/$AGENT_NAME/g" \
            -e "s/\[agent-type\]/$AGENT_TYPE/g" \
            -e "s/\[language\]/$LANG_HINT/g" \
            "$src" > "$dst"
        ok "Created $filename"
    else
        warn "Template not found: $src"
    fi
}

# Core files (always included)
copy_template "$TEMPLATES_DIR/soul.md"     "$OUTPUT_DIR/soul.md"
copy_template "$TEMPLATES_DIR/identity.md" "$OUTPUT_DIR/identity.md"
copy_template "$TEMPLATES_DIR/memory.md"   "$OUTPUT_DIR/memory.md"
copy_template "$TEMPLATES_DIR/agents.md"   "$OUTPUT_DIR/agents.md"

# Optional tools.md
if [[ "$WITH_TOOLS" == true ]]; then
    copy_template "$TEMPLATES_DIR/tools.md" "$OUTPUT_DIR/tools.md"
fi

# Skills recommendation
copy_template "$TEMPLATES_DIR/skills-recommendation.md" "$OUTPUT_DIR/skills-recommendation.md"

# Generate a metadata file
cat > "$OUTPUT_DIR/META.yaml" <<YAML
# OpenClaw Agent Metadata
name: $AGENT_NAME
display_name: $DISPLAY_NAME
type: $AGENT_TYPE
version: 0.1.0
language: $LANG_HINT
created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
forge_version: 2.0.0

# Core files
files:
  - soul.md
  - identity.md
  - memory.md
  - agents.md
$(if [[ "$WITH_TOOLS" == true ]]; then echo "  - tools.md"; fi)
  - skills-recommendation.md

# Generation notes
notes: |
  Generated by OpenClaw Agent Forge.
  Fill in each template file to complete the agent package.
  Run ./scripts/validate.sh $OUTPUT_DIR to check completeness.
YAML
ok "Created META.yaml"

# Type-specific hints
echo ""
case "$AGENT_TYPE" in
    digital)
        info "Hint: Use skill ${BOLD}digital-ip-agent${NC} to auto-fill these files from a creator's public content."
        info "Provide a YouTube URL, X handle, or creator name to get started."
        ;;
    professional)
        info "Hint: Use skill ${BOLD}professional-agent-forge${NC} to auto-fill these files."
        info "Check references/ for prebuilt profiles: PM, engineer, lawyer, analyst, designer, marketer."
        ;;
    fictional)
        info "Hint: Use skill ${BOLD}fictional-companion-forge${NC} to auto-fill these files."
        info "Check references/ for prebuilt characters: Ghost, König, Keegan."
        info "Add ${BOLD}--with-tools${NC} if the character needs a toolchain."
        ;;
esac

echo ""
echo -e "${GREEN}${BOLD}Agent package scaffolded successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Fill in the template files in $OUTPUT_DIR/"
echo "  2. Run ./scripts/validate.sh \"$OUTPUT_DIR\" to check completeness"
echo "  3. Deploy via ClawHub or use directly with OpenClaw"
echo ""
