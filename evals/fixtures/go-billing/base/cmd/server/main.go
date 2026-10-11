package main

import (
	"log"
	"net/http"

	"example.com/billing/internal/api"
	"example.com/billing/internal/repository/memory"
	"example.com/billing/internal/service"
	"example.com/billing/internal/worker"
)

func main() {
	repo := memory.NewInvoiceRepo()
	tx := memory.TxManager{}

	invoices := service.NewInvoiceService(repo, tx)
	_ = worker.Register(repo, tx)

	h := api.NewInvoiceHandler(invoices)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /invoices/{id}", h.Get)
	mux.HandleFunc("POST /invoices/{id}/finalize", h.Finalize)

	log.Fatal(http.ListenAndServe(":8080", mux))
}
