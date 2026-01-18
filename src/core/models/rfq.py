from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RFQStatus(str, Enum):
    """Status of a Request for Quote."""
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    FILLED = "filled"
    CANCELLED = "cancelled"


class QuoteStatus(str, Enum):
    """Status of a Quote."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class QuoteItem(BaseModel):
    """Line item in a quote."""
    description: str
    quantity: float
    unit_price: float
    total_price: float
    currency: str = "USD"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Quote(BaseModel):
    """A quote received from a supply chain provider."""
    id: UUID = Field(default_factory=uuid4)
    rfq_id: UUID
    provider_id: str
    amount: float
    currency: str = "USD"
    contractor_name: Optional[str] = None
    status: QuoteStatus = QuoteStatus.PENDING
    items: List[QuoteItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "rfq_id": str(self.rfq_id),
            "provider_id": self.provider_id,
            "amount": self.amount,
            "currency": self.currency,
            "contractor_name": self.contractor_name,
            "status": self.status.value,
            "items": [item.dict() for item in self.items],
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata
        }


class RFQ(BaseModel):
    """Request for Quote (Outbound Bid Request)."""
    id: UUID = Field(default_factory=uuid4)
    project_name: str
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    status: RFQStatus = RFQStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.now)
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "project_name": self.project_name,
            "description": self.description,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "callback_url": self.callback_url,
            "metadata": self.metadata
        }
