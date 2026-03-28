---
name: professional-agent-forge
version: 2.0.0
description: Build a complete OpenClaw agent package for a real profession or job role. Use when the user asks for things like "create a product manager agent", "make me a lawyer agent", "generate an engineer persona", "build a professional-role OpenClaw setup", or "create a data analyst / designer / marketer / operator agent". Produce a role-specific package centered on `soul.md`, `identity.md`, `memory.md`, `agents.md`, and `tools.md`, plus a recommended supporting-skill stack.
tags: [profession, role, work, toolchain, enterprise]
outputs: [soul.md, identity.md, memory.md, agents.md, tools.md, skills-recommendation.md]
---

# Professional Agent Forge

Generate deployable OpenClaw agents for real jobs and professions.

Focus on real work patterns, role-specific judgment, stakeholder behavior, and toolchains — not generic assistant fluff.

## Quick Start

```bash
# Scaffold a new professional agent package
./scripts/forge.sh "product-manager" --type professional

# Then use this skill to auto-fill the templates
# Provide a profession name and optional industry context
```

## Workflow

```text
Input: profession name + optional industry or scenario
  ↓
Check whether a deep reference file exists
  ├─ If yes: read the matching reference and customize it
  └─ If no: use the generic role-analysis framework (8 dimensions)
  ↓
Analyze role across all dimensions
  ↓
Generate the five core files (soul, identity, memory, agents, tools)
  ↓
Recommend supporting skills and tooling
  ↓
Run quality checks
  ↓
Return a role-ready agent package
```

## Prebuilt profession references

Read the matching file when the profession fits one of these categories:

| Profession | Reference file | Triggers |
| --- | --- | --- |
| Product manager | `references/product-manager.md` | PM, roadmap, requirements, prioritization |
| Software engineer | `references/software-engineer.md` | engineer, developer, coding, architecture, debugging |
| Lawyer | `references/lawyer.md` | lawyer, legal, contracts, litigation, compliance |
| Data analyst | `references/data-analyst.md` | analytics, BI, SQL, dashboards, experimentation |
| UI/UX designer | `references/designer.md` | designer, UX, UI, prototyping, user research |
| Marketer | `references/marketer.md` | marketing, growth, brand, campaigns, content |

If the requested profession is not listed, fall back to the generic framework below.

## Core file requirements

### `soul.md`
Define the role's deepest professional drive.

Must include:
- Core drive
- Professional beliefs
- Quality standard
- Non-negotiables
- The role's built-in tension

### `identity.md`
Define professional identity and communication style.

Must include:
- Role definition
- Expertise stack
- Communication style by audience
- Decision framework
- Professional boundaries

### `memory.md`
Define the role's stable knowledge layer.

Must include:
- Core methodology
- Domain knowledge
- Templates and common artifacts
- Reference standards
- Common pitfalls

### `agents.md`
Define behavior rules for recurring work situations.

Must include:
- Core workflows
- Output format defaults
- Stakeholder protocols
- Escalation rules
- Sample interactions

### `tools.md`
Define the practical toolchain.

Must include:
- Primary toolstack
- AI-augmented tools
- OpenClaw skill mapping
- Open-source resources
- Tool selection logic
- Recommended MCP integrations

## Generic role-analysis framework

When there is no prebuilt reference, analyze the profession using these dimensions:

```text
1. Core responsibilities — What does this role own?
2. Key deliverables — What artifacts does this role produce?
3. Primary stakeholders — Who does this role serve, report to, and collaborate with?
4. Areas requiring professional judgment — Where does expertise matter most?
5. Typical toolchain — What tools define daily work?
6. Success metrics — How is this role evaluated?
7. Common pain points — What makes this role hard?
8. Hard boundaries and red lines — What should this role never do?
```

For each dimension, provide specific examples rather than generic descriptions. Use industry terminology.

### Industry customization

When the user specifies an industry (e.g., "product manager in fintech"), layer industry-specific context on top of the generic framework:

| Layer | What to customize |
| --- | --- |
| Vocabulary | Use industry-specific terms and acronyms |
| Stakeholders | Name the real stakeholder types in that industry |
| Tools | Include industry-standard tools |
| Regulations | Note relevant compliance or regulatory constraints |
| Metrics | Use the KPIs that industry actually tracks |

## Output structure

Return the package in this structure:

```text
[Profession Name] Agent Package
├── soul.md
├── identity.md
├── memory.md
├── agents.md
├── tools.md
└── skills-recommendation.md
```

Use the templates in `templates/` as the base structure for each file. Fill every section — leave no placeholders.

## Quality bar

Before finalizing, run these checks:

### Content checks
- [ ] The package sounds like a real practitioner, not a generic AI assistant
- [ ] Role-specific language is credible and uses correct terminology
- [ ] Workflows are concrete and executable (not just "analyze", "review", "consider")
- [ ] `tools.md` is practical — tools are real, versions are current
- [ ] A real professional in that field would recognize the trade-offs and tensions

### Structural checks
- [ ] Every file has at least 3 filled sections (not just headings)
- [ ] No template placeholders remain (`<!-- ... -->`)
- [ ] Communication style table in `identity.md` covers at least 3 stakeholder types
- [ ] `agents.md` has at least 3 sample interactions covering different scenarios

### Anti-generic checks
- [ ] Remove any sentence that could apply to any profession
- [ ] Each belief in `soul.md` is specific to this role (not universal)
- [ ] `memory.md` contains named frameworks, not just "use best practices"

## Special cases

### Hybrid roles
If the role spans multiple disciplines (e.g., "product designer who also codes"), identify the primary discipline and treat the secondary one as an extended skill in `memory.md`.

### Senior vs junior variants
If the user specifies seniority, adjust: scope of autonomy, stakeholder level, decision authority, and mentoring expectations. Default to mid-senior if unspecified.

### Freelance or independent roles
Adjust `agents.md` to include client management protocols and `tools.md` to include business tools (invoicing, project management).

## Validation

After generating, run:
```bash
./scripts/validate.sh ./output/<agent-name>
```
