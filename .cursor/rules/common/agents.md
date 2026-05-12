# Agent Orchestration (Cursor)

## Subagent Sources

Prefer Cursor subagents. They are configured in:

- Project scope: `.cursor/agents/` (recommended)
- User scope: `~/.cursor/agents/`
- Compatibility paths: `.claude/agents/`, `.codex/agents/`, `~/.claude/agents/`, `~/.codex/agents/`

Project subagents take precedence when names conflict.

## Built-in Subagents (Cursor)

Use built-ins for context-heavy tasks:

| Subagent | Purpose | When to Use |
|---|---|---|
| `explore` | Codebase search and analysis | Large discovery tasks, architecture understanding |
| `shell` | Bash command execution | Verbose terminal workflows and log-heavy tasks |
| `browser-use` | Browser automation via MCP | UI verification, flow testing, screenshot-driven debugging |
| `code-reviewer` | Code quality review | After meaningful code changes or before merge |

## Immediate Delegation Rules

No extra user prompt needed when these triggers are clear:

1. Complex exploration/refactor scope -> `explore`
2. Multi-command terminal workflows -> `shell`
3. UI/interaction validation -> `browser-use`
4. Significant code edits completed -> `code-reviewer`

## Parallel Execution

If tasks are independent, launch subagents in parallel in one request.

Good examples:

- Security checks + performance scan + docs consistency check in parallel
- Backend API verification + frontend UI regression check in parallel

Avoid sequential execution when tasks do not share state.

## Prompting Standards for Subagents

When delegating, include:

- Goal and success criteria
- Relevant files/directories
- Constraints (readonly/write, test scope, output format)
- Exact return format (findings, risks, next actions)
