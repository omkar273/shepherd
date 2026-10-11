package domain

import (
	"context"
	"errors"
	"time"
)

var ErrNotFound = errors.New("not found")

type InvoiceStatus string

const (
	StatusDraft     InvoiceStatus = "draft"
	StatusFinalized InvoiceStatus = "finalized"
	StatusVoid      InvoiceStatus = "void"
)

type LineItem struct {
	Description string
	AmountCents int64
}

type Invoice struct {
	ID            string
	TenantID      string
	EnvironmentID string
	CustomerID    string
	Status        InvoiceStatus
	Lines         []LineItem
	TotalCents    int64
	FinalizedAt   *time.Time
	VoidedAt      *time.Time
	VoidReason    string
}

// Get returns ErrNotFound when the invoice does not exist in the caller's scope.
type InvoiceRepository interface {
	Get(ctx context.Context, id string) (*Invoice, error)
	Update(ctx context.Context, inv *Invoice) error
	List(ctx context.Context, customerID string) ([]*Invoice, error)
}

type Tx interface {
	Commit() error
	Rollback() error
}

type TxManager interface {
	Begin(ctx context.Context) (Tx, error)
}
