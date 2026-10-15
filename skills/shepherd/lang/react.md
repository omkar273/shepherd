---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
---

# React

Run the repo's eslint first. If it has `eslint-plugin-react-hooks`, trust
`rules-of-hooks` and `exhaustive-deps` over this list. If the repo uses React
Compiler, all manual memoization is noise. Do not install a tool.

Impact: CRITICAL is a security or data bug, or a feature that does not work.
HIGH is a bug in some cases, a failure that nobody sees, or a slow path.
MEDIUM is code that adds nothing.

## Keep

- **CRITICAL.** Sanitization around `dangerouslySetInnerHTML`. Without it,
  user text can run script.
  ```tsx
  <div dangerouslySetInnerHTML={{ __html: note.body }} />               // bad
  <div dangerouslySetInnerHTML={{ __html: sanitize(note.body) }} />     // good
  ```
- **HIGH.** Effect cleanup, and correct dependency arrays.
  ```tsx
  useEffect(() => { socket.on("msg", onMsg) }, [])                          // bad
  useEffect(() => { socket.on("msg", onMsg); return () => socket.off("msg", onMsg) }, [onMsg]) // good
  ```
- **HIGH.** Loading, error, and empty states for async data that the user
  sees.
  ```tsx
  const { data } = useQuery(q); return <List items={data!} />          // bad
  if (isPending) return <Spinner />; if (error) return <Failed e={error} /> // good
  ```
- **HIGH.** A stable `key` from the data on a list that can change order.
  ```tsx
  items.map((it, i) => <Row key={i} item={it} />)     // bad: state moves to the wrong row
  items.map((it) => <Row key={it.id} item={it} />)    // good
  ```
- **MEDIUM.** Route-level error boundaries.

## Cut

- **HIGH.** `useState(prop)` that copies a prop. The copy goes stale when the
  prop changes. Use the prop.
  ```tsx
  const [total, setTotal] = useState(props.total) // bad
  const total = props.total                        // good
  ```
- **HIGH.** A `useEffect` that computes a value from props or state and sets
  it as state. It renders twice and shows a stale value first. Compute the
  value during render.
  ```tsx
  const [label, setLabel] = useState(""); useEffect(() => setLabel(fmt(qty)), [qty]) // bad
  const label = fmt(qty)                                                            // good
  ```
- **MEDIUM.** `useMemo` or `useCallback` around a cheap value, or for a child
  that is not memoized.
  ```tsx
  const label = useMemo(() => `${qty} items`, [qty]) // bad
  const label = `${qty} items`                       // good
  ```
- **MEDIUM.** A custom hook that wraps one call (`useQuery`, `useState`) for
  one consumer.
- **MEDIUM.** Context for data that goes only one or two levels down. Use
  props.
- **MEDIUM.** Pass-through wrapper components, and optional props that no
  caller passes.
- **MEDIUM.** `if (!data) return null` when the type guarantees `data`.

## Boundaries

The boundaries are URL and search params, form input, API responses,
`localStorage`, and `postMessage`. Validate API responses in the data layer,
not in every component.

## Wiring

- **CRITICAL.** Route registration. A page that no route lists is
  unreachable.
  ```tsx
  routes = [{ path: "/orders", element: <Orders /> }]  // bad: no OrderDetail route
  routes.push({ path: "/orders/:id", element: <OrderDetail /> }) // good
  ```
- **HIGH.** Providers that you mount above every consumer. A missing provider
  throws at runtime or gives the default value.
  ```tsx
  root.render(<App />)                             // bad: useCart() has no provider
  root.render(<CartProvider><App /></CartProvider>) // good
  ```
- **HIGH.** Query keys that match their invalidations. A key that does not
  match leaves stale data on the screen.
  ```tsx
  useQuery({ queryKey: ["order", id] }); invalidateQueries({ queryKey: ["orders", id] }) // bad
  useQuery({ queryKey: ["order", id] }); invalidateQueries({ queryKey: ["order", id] })  // good
  ```
- **MEDIUM.** Exports through the repo's index or barrel file. A new component
  that nothing imports is dead code.
- **MEDIUM.** The repo's design-system component instead of a new or native
  one.
