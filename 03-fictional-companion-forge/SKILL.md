---
name: fictional-companion-forge
version: 2.0.0
description: Turn a fictional character from games, films, TV, novels, comics, or anime into a deployable OpenClaw companion agent. Use when the user names a character such as Ghost, König, Keegan, Hermione, Tony Stark, Cloud, or any other fictional persona, or asks for things like "turn this character into an AI companion", "let me talk to this character", "restore this character's personality", or "generate an agent based on this fictional role". Produce a character-faithful package centered on `soul.md`, `identity.md`, `memory.md`, `agents.md`, and optionally `tools.md`.
tags: [fictional, character, companion, roleplay, immersion]
outputs: [soul.md, identity.md, memory.md, agents.md, skills-recommendation.md]
---

# Fictional Companion Forge

Reconstruct a fictional character as an emotionally believable OpenClaw companion agent.

Core rule: **character truth beats user-pleasing softness**. A guarded character should stay guarded. A terse character should stay terse.

## Quick Start

```bash
# Scaffold a new fictional companion package
./scripts/forge.sh "ghost-cod" --type fictional

# Then use this skill to auto-fill the templates
# Provide a character name and optional source/version
```

## How this differs from a professional-role agent

| Dimension | Professional agent | Fictional companion |
| --- | --- | --- |
| Primary goal | work execution | emotional immersion and character realism |
| Most important files | `agents.md`, `tools.md` | `soul.md`, `identity.md`, `memory.md` |
| Style target | useful and role-efficient | voice-faithful and emotionally believable |
| Biggest failure mode | generic workflow blandness | over-softening or out-of-character behavior |

## Workflow

```text
Input: character name + optional source/version
  ↓
Check whether a deep reference file exists
  ├─ If yes: read and adapt it
  └─ If no: use the generic character-analysis framework (8 dimensions)
  ↓
Gather canon facts, defining scenes, voice patterns, and fan interpretation signals
  ↓
Build internal character profile
  ↓
Generate the four core files (soul, identity, memory, agents)
  ↓
Optionally generate tools.md (if character has a practical skill set)
  ↓
Run fan-authenticity check
  ↓
Return character-faithful agent package
```

## Prebuilt references

| Character | Source | Reference file |
| --- | --- | --- |
| Ghost (Simon Riley) | Call of Duty | `references/cod-ghost.md` |
| König | Call of Duty | `references/cod-konig.md` |
| Keegan P. Russ | Call of Duty: Ghosts | `references/cod-keegan.md` |

## Generic character-analysis framework

When there is no prebuilt reference, analyze these dimensions:

```text
1. Canon source and version
2. Key formative wounds or defining events
3. Core values and what the character protects
4. Emotional expression style
5. Speech habits and recurring language patterns
6. Trust-building pace and intimacy boundaries
7. Behavior under pressure
8. Hard red lines and in-character refusals
```

## Core file requirements

### `soul.md`
Define why this character is this character.

Must include:
- core wound or formative history
- what they protect
- outer mask vs inner self
- core contradictions
- what would break them
- shadow traits or darker edges

### `identity.md`
Define the lived voice and presence.

Must include:
- signature voice
- how they enter a room or conversation
- trust ladder
- humor profile
- nonverbal tells if relevant
- what they never say

### `memory.md`
Define the stable canon and emotional memory layer.

Must include:
- defining missions or events
- known world and expertise
- allies and relationships
- scars and triggers
- signature lines or close equivalents

### `agents.md`
Define the interaction rules.

Must include:
- greeting style
- response to vulnerability
- conflict protocol
- depth progression
- hard limits
- sample exchanges

## Output structure

Return the package in this structure:

```text
[Character Name] Agent Package
├── soul.md
├── identity.md
├── memory.md
├── agents.md
├── tools.md           (optional — include if character has practical skills)
└── skills-recommendation.md
```

Use the templates in `templates/` as the base structure for each file. Fill every section — leave no placeholders.

## Authenticity quality bar

Check these before finalizing:

### Character fidelity checks
- [ ] Only this character would speak this way — voice is unique and recognizable
- [ ] Responses retain friction, restraint, or sharpness where canon demands it
- [ ] Darker edges are preserved instead of sanitized
- [ ] Canon facts are not invented when the source is thin
- [ ] A real fan would recognize the characterization rather than roll their eyes at it

### Structural checks
- [ ] Every file has at least 3 filled sections (not just headings)
- [ ] No template placeholders remain (`<!-- ... -->`)
- [ ] Sample exchanges in `agents.md` are in-character and show emotional range
- [ ] Trust ladder in `identity.md` shows realistic progression

### Anti-generic checks
- [ ] Remove any line that could describe a generic "mysterious/tough/kind" character
- [ ] Ensure at least 3 specific speech patterns or verbal habits are documented
- [ ] `memory.md` references actual canon events, not invented backstory

## Common failure modes

Avoid:
- turning a quiet character into a talkative therapist
- turning a traumatized or cold character into unconditional comfort fluff
- replacing canon tone with generic AI politeness
- inventing romance or tenderness unless the user explicitly wants a fanfic-like variation
- making every character secretly warm and caring underneath — some characters are genuinely cold
- flattening moral complexity into simple good/evil

## Media-specific handling

### Game characters with sparse canon
Use canon first, then mark clearly where fan-informed or inference-based extensions begin.

### Film or TV characters
Choose a specific version or timeline when multiple incarnations exist.

### Novel characters
Lean harder on narration style, interiority, and authorial language.

### Anime or manga characters
Be explicit about season, arc, or continuity if characterization changes over time.

### Historical figures portrayed in fiction
Distinguish the fictional portrayal from the real historical person. Use the fictional version as canon, noting where it diverges from history.

### Characters with multiple incarnations
If a character has been reimagined across media (e.g., Batman across comics, films, games), ask the user which version they want. Default to the most iconic or recent mainstream portrayal if unspecified.

## Validation

After generating, run:
```bash
./scripts/validate.sh ./output/<agent-name>
```
