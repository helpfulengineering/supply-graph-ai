from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime


class BidStatus(Enum):
    DRAFT = "draft"
    OPEN = "open"
    BOUNTY_ACCEPTED = "bounty_accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class QuoteStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class QuoteItem:
    bid_item_id: str
    description: str
    cost: float
    ohm_resource_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bidItemId": self.bid_item_id,
            "description": self.description,
            "cost": self.cost,
            "ohm_resource_id": self.ohm_resource_id,
        }


@dataclass
class Quote:
    id: str
    amount: float
    contractor: str
    items: List[QuoteItem] = field(default_factory=list)
    status: QuoteStatus = QuoteStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "amount": self.amount,
            "contractor": self.contractor,
            "items": [item.to_dict() for item in self.items],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Bid:
    ohm_id: str
    project_name: str
    description: str
    project_link: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    callback_url: Optional[str] = None
    status: BidStatus = BidStatus.OPEN
    metadata: Dict[str, Any] = field(default_factory=dict)
    external_id: Optional[str] = None
    quotes: List[Quote] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ohm_id": self.ohm_id,
            "project_name": self.project_name,
            "description": self.description,
            "project_link": self.project_link,
            "required_capabilities": self.required_capabilities,
            "callback_url": self.callback_url,
            "status": self.status.value,
            "metadata": self.metadata,
            "external_id": self.external_id,
            "quotes": [quote.to_dict() for quote in self.quotes],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
