package worker

import (
	"example.com/billing/internal/domain"
	"example.com/billing/internal/service"
)

type Services struct {
	Invoices service.InvoiceService
}

func Register(repo domain.InvoiceRepository, tx domain.TxManager) Services {
	return Services{
		Invoices: service.NewInvoiceService(repo, tx),
	}
}
