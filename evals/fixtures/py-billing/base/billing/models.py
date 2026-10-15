from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    PAID = "paid"
    VOID = "void"


@dataclass
class Invoice:
    id: str
    tenant_id: str
    customer_id: str
    status: Status
    total_cents: int
    paid_cents: int = 0
    refunded_cents: int = 0
    void_reason: str = ""
    refund_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Context:
    tenant_id: str
    user_id: str
