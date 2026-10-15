---
paths:
  - "**/*.svelte"
  - "**/*.svelte.ts"
  - "**/*.svelte.js"
---

# Svelte 5

Run the tools first. A tool finding is the authority.

1. If the Svelte MCP server is connected, call its `svelte-autofixer` tool on
   each component that you change. Fix each issue and suggestion, then call
   it again.
2. If the repo has `@sveltejs/mcp` in `package.json`, run
   `npx @sveltejs/mcp svelte-autofixer <file>` instead.
3. The repo's `check` script (`svelte-check`) and its lint script.

Do not install a tool. If the repo has its own Svelte skill or markup lint,
read or run it first. This file adds the lean cut list.

Impact: CRITICAL is a security or data bug, or a feature that does not work.
HIGH is a bug in some cases, a failure that nobody sees, or a slow path.
MEDIUM is code that adds nothing.

## Keep

- **CRITICAL.** Sanitization around `{@html}`. Without it, user text can run
  script.
  ```svelte
  {@html note.body}           <!-- bad -->
  {@html sanitize(note.body)} <!-- good -->
  ```
- **HIGH.** Effect teardown: return a teardown function from `$effect`.
  ```svelte
  $effect(() => { const id = setInterval(tick, 1000) })                         // bad
  $effect(() => { const id = setInterval(tick, 1000); return () => clearInterval(id) }) // good
  ```
- **HIGH.** Loading, error, and empty states for async data that the user
  sees (`{#await}`, `{:catch}`, `{:else}`).
  ```svelte
  {#await orders then list}<List {list} />{/await}  <!-- bad: no pending or error state -->
  {#await orders}<Spinner />{:then list}<List {list} />{:catch e}<Failed {e} />{/await}
  ```
- **HIGH.** A key on an `{#each}` list that can change order.
  ```svelte
  {#each items as item}           <!-- bad: state moves to the wrong row -->
  {#each items as item (item.id)} <!-- good -->
  ```

## Cut

- **HIGH.** `$state` plus an `$effect` that computes it from other state or
  props. It shows a stale value first. Use `$derived`.
  ```svelte
  let count = $state(0); $effect(() => { count = cart.items.length }) // bad
  let count = $derived(cart.items.length)                              // good
  ```
- **HIGH.** `$state` that copies a prop. The copy goes stale when the prop
  changes. Use the prop, or derive a value from it with `$derived`.
  ```svelte
  let { order } = $props(); let qty = $state(order.qty) // bad
  let { order } = $props(); let qty = $derived(order.qty) // good
  ```
- **HIGH.** Svelte 4 syntax in a runes component: `export let`, `$:`,
  `on:click`, `createEventDispatcher`. Runes mode rejects `export let` and
  `$:`, and marks the others as deprecated. Use `$props()`, `$derived`,
  `onclick`, and callback props.
  ```svelte
  export let order; $: total = order.qty * order.price                  // bad
  let { order } = $props(); let total = $derived(order.qty * order.price) // good
  ```
- **MEDIUM.** `{#if x}` or `?.` guards on a prop whose type is required.
  ```svelte
  {#if order}<p>{order.qty}</p>{/if} <!-- bad: order is required -->
  <p>{order.qty}</p>                 <!-- good -->
  ```
- **MEDIUM.** State that you can derive from other state.
- **MEDIUM.** Context or a store for data that goes only one or two levels
  down. Use props.
- **MEDIUM.** Pass-through wrapper components, one-off child components that
  name no concept, and optional props that no caller passes.
- **MEDIUM.** A formatting helper with one or two callers inside one
  component. Write it inline.

## Boundaries

The boundaries are `load` and form-action inputs, route and search params,
form data, and `fetch` responses. Validate the data at these boundaries, on
the server side, not in every component.

## Wiring

- **CRITICAL.** Route files (`+page`, `+layout`, `+server`, `+page.server`).
  A route needs the file name that SvelteKit expects.
  ```sh
  src/routes/orders/page.svelte   # bad: SvelteKit ignores it
  src/routes/orders/+page.svelte  # good
  ```
- **HIGH.** The `load` return type that the page consumes. Use the generated
  `PageData` and `PageProps` types.
  ```svelte
  let { data } = $props()            // bad: data has no type
  let { data }: PageProps = $props() // good
  ```
- **MEDIUM.** Component library exports.
- **MEDIUM.** The repo's design-system component instead of a new one.
