# React

## Keep

- Loading, error, and empty states for async data the user sees.
- Effect cleanup, and correct dependency arrays.
- Route-level error boundaries.
- Sanitization around `dangerouslySetInnerHTML`.

## Cut

- `useState(prop)` that copies a prop. Use the prop; the copy goes stale when
  the prop changes.
- A `useEffect` that sets state computed from props or state. Compute it
  during render.
- `useMemo` or `useCallback` around cheap values, or for children that aren't
  memoized. If the repo uses React Compiler, all manual memoization is noise.
- A custom hook wrapping one call (`useQuery`, `useState`) for one consumer.
- Context for data passed only one or two levels down. Use props.
- Pass-through wrapper components; optional props that no caller passes.
- `if (!data) return null` when the type guarantees `data`.

## Boundaries

URL and search params, form input, API responses (validate in the data layer,
not in every component), `localStorage`, `postMessage`.

## Wiring

Route registration, providers mounted above every consumer, query keys that
match their invalidations, exports through the repo's index or barrel file,
and the repo's design-system component over a new or native one.
