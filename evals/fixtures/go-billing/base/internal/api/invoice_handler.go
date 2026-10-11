package api

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"

	"example.com/billing/internal/domain"
	"example.com/billing/internal/service"
)

type InvoiceHandler struct {
	invoices service.InvoiceService
}

func NewInvoiceHandler(invoices service.InvoiceService) *InvoiceHandler {
	return &InvoiceHandler{invoices: invoices}
}

func writeError(w http.ResponseWriter, err error) {
	log.Printf("request failed: %v", err)
	switch {
	case errors.Is(err, domain.ErrNotFound):
		http.Error(w, "not found", http.StatusNotFound)
	case errors.Is(err, service.ErrInvalidState):
		http.Error(w, err.Error(), http.StatusConflict)
	default:
		http.Error(w, "internal error", http.StatusInternalServerError)
	}
}

func (h *InvoiceHandler) Get(w http.ResponseWriter, r *http.Request) {
	inv, err := h.invoices.Get(r.Context(), r.PathValue("id"))
	if err != nil {
		writeError(w, err)
		return
	}
	json.NewEncoder(w).Encode(inv)
}

func (h *InvoiceHandler) Finalize(w http.ResponseWriter, r *http.Request) {
	inv, err := h.invoices.Finalize(r.Context(), service.FinalizeRequest{InvoiceID: r.PathValue("id")})
	if err != nil {
		writeError(w, err)
		return
	}
	json.NewEncoder(w).Encode(inv)
}
