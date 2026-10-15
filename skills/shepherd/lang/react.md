---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
---

# React

## Keep

- Loading, error, and empty states for async data that the user sees.
- Effect cleanup, and correct dependency arrays.
- Route-level error boundaries.
- Sanitization around `dangerouslySetInnerHTML`.

## Cut

- `useState(prop)` that copies a prop. Use the prop. The copy becomes stale
  when the prop changes.
- A `useEffect` that computes a value from props or state and sets it as
  state. Compute the value during render.
- `useMemo` or `useCallback` around cheap values, or for children that are not
  memoized. If the repo uses React Compiler, all manual memoization is noise.
- A custom hook that wraps one call (`useQuery`, `useState`) for one consumer.
- Context for data that goes only one or two levels down. Use props.
- Pass-through wrapper components.
- Optional props that no caller passes.
- `if (!data) return null` when the type guarantees `data`.

## Boundaries

The boundaries are URL and search params, form input, API responses,
`localStorage`, and `postMessage`. Validate API responses in the data layer,
not in every component.

## Wiring

- Route registration.
- Providers that you mount above every consumer.
- Query keys that match their invalidations.
- Exports through the repo's index or barrel file.
- The repo's design-system component instead of a new or native one.
