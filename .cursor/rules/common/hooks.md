# Hooks System (Cursor)

## Supported Hook Events

Use official Cursor event names in `hooks.json`:

- Lifecycle: `sessionStart`, `sessionEnd`, `stop`
- Generic tool hooks: `preToolUse`, `postToolUse`, `postToolUseFailure`
- Subagent hooks: `subagentStart`, `subagentStop`
- Shell/MCP hooks: `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`
- File hooks: `beforeReadFile`, `afterFileEdit`
- Prompt/context hooks: `beforeSubmitPrompt`, `preCompact`, `afterAgentResponse`, `afterAgentThought`
- Tab-only hooks: `beforeTabFileRead`, `afterTabFileEdit`

## File Location and Path Rules

- Project hooks file: `.cursor/hooks.json`
- Global hooks file: `~/.cursor/hooks.json`
- For project hooks, scripts should use paths relative to project root, e.g. `.cursor/hooks/format.sh`
- For user hooks, scripts are relative to `~/.cursor/`, e.g. `./hooks/audit.sh`

## Safe Policy Defaults

- Prefer fail-open for non-critical observability hooks
- Use `failClosed: true` only for security-critical gates (for example `beforeMCPExecution`)
- Keep `timeout` explicit for long-running checks to avoid blocking workflows
- Use `matcher` to target only relevant tool calls and avoid noisy hooks

## Hook Output Discipline

- Return strict JSON outputs according to each event schema
- Use clear `user_message` when denying actions
- Keep denial reasons actionable, not generic
- Avoid side effects in observational hooks unless explicitly required
