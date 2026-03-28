#!/usr/bin/env bash
#
# publish.sh — Publish skills to ClawHub (dry-run by default).
#
# Usage:
#   ./scripts/publish.sh                  # dry-run all skills
#   ./scripts/publish.sh --skill 01       # dry-run specific skill
#   ./scripts/publish.sh --execute        # actually publish
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
error() { echo -e "${RED}✗${NC}  $*" >&2; }

# --- Skill definitions ---
declare -A SKILL_DIRS SKILL_SLUGS SKILL_NAMES SKILL_VERSIONS

SKILL_DIRS[01]="$PROJECT_ROOT/01-digital-ip-agent"
SKILL_SLUGS[01]="digital-ip-agent"
SKILL_NAMES[01]="Digital IP Agent"
SKILL_VERSIONS[01]="2.0.0"

SKILL_DIRS[02]="$PROJECT_ROOT/02-professional-agent-forge"
SKILL_SLUGS[02]="professional-agent-forge"
SKILL_NAMES[02]="Professional Agent Forge"
SKILL_VERSIONS[02]="2.0.0"

SKILL_DIRS[03]="$PROJECT_ROOT/03-fictional-companion-forge"
SKILL_SLUGS[03]="fictional-companion-forge"
SKILL_NAMES[03]="Fictional Companion Forge"
SKILL_VERSIONS[03]="2.0.0"

# --- Parse arguments ---
TARGET_SKILL=""
EXECUTE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skill)   TARGET_SKILL="$2"; shift 2 ;;
        --execute) EXECUTE=true; shift ;;
        --help|-h)
            cat <<EOF
${BOLD}OpenClaw ClawHub Publisher${NC}

${BOLD}Usage:${NC}
  $0 [options]

${BOLD}Options:${NC}
  --skill <id>    Publish a specific skill: 01, 02, or 03
  --execute       Actually run the publish commands (default: dry-run)
  --help          Show this help

${BOLD}Skills:${NC}
  01  Digital IP Agent
  02  Professional Agent Forge
  03  Fictional Companion Forge

${BOLD}Recommended publish order:${NC}
  01 → 02 → 03

EOF
            exit 0
            ;;
        -*) error "Unknown option: $1"; exit 1 ;;
        *)  error "Unexpected argument: $1"; exit 1 ;;
    esac
done

# --- Pre-flight checks ---
echo ""
echo -e "${BOLD}OpenClaw ClawHub Publisher${NC}"
echo ""

if [[ "$EXECUTE" == false ]]; then
    warn "DRY-RUN MODE — add --execute to actually publish"
    echo ""
fi

# Check clawhub CLI exists
if [[ "$EXECUTE" == true ]] && ! command -v clawhub &>/dev/null; then
    error "clawhub CLI not found. Install it first: https://clawhub.dev/docs/cli"
    exit 1
fi

# --- Publish function ---
publish_skill() {
    local id="$1"
    local dir="${SKILL_DIRS[$id]}"
    local slug="${SKILL_SLUGS[$id]}"
    local name="${SKILL_NAMES[$id]}"
    local version="${SKILL_VERSIONS[$id]}"

    if [[ ! -d "$dir" ]]; then
        error "Skill directory not found: $dir"
        return 1
    fi

    if [[ ! -f "$dir/SKILL.md" ]]; then
        error "SKILL.md not found in $dir"
        return 1
    fi

    local cmd="clawhub publish \"$dir\" --slug \"$slug\" --name \"$name\" --version \"$version\""

    echo -e "  ${BOLD}[$id] $name${NC}"
    echo -e "  Dir:     $dir"
    echo -e "  Slug:    $slug"
    echo -e "  Version: $version"
    echo -e "  Command: $cmd"

    if [[ "$EXECUTE" == true ]]; then
        echo ""
        info "Publishing..."
        if eval "$cmd"; then
            ok "Published $name v$version"
        else
            error "Failed to publish $name"
            return 1
        fi
    else
        info "(dry-run — skipping actual publish)"
    fi
    echo ""
}

# --- Run ---
SKILLS_TO_PUBLISH=()

if [[ -n "$TARGET_SKILL" ]]; then
    if [[ -z "${SKILL_DIRS[$TARGET_SKILL]+x}" ]]; then
        error "Unknown skill ID: $TARGET_SKILL (use 01, 02, or 03)"
        exit 1
    fi
    SKILLS_TO_PUBLISH=("$TARGET_SKILL")
else
    SKILLS_TO_PUBLISH=("01" "02" "03")
fi

for skill_id in "${SKILLS_TO_PUBLISH[@]}"; do
    publish_skill "$skill_id"
done

if [[ "$EXECUTE" == false ]]; then
    echo -e "${YELLOW}${BOLD}Dry-run complete.${NC} Run with --execute to publish for real."
else
    echo -e "${GREEN}${BOLD}All done!${NC}"
fi
echo ""
