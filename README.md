# Maestro Skills

A skill framework repository for **English teaching**. Skills are Cursor Agent Skills that extend AI capabilities for language learning, assessment, and instruction.

## Structure

```
maestro-skills/
├── skills/                    # Individual skills
│   └── <skill-name>/
│       ├── SKILL.md           # Required - main instructions
│       ├── references/        # Optional - detailed docs
│       ├── scripts/           # Optional - utility scripts
│       └── assets/            # Optional - data files
├── .gitignore
└── README.md
```

## Skills

| Skill | Description |
|-------|-------------|
| [english-reading-difficulty](skills/english-reading-difficulty/) | Analyzes English reading materials for difficulty (vocabulary, sentence complexity, CEFR alignment) |

## Adding a Skill

1. Create a directory under `skills/` with a lowercase, hyphenated name
2. Add `SKILL.md` with YAML frontmatter (`name`, `description`) and instructions
3. Use `references/`, `scripts/`, and `assets/` as needed for progressive disclosure

## Usage

Skills in this repo can be used as project skills by placing them in `.cursor/skills/` or by linking this repo. See [Cursor Skills documentation](https://docs.cursor.com/context/rules-for-ai#skills) for setup.
