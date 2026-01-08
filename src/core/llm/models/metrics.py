"""
LLM Metrics Models for the Open Hardware Manager.

This module provides data models for LLM metrics and cost tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMMetricType(Enum):
    """Types of LLM metrics."""

    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    COST = "cost"
    PERFORMANCE = "performance"


@dataclass
class LLMCostMetrics:
    """Cost metrics for LLM operations."""

    total_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_per_token: float = 0.0
    currency: str = "USD"
    provider: str = ""
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def add_request_cost(
        self, input_tokens: int, output_tokens: int, cost_per_token: float
    ):
        """Add cost for a single request."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens

        request_cost = (input_tokens + output_tokens) * cost_per_token
        self.total_cost += request_cost

        # Update average cost per token
        if self.total_tokens > 0:
            self.cost_per_token = self.total_cost / self.total_tokens


@dataclass
class LLMMetrics:
    """Comprehensive metrics for LLM operations."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_response_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    last_request_time: Optional[datetime] = None
    cost_metrics: Dict[str, LLMCostMetrics] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)

    def add_request(
        self,
        success: bool,
        tokens: int,
        cost: float,
        response_time: float,
        provider: str,
        model: str,
        error_type: Optional[str] = None,
    ):
        """Add metrics for a single request."""
        self.total_requests += 1
        self.total_tokens += tokens
        self.total_cost += cost
        self.last_request_time = datetime.now()

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Update average response time
        if self.total_requests > 0:
            self.average_response_time = (
                self.average_response_time * (self.total_requests - 1) + response_time
            ) / self.total_requests

        # Update cost metrics by provider
        provider_key = f"{provider}:{model}"
        if provider_key not in self.cost_metrics:
            self.cost_metrics[provider_key] = LLMCostMetrics(
                provider=provider, model=model
            )

        # Calculate tokens split (assuming 50/50 for simplicity)
        input_tokens = tokens // 2
        output_tokens = tokens - input_tokens
        cost_per_token = cost / tokens if tokens > 0 else 0.0

        self.cost_metrics[provider_key].add_request_cost(
            input_tokens, output_tokens, cost_per_token
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def uptime(self) -> timedelta:
        """Calculate uptime since start."""
        return datetime.now() - self.start_time
