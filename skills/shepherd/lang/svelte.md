# Svelte 5

If the repo has its own Svelte skill or markup lint, read or run it first. This
file adds only the lean cut list.

## Keep

- Loading, error, and empty states for async data the user sees.
- Effect teardown: return a cleanup function from `$effect`.
- Sanitization around `{@html}`.

## Cut

- `$state` plus an `$effect` that computes it from other state or props.
  Use `let x = $derived(...)`.
- `$state` that copies a prop. Use the prop, or `$derived` from it.
- State that can be derived from other state.
- `{#if x}` or `?.` guards on a prop whose type is required.
- Context or a store for data passed only one or two levels down. Use props.
- Pass-through wrapper components; one-off child components that name no
  concept.
- Optional props that no caller passes.
- A formatting helper with one or two callers inside one component. Inline it.

## Boundaries

`load` and form-action inputs, route and search params, form data, `fetch`
responses. Validate there, on the server side, not in every component.

## Wiring

Route files (`+page`, `+layout`, `+server`, `+page.server`), the `load` return
type the page consumes, component library exports, and the repo's
design-system component over a new one.
