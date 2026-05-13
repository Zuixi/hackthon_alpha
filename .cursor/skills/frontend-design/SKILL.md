---
name: frontend-design
description: Production frontend patterns for React + Vite + TypeScript + Tailwind CSS + shadcn/ui. Use when building UI features, forms, data fetching, performance optimizations, accessibility fixes, or component architecture in this stack.
disable-model-invocation: true
---

# Frontend Patterns (React + Vite + TS + Tailwind + shadcn/ui)

## When to Use

Apply this skill when the task involves:
- React component design, state flow, or reusable UI abstractions
- Tailwind or shadcn/ui component composition and variants
- Data fetching, caching, and async UX states
- Form validation and submission workflows
- Performance, accessibility, and frontend quality gates

## Stack Defaults (Use Unless User Overrides)

1. Framework/runtime: React + Vite
2. Language safety: TypeScript strict mode
3. Styling: Tailwind CSS + `cn()` + `tailwind-merge`
4. UI primitives: shadcn/ui (Radix-based)
5. Data layer: TanStack Query for server state
6. Forms: react-hook-form + zod resolver
7. Testing: Vitest + React Testing Library; Playwright for E2E

## Delivery Workflow

1. Clarify feature boundaries and UI states (loading, empty, error, success).
2. Implement UI as composable shadcn/ui-based components.
3. Keep business logic in hooks or service modules, not in view markup.
4. Add validation, error handling, and optimistic UX only when justified.
5. Verify accessibility, testability, and bundle impact before finishing.

## Core Patterns

### 1) Components and Styling
- Prefer composition over inheritance.
- Build reusable UI around variant APIs (`cva` style) instead of class sprawl.
- Keep Tailwind classes readable; extract repeated patterns into components.
- Use semantic HTML first, then apply shadcn/ui primitives.

### 2) State Management
- Local UI state: `useState` / `useReducer`.
- Shared cross-tree state: React Context only for low-frequency global state.
- Server state: TanStack Query (query keys, invalidation, retries, caching).
- Do not build custom `useQuery` clones for production defaults.

### 3) Forms and Validation
- Default to `react-hook-form` + `zod`.
- Validate at schema boundary; surface field-level and form-level errors.
- Keep inputs controlled through form library bindings.
- Disable submit during pending requests; prevent duplicate submissions.

### 4) Performance
- Measure first; optimize where evidence exists.
- Use memoization (`useMemo`, `useCallback`, `React.memo`) only for real re-render pressure.
- Use route/component lazy loading via `import()` for heavy screens.
- Use virtualization for long lists.
- Avoid mutating arrays/objects in render paths (e.g. clone before sort).

### 5) Accessibility
- Ensure keyboard navigation for dialogs, dropdowns, and menus.
- Preserve visible focus styles; never remove focus ring without replacement.
- Add proper labels, roles, and `aria-*` only when semantics need support.
- Manage focus on open/close for modals and popovers.

### 6) Vite Engineering Conventions
- Use `import.meta.env` for env values; avoid leaking secrets to client bundles.
- Prefer path aliases and consistent module boundaries.
- Watch bundle size and split large dependencies deliberately.
- Keep lint/typecheck/test as separate CI steps for clear failure signals.

## Anti-Patterns (Avoid)

- Render props as default architecture for new code (hooks are the default).
- Massive page components mixing network, state, and view concerns.
- Unbounded Context usage causing broad re-renders.
- Tailwind class duplication across many files without abstraction.
- Overusing memoization without profiling evidence.
- Type assertions (`as any`) instead of narrowing/validation.

## Done Criteria

Consider work complete only if:
- Types are safe and no avoidable `any` is introduced.
- Loading/empty/error/success states are explicitly handled.
- UI is keyboard-usable and focus behavior is sane.
- Tests cover critical behavior changes (unit/integration/E2E as needed).
- New code follows existing naming and component conventions.

## Progressive Disclosure

If the request is complex, expand in this order:
1. Define data contracts (TypeScript + zod)
2. Define UI composition and variants
3. Wire server state and mutation flows
4. Add tests and accessibility hardening
5. Optimize performance based on measurements
