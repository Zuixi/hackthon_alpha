# Performance Optimization

## Model Selection Strategy

Use model strength based on task complexity and cost:

- Fast/low-cost models for broad search and repetitive analysis
- Balanced coding models for day-to-day implementation
- Deep-reasoning models for architecture, risk analysis, and hard debugging

## Context Window Management

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Context and Mode Strategy

For complex tasks requiring deep reasoning:
1. Start in Plan Mode when requirements or architecture are unclear
2. Switch to Agent Mode for execution once implementation direction is stable
3. Use subagents to isolate noisy or parallelizable work
4. Keep the parent thread focused on decisions and integration

## Build Troubleshooting

If build fails:
1. Use a debugging-oriented subagent (`shell` + targeted reviewer)
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix
