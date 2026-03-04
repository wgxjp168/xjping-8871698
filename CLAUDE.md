# CLAUDE.md

This file provides guidance to AI assistants working on this repository.

## Project Overview

**Repository**: xjping-8871698
**Status**: Early-stage / in development
**Description**: "我的梦想刚刚开始" — My dream has just begun.

This repository is freshly initialized. As the project grows, update this file to reflect the actual stack, conventions, and workflows.

---

## Repository Structure

```
xjping-8871698/
├── README.md        # Project overview
└── CLAUDE.md        # This file
```

As source code is added, document new directories here (e.g., `src/`, `tests/`, `docs/`).

---

## Git Workflow

### Branches

- `master` — stable, production-ready code
- `claude/<description>` — branches created by AI assistants for specific tasks

### Commits

- Write clear, descriptive commit messages in the imperative mood:
  - Good: `Add user authentication module`
  - Avoid: `fix stuff`, `WIP`, `changes`
- Keep commits focused on a single concern.

### Push

Always push with tracking:
```bash
git push -u origin <branch-name>
```

---

## Development Setup

_No build system or dependencies have been configured yet._

When a stack is chosen, document the following here:
- How to install dependencies
- How to run the development server
- How to run tests
- Required environment variables

---

## Code Conventions

_No language or framework has been selected yet._

When development begins, document conventions such as:
- Language version (e.g., Node 20, Python 3.12, Go 1.22)
- Formatting tool and rules (e.g., Prettier, Black, gofmt)
- Linting rules (e.g., ESLint, Ruff, golangci-lint)
- Naming conventions (files, functions, variables)
- Directory structure patterns

---

## Testing

_No testing framework has been configured yet._

When tests are added, document:
- Test runner and how to invoke it (`npm test`, `pytest`, `go test ./...`)
- Where tests live relative to source files
- Required coverage thresholds

---

## CI/CD

_No CI/CD pipeline has been set up yet._

When a pipeline is added (e.g., GitHub Actions), document:
- What runs on PRs vs. merges to `master`
- How to check pipeline status locally

---

## Notes for AI Assistants

- This file should be kept up to date as the project evolves.
- Before making changes, read all relevant source files to understand existing patterns.
- Avoid over-engineering: implement only what is needed for the current task.
- Never commit secrets, credentials, or `.env` files.
- When in doubt about scope, ask the user before proceeding.
- All AI-initiated work should happen on a `claude/` branch, then be reviewed before merging.
