# CLAUDE.md

Context for Claude Code working in this repository. Read this before making any changes.

## Quick Reference

| What           | Detail                              |
|----------------|-------------------------------------|
| Repo type      | GitHub profile README               |
| Owner          | Tkeersemaker (beginner programmer)  |
| Content file   | README.md only                      |
| Default branch | main                                |
| Live URL       | https://github.com/Tkeersemaker     |

## Repo Structure

```
Tkeersemaker/
├── CLAUDE.md        # This file — AI context
└── README.md        # Profile page (the only content that matters)
```

No build system. No tests. No dependencies. No CI. This is intentional.

## Bash Commands

```bash
# Check what has changed before committing
git diff README.md

# Stage and commit the README
git add README.md
git commit -m "Update README: <short description>"

# Push to remote on a feature branch
git push -u origin claude/<branch-name>
```

## Branch Strategy

- Default remote branch: `main`
- AI-assisted work: `claude/<short-description>` (e.g. `claude/expand-bio`)
- Always open a PR from `claude/*` into `main` — do not push directly to `main`

## README Conventions

- GitHub-flavored Markdown only
- Emoji are appropriate and encouraged — this is a personal page
- Keep it short: a profile README should be skimmable in under 30 seconds
- Tone: casual, friendly, first-person ("I'm learning...", not "The owner is...")
- Do not use corporate or formal language
- Do not add badges, stats widgets, or third-party embeds unless explicitly asked

## Owner Context

The owner is actively learning to program. This means:
- Keep all suggested content accurate and honest — do not overclaim skills
- Avoid jargon; if a tech term appears it is fine, but do not introduce unexplained acronyms
- Encouragement is appropriate; this is a personal space

## What NOT to Do

- Do NOT create `package.json`, `.github/workflows/`, `.gitignore`, or any config files
- Do NOT add a LICENSE file unless asked
- Do NOT rewrite the README in a formal or resume-style voice
- Do NOT add sections like "Technologies I Use" or "GitHub Stats" without being asked
- Do NOT push directly to `main` — always use a `claude/*` branch and PR
- Do NOT add more than one file per task unless explicitly instructed
- Do NOT alter CLAUDE.md unless the owner asks for it to be updated

## Verification Checklist

Before finishing any task, confirm:
- [ ] Only README.md was changed (unless something else was explicitly requested)
- [ ] README still renders valid Markdown (no broken syntax)
- [ ] Tone matches the existing casual, personal style
- [ ] No unrequested files were created
- [ ] Commit message is short and describes the change plainly

## Context Management

- Use `/clear` between unrelated tasks
- This repo has no code to analyse — tasks are short; context should stay small
- If a task feels large or unclear, ask one clarifying question before starting

## Future .claude/ Structure

If modular rules are added later, use:

```
.claude/
└── rules/
    ├── readme-style.md    # Writing style rules for README edits
    └── git-workflow.md    # Branch and commit conventions
```

Do not create this structure until the owner requests it.
