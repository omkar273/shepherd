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

