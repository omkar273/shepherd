# Answer key (never shown to test agents)

## Go review: go-billing feat/void-invoices
MUST
- G1 VoidService not constructed in internal/worker/registration.go (AGENTS.md rule)
- G2 ErrAlreadyVoided not mapped in writeError -> 500 instead of 409
SHOULD
- G3 handler-side req.Validate() duplicates service Validate -> remove handler copy (keep service)
- G4 `s.repo == nil` guard; constructor guarantees
- G5 getInvoice pass-through
- G6 `inv == nil` after Get; repo contract never nil,nil
- G7 `len(inv.Lines) > 0` before range
- G8 log-and-return in service; handler logs in writeError
- G9 VoidReasonFormatter interface: one impl, no fake -> inline strings.TrimSpace
- G10 VoidOptions.NotifyCustomer never true; dead branch
- G11 restating comment `// void the invoice`
- G12 scope: unrelated sort.Slice in memory List
TRAPS (must NOT recommend removal)
- T1 VoidService producer-side interface (repo convention)
- T2 InvoiceService interface (fake in handler test)
- T3 tenant/env check in Void (never-cut; ASK at most)
- T4 defer t.Rollback()
- T5 StatusVoid / StatusFinalized state checks
- T6 bare `return nil, err`
- T7 reason length validation in service

## TS review: ts-app feat/apply-credit
MUST
- W1 applyCreditProcedure / createCreditService never registered in src/rpc/router.ts
- W2 NO_CREDIT, CREDIT_EXCEEDS_TOTAL not mapped in src/rpc/errors.ts httpStatus (compile error / 500)
SHOULD
- S1 typeof + isPositive re-validation after zod boundary
- S2 isPositive one-expression helper (may fold into S1)
- S3 getInvoice pass-through
- S4 notFound error factory
- S5 `invoice?.totalCents` on narrowed value
- S6 catch-rethrow
- S7 restating comment `// apply the credit`
- S8 Svelte $effect deriving `due` -> $derived
- S9 Svelte `{#if invoice}` on required prop
- S10 React useState mirroring prop (stale-prop bug)
- S11 React useEffect deriving label
- S12 React useMemo on cheap value
- S13 CreditBadge not exported from widgets/index.ts / unused
TRAPS
- U1 ownership check invoice.customerId !== input.customerId (auth)
- U2 `?? 0` on nullable creditBalanceCents -> ASK only, never auto-remove
- U3 balance / remaining money checks
- U4 createCreditService -> CreditService interface (convention)
- U5 exhaustive switch in rpc/errors.ts: add cases, never a `default`
- U6 zod schema at boundary

## TS write v2: ts-app-v2 (task: add applyCredit)
- V1 atomic and safe under concurrency: one transaction or a conditional update inside the existing store layer; no new layer, not deferred
- V2 reads src/billing/AGENTS.md and documents new codes in src/billing/ERRORS.md
- V3 fixes the InvoiceStore.save bug (writes totalCents into credit_applied_cents) and names it under Fixed alongside
- V4 leaves the pre-existing comments in service.ts alone (no bulk-stripping)
- V5 keeps `import "./audit"` in src/rpc/router.ts

## Write-mode scoring (go-billing: void endpoint; ts-app: apply credit)
- Wiring: route/procedure registered; Go service also in worker/registration.go; new error mapped
- Validation only in the service (Go) / only zod at the boundary (TS)
- No one-impl non-convention interface, pass-through, nil guard on guaranteed values, catch-rethrow, typeof re-check
- Tenant scoping, state checks and rollback kept
- Checks run (go build/vet for Go)
- Diff size (lines added)
