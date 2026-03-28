# Release Notes

## v2.0.0

Skill upgrade and tooling release.

### New: Generation Scripts
- `scripts/forge.sh` — Scaffold a new agent package with one command (interactive or CLI mode)
- `scripts/validate.sh` — Validate package completeness, content depth, and quality
- `scripts/publish.sh` — Dry-run or publish skills to ClawHub

### New: Output Templates
- `templates/` directory with skeleton files for all core outputs: `soul.md`, `identity.md`, `memory.md`, `agents.md`, `tools.md`, `skills-recommendation.md`
- Each template has structured sections with guidance comments
- Templates are auto-copied and customized by `forge.sh`

### Skill Upgrades
- All skills upgraded to v2.0.0 with enhanced frontmatter (version, tags, outputs)
- Added Quick Start sections with script usage examples
- Added `tools.md` generation to Digital IP Agent (was missing)
- Enhanced quality bars with checklist format and anti-generic checks
- Added industry customization layer to Professional Agent Forge
- Added special case handling: team accounts, deceased creators, hybrid roles, seniority variants, multiple incarnations
- Expanded common failure modes for Fictional Companion Forge
- Added validation command to all skill outputs

### Structural Improvements
- Updated repository structure in both READMEs (EN + CN)
- Added scripts documentation with usage examples (bilingual)
- Updated `.gitignore` to exclude `output/` directory

---

## v1.0.0
Initial public release of the OpenClaw Personalized Agent Forge bundle.

Included skills:
- Digital IP Agent
- Professional Agent Forge
- Fictional Companion Forge

Highlights:
- English-first publication pass
- Bilingual repository README files
- Split and cleaned references for professional-role generation
- GitHub publication-ready structure
- ClawHub publish plan included
