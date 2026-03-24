# ClawHub Publishing Plan

This bundle should be published to ClawHub as **three separate skills**, not as one combined bundle.

## Why publish separately
- Each skill has a distinct trigger surface
- ClawHub listings work better when each skill has a tight value proposition
- Users can install only the piece they need

---

## Skill 1: digital-ip-agent

### Suggested slug
`digital-ip-agent`

### Suggested display name
`Digital IP Agent`

### Version
`1.0.0`

### Short changelog
`Initial public release.`

### Positioning
Turn a public creator, blogger, podcaster, YouTuber, or X/Twitter personality into a deployable OpenClaw persona package.

### Publish command
```bash
clawhub publish ./01-digital-ip-agent \
  --slug digital-ip-agent \
  --name "Digital IP Agent" \
  --version 1.0.0 \
  --changelog "Initial public release."
```

---

## Skill 2: professional-agent-forge

### Suggested slug
`professional-agent-forge`

### Suggested display name
`Professional Agent Forge`

### Version
`1.0.0`

### Short changelog
`Initial public release.`

### Positioning
Build a profession-specific OpenClaw agent package with role logic, workflows, and toolchain grounding.

### Publish command
```bash
clawhub publish ./02-professional-agent-forge \
  --slug professional-agent-forge \
  --name "Professional Agent Forge" \
  --version 1.0.0 \
  --changelog "Initial public release."
```

---

## Skill 3: fictional-companion-forge

### Suggested slug
`fictional-companion-forge`

### Suggested display name
`Fictional Companion Forge`

### Version
`1.0.0`

### Short changelog
`Initial public release.`

### Positioning
Turn a fictional character into a character-faithful OpenClaw companion agent.

### Publish command
```bash
clawhub publish ./03-fictional-companion-forge \
  --slug fictional-companion-forge \
  --name "Fictional Companion Forge" \
  --version 1.0.0 \
  --changelog "Initial public release."
```

---

## Publish order recommendation
1. `digital-ip-agent`
2. `professional-agent-forge`
3. `fictional-companion-forge`

This order moves from most generally useful to most niche / stylized.

---

## Pre-publish checklist
- GitHub repo is stable
- root README is polished
- each SKILL.md frontmatter is in English
- no leftover junk files
- ClawHub account is logged in

---

## Login step
```bash
clawhub login
clawhub whoami
```
