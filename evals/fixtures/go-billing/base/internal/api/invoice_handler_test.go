package api

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"example.com/billing/internal/domain"
	"example.com/billing/internal/service"
)

type fakeInvoiceService struct {
	inv *domain.Invoice
	err error
}

func (f fakeInvoiceService) Get(context.Context, string) (*domain.Invoice, error) {
	return f.inv, f.err
}

func (f fakeInvoiceService) Finalize(context.Context, service.FinalizeRequest) (*domain.Invoice, error) {
	return f.inv, f.err
}

func TestGetNotFound(t *testing.T) {
	h := NewInvoiceHandler(fakeInvoiceService{err: domain.ErrNotFound})
	req := httptest.NewRequest(http.MethodGet, "/invoices/x", nil)
	req.SetPathValue("id", "x")
	rec := httptest.NewRecorder()
	h.Get(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got %d", rec.Code)
	}
}
