package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"example.com/billing/internal/domain"
)

var ErrInvalidState = errors.New("invalid invoice state")

type FinalizeRequest struct {
	InvoiceID string
}

func (r FinalizeRequest) Validate() error {
	if r.InvoiceID == "" {
		return errors.New("invoice_id is required")
	}
	return nil
}

type InvoiceService interface {
	Get(ctx context.Context, id string) (*domain.Invoice, error)
	Finalize(ctx context.Context, req FinalizeRequest) (*domain.Invoice, error)
}

type invoiceService struct {
	repo domain.InvoiceRepository
	tx   domain.TxManager
}

func NewInvoiceService(repo domain.InvoiceRepository, tx domain.TxManager) InvoiceService {
	return &invoiceService{repo: repo, tx: tx}
}

func (s *invoiceService) Get(ctx context.Context, id string) (*domain.Invoice, error) {
	return s.repo.Get(ctx, id)
}

func (s *invoiceService) Finalize(ctx context.Context, req FinalizeRequest) (*domain.Invoice, error) {
	if err := req.Validate(); err != nil {
		return nil, err
	}
	t, err := s.tx.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer t.Rollback()

	inv, err := s.repo.Get(ctx, req.InvoiceID)
	if err != nil {
		return nil, err
	}
	if inv.Status != domain.StatusDraft {
		return nil, fmt.Errorf("finalize %s from %s: %w", inv.ID, inv.Status, ErrInvalidState)
	}
	var total int64
	for _, l := range inv.Lines {
		total += l.AmountCents
	}
	now := time.Now()
	inv.Status = domain.StatusFinalized
	inv.TotalCents = total
	inv.FinalizedAt = &now
	if err := s.repo.Update(ctx, inv); err != nil {
		return nil, err
	}
	return inv, t.Commit()
}
