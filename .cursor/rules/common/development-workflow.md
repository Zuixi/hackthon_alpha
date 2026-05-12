# Development Workflow

> This file extends [common/git-workflow.md](./git-workflow.md) with the full feature development process that happens before git operations.

The Feature Implementation Workflow describes the development pipeline: research, planning, TDD, code review, and then committing to git.

## Feature Implementation Workflow

0. **Research & Reuse** _(mandatory before any new implementation)_
   - Search the local codebase first for reusable modules/patterns.
   - Verify third-party API behavior with official docs (or Context7 when available).
   - Check mature libraries/packages before hand-rolling utilities.
   - Prefer adapting proven implementations when they satisfy requirements.

1. **Plan First**
   - Use a planning-oriented subagent (custom `planner` if present, otherwise `explore`)
   - Generate planning docs before coding: PRD, architecture, system_design, tech_doc, task_list
   - Identify dependencies and risks
   - Break down into phases

2. **TDD Approach**
   - Use TDD discipline; use custom `tdd-guide` subagent if configured
   - Write tests first (RED)
   - Implement to pass tests (GREEN)
   - Refactor (IMPROVE)
   - Verify 80%+ coverage

3. **Code Review**
   - Use `code-reviewer` subagent immediately after writing code
   - Address CRITICAL and HIGH issues
   - Fix MEDIUM issues when possible

4. **Commit & Push**
   - Detailed commit messages
   - Follow conventional commits format
   - See [git-workflow.md](./git-workflow.md) for commit message format and PR process

5. **Pre-Review Checks**
   - Verify all automated checks (CI/CD) are passing
   - Resolve any merge conflicts
   - Ensure branch is up to date with target branch
   - Only request review after these checks pass

## Cursor-Specific Notes

- For broad codebase exploration, prefer `explore` subagent over manual scattered searches.
- For command-heavy operations, prefer `shell` subagent to isolate noisy terminal output.
- For UI behavior validation, prefer `browser-use` subagent for reproducible browser steps.
