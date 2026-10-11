package memory

import (
	"context"
	"sync"

	"example.com/billing/internal/domain"
	"example.com/billing/internal/types"
)

type InvoiceRepo struct {
	mu       sync.Mutex
	invoices map[string]*domain.Invoice
}

func NewInvoiceRepo() *InvoiceRepo {
	return &InvoiceRepo{invoices: map[string]*domain.Invoice{}}
}

func inScope(ctx context.Context, inv *domain.Invoice) bool {
	return inv.TenantID == types.TenantID(ctx) && inv.EnvironmentID == types.EnvironmentID(ctx)
}

func (r *InvoiceRepo) Get(ctx context.Context, id string) (*domain.Invoice, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	inv, ok := r.invoices[id]
	if !ok || !inScope(ctx, inv) {
		return nil, domain.ErrNotFound
	}
	copied := *inv
	return &copied, nil
}

func (r *InvoiceRepo) Update(ctx context.Context, inv *domain.Invoice) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	existing, ok := r.invoices[inv.ID]
	if !ok || !inScope(ctx, existing) {
		return domain.ErrNotFound
	}
	copied := *inv
	r.invoices[inv.ID] = &copied
	return nil
}

func (r *InvoiceRepo) List(ctx context.Context, customerID string) ([]*domain.Invoice, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []*domain.Invoice
	for _, inv := range r.invoices {
		if inv.CustomerID == customerID && inScope(ctx, inv) {
			copied := *inv
			out = append(out, &copied)
		}
	}
	return out, nil
}

type tx struct{}

func (tx) Commit() error   { return nil }
func (tx) Rollback() error { return nil }

type TxManager struct{}

func (TxManager) Begin(context.Context) (domain.Tx, error) { return tx{}, nil }
