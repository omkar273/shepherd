# Svelte 5

If the repo has its own Svelte skill or markup lint, read or run it first. This
file adds only the lean cut list.

## Keep

- Loading, error, and empty states for async data that the user sees.
- Effect teardown: return a teardown function from `$effect`.
- Sanitization around `{@html}`.

## Cut

- `$state` plus an `$effect` that computes it from other state or props.
  Use `let x = $derived(...)`.
- `$state` that copies a prop. Use the prop, or derive a value from it with
  `$derived`.
- State that you can derive from other state.
- `{#if x}` or `?.` guards on a prop whose type is required.
- Context or a store for data that goes only one or two levels down. Use
  props.
- Pass-through wrapper components.
- One-off child components that name no concept.
- Optional props that no caller passes.
- A formatting helper with one or two callers inside one component. Inline it.

## Boundaries

The boundaries are `load` and form-action inputs, route and search params,
form data, and `fetch` responses. Validate the data at these boundaries, on
the server side, not in every component.

## Wiring

- Route files (`+page`, `+layout`, `+server`, `+page.server`).
- The `load` return type that the page consumes.
- Component library exports.
- The repo's design-system component instead of a new one.
