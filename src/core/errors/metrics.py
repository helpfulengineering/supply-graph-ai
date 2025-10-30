"""
Metrics and monitoring system for the Open Matching Engine

This module provides metrics collection for errors,
performance, and LLM operations with real-time monitoring capabilities.
"""

import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
import asyncio

from .exceptions import ErrorSeverity, ErrorCategory, LLMError


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels
        }


@dataclass
class MetricSeries:
    """Series of metric data points"""
    name: str
    metric_type: MetricType
    points: List[MetricPoint] = field(default_factory=list)
    max_points: int = 1000
    
    def add_point(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Add a new metric point"""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            labels=labels or {}
        )
        self.points.append(point)
        
        # Keep only the most recent points
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get the latest metric point"""
        return self.points[-1] if self.points else None
    
    def get_average(self, duration: Optional[timedelta] = None) -> Optional[float]:
        """Get average value over duration"""
        if not self.points:
            return None
        
        cutoff_time = datetime.now() - duration if duration else None
        relevant_points = [
            p for p in self.points
            if cutoff_time is None or p.timestamp >= cutoff_time
        ]
        
        if not relevant_points:
            return None
        
        return sum(p.value for p in relevant_points) / len(relevant_points)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "points": [p.to_dict() for p in self.points[-100:]]  # Last 100 points
        }


class ErrorMetrics:
    """
    Metrics collector for error tracking and analysis.
    
    Tracks error rates, types, severity, and patterns across
    all components of the system.
    """
    
    def __init__(self):
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_rates: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.severity_counts: Dict[ErrorSeverity, int] = defaultdict(int)
        self.category_counts: Dict[ErrorCategory, int] = defaultdict(int)
        self.component_errors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.error_timeline: deque = deque(maxlen=10000)
        self._lock = threading.Lock()
    
    def record_error(
        self,
        error_type: str,
        component: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None
    ):
        """Record an error occurrence"""
        with self._lock:
            # Update counters
            self.error_counts[error_type] += 1
            self.severity_counts[severity] += 1
            self.category_counts[category] += 1
            self.component_errors[component][error_type] += 1
            
            # Record in timeline
            error_event = {
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "component": component,
                "severity": severity.value,
                "category": category.value,
                "details": details or {}
            }
            self.error_timeline.append(error_event)
            
            # Update error rates (errors per minute)
            current_time = datetime.now()
            minute_key = current_time.strftime("%Y-%m-%d %H:%M")
            
            # Clean old rate data (keep last 24 hours)
            cutoff_time = current_time - timedelta(hours=24)
            self.error_rates[error_type] = [
                point for point in self.error_rates[error_type]
                if point.timestamp >= cutoff_time
            ]
            
            # Add new rate point
            self.error_rates[error_type].append(
                MetricPoint(
                    timestamp=current_time,
                    value=1,
                    labels={"component": component, "severity": severity.value}
                )
            )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        with self._lock:
            total_errors = sum(self.error_counts.values())
            
            return {
                "total_errors": total_errors,
                "error_counts": dict(self.error_counts),
                "severity_breakdown": {
                    severity.value: count
                    for severity, count in self.severity_counts.items()
                },
                "category_breakdown": {
                    category.value: count
                    for category, count in self.category_counts.items()
                },
                "component_errors": dict(self.component_errors),
                "recent_errors": list(self.error_timeline)[-100:],  # Last 100 errors
                "error_rates": {
                    error_type: len(points)
                    for error_type, points in self.error_rates.items()
                }
            }
    
    def get_error_rate(self, error_type: str, duration: timedelta = timedelta(minutes=5)) -> float:
        """Get error rate for specific error type over duration"""
        with self._lock:
            if error_type not in self.error_rates:
                return 0.0
            
            cutoff_time = datetime.now() - duration
            recent_errors = [
                point for point in self.error_rates[error_type]
                if point.timestamp >= cutoff_time
            ]
            
            return len(recent_errors) / duration.total_seconds() * 60  # errors per minute


class PerformanceMetrics:
    """
    Metrics collector for performance monitoring.
    
    Tracks operation durations, throughput, resource usage,
    and performance trends across all system components.
    """
    
    def __init__(self):
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.throughput_metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.resource_usage: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.performance_timeline: deque = deque(maxlen=10000)
        self._lock = threading.Lock()
    
    def record_operation(
        self,
        operation: str,
        duration_ms: float,
        component: str,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record operation performance"""
        with self._lock:
            # Update operation metrics
            self.operation_times[operation].append(duration_ms)
            self.operation_counts[operation] += 1
            
            # Keep only recent data (last 1000 operations per type)
            if len(self.operation_times[operation]) > 1000:
                self.operation_times[operation] = self.operation_times[operation][-1000:]
            
            # Record in timeline
            perf_event = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "component": component,
                "duration_ms": duration_ms,
                "success": success,
                "metadata": metadata or {}
            }
            self.performance_timeline.append(perf_event)
            
            # Update throughput metrics (operations per minute)
            current_time = datetime.now()
            minute_key = current_time.strftime("%Y-%m-%d %H:%M")
            
            # Clean old throughput data
            cutoff_time = current_time - timedelta(hours=24)
            self.throughput_metrics[operation] = [
                point for point in self.throughput_metrics[operation]
                if point.timestamp >= cutoff_time
            ]
            
            # Add new throughput point
            self.throughput_metrics[operation].append(
                MetricPoint(
                    timestamp=current_time,
                    value=1,
                    labels={"component": component, "success": str(success)}
                )
            )
    
    def record_resource_usage(
        self,
        resource_type: str,
        usage_value: float,
        component: str,
        unit: str = "count"
    ):
        """Record resource usage metrics"""
        with self._lock:
            self.resource_usage[resource_type].append(
                MetricPoint(
                    timestamp=datetime.now(),
                    value=usage_value,
                    labels={"component": component, "unit": unit}
                )
            )
            
            # Keep only recent data
            if len(self.resource_usage[resource_type]) > 1000:
                self.resource_usage[resource_type] = self.resource_usage[resource_type][-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        with self._lock:
            summary = {
                "operation_stats": {},
                "throughput_stats": {},
                "resource_usage": {},
                "recent_performance": list(self.performance_timeline)[-100:]
            }
            
            # Calculate operation statistics
            for operation, times in self.operation_times.items():
                if times:
                    summary["operation_stats"][operation] = {
                        "count": self.operation_counts[operation],
                        "avg_duration_ms": sum(times) / len(times),
                        "min_duration_ms": min(times),
                        "max_duration_ms": max(times),
                        "p95_duration_ms": sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times),
                        "p99_duration_ms": sorted(times)[int(len(times) * 0.99)] if len(times) > 100 else max(times)
                    }
            
            # Calculate throughput statistics
            for operation, points in self.throughput_metrics.items():
                if points:
                    recent_points = [
                        p for p in points
                        if p.timestamp >= datetime.now() - timedelta(minutes=5)
                    ]
                    summary["throughput_stats"][operation] = {
                        "operations_per_minute": len(recent_points) / 5,
                        "total_operations": len(points)
                    }
            
            # Calculate resource usage statistics
            for resource_type, points in self.resource_usage.items():
                if points:
                    recent_points = [
                        p for p in points
                        if p.timestamp >= datetime.now() - timedelta(minutes=5)
                    ]
                    if recent_points:
                        values = [p.value for p in recent_points]
                        summary["resource_usage"][resource_type] = {
                            "current_value": values[-1],
                            "avg_value": sum(values) / len(values),
                            "min_value": min(values),
                            "max_value": max(values)
                        }
            
            return summary


class LLMMetrics:
    """
    Metrics collector for LLM operations.
    
    Tracks LLM usage, costs, performance, and provider-specific
    metrics with detailed analytics and cost tracking.
    """
    
    def __init__(self):
        self.provider_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "requests": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "total_cost": 0.0,
            "response_times": [],
            "errors": 0,
            "last_request": None
        })
        self.model_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "requests": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "total_cost": 0.0,
            "response_times": [],
            "errors": 0
        })
        self.cost_timeline: deque = deque(maxlen=10000)
        self.usage_timeline: deque = deque(maxlen=10000)
        self._lock = threading.Lock()
    
    def record_llm_request(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        duration_ms: float,
        success: bool = True
    ):
        """Record LLM request metrics"""
        with self._lock:
            # Update provider stats
            self.provider_stats[provider]["requests"] += 1
            self.provider_stats[provider]["tokens_input"] += tokens_input
            self.provider_stats[provider]["tokens_output"] += tokens_output
            self.provider_stats[provider]["total_cost"] += cost
            self.provider_stats[provider]["response_times"].append(duration_ms)
            self.provider_stats[provider]["last_request"] = datetime.now().isoformat()
            
            if not success:
                self.provider_stats[provider]["errors"] += 1
            
            # Keep only recent response times
            if len(self.provider_stats[provider]["response_times"]) > 1000:
                self.provider_stats[provider]["response_times"] = \
                    self.provider_stats[provider]["response_times"][-1000:]
            
            # Update model stats
            model_key = f"{provider}:{model}"
            self.model_stats[model_key]["requests"] += 1
            self.model_stats[model_key]["tokens_input"] += tokens_input
            self.model_stats[model_key]["tokens_output"] += tokens_output
            self.model_stats[model_key]["total_cost"] += cost
            self.model_stats[model_key]["response_times"].append(duration_ms)
            
            if not success:
                self.model_stats[model_key]["errors"] += 1
            
            # Keep only recent response times
            if len(self.model_stats[model_key]["response_times"]) > 1000:
                self.model_stats[model_key]["response_times"] = \
                    self.model_stats[model_key]["response_times"][-1000:]
            
            # Record in timelines
            current_time = datetime.now()
            
            cost_event = {
                "timestamp": current_time.isoformat(),
                "provider": provider,
                "model": model,
                "cost": cost,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output
            }
            self.cost_timeline.append(cost_event)
            
            usage_event = {
                "timestamp": current_time.isoformat(),
                "provider": provider,
                "model": model,
                "duration_ms": duration_ms,
                "success": success
            }
            self.usage_timeline.append(usage_event)
    
    def get_llm_summary(self) -> Dict[str, Any]:
        """Get LLM metrics summary"""
        with self._lock:
            total_cost = sum(stats["total_cost"] for stats in self.provider_stats.values())
            total_requests = sum(stats["requests"] for stats in self.provider_stats.values())
            total_tokens = sum(
                stats["tokens_input"] + stats["tokens_output"]
                for stats in self.provider_stats.values()
            )
            
            return {
                "overview": {
                    "total_cost": total_cost,
                    "total_requests": total_requests,
                    "total_tokens": total_tokens,
                    "avg_cost_per_request": total_cost / total_requests if total_requests > 0 else 0
                },
                "provider_stats": dict(self.provider_stats),
                "model_stats": dict(self.model_stats),
                "recent_costs": list(self.cost_timeline)[-100:],
                "recent_usage": list(self.usage_timeline)[-100:]
            }
    
    def get_cost_breakdown(self, duration: timedelta = timedelta(days=1)) -> Dict[str, Any]:
        """Get cost breakdown over time period"""
        with self._lock:
            cutoff_time = datetime.now() - duration
            
            recent_costs = [
                event for event in self.cost_timeline
                if datetime.fromisoformat(event["timestamp"]) >= cutoff_time
            ]
            
            provider_costs = defaultdict(float)
            model_costs = defaultdict(float)
            
            for event in recent_costs:
                provider_costs[event["provider"]] += event["cost"]
                model_costs[f"{event['provider']}:{event['model']}"] += event["cost"]
            
            return {
                "total_cost": sum(provider_costs.values()),
                "provider_breakdown": dict(provider_costs),
                "model_breakdown": dict(model_costs),
                "period": duration.total_seconds() / 3600,  # hours
                "cost_per_hour": sum(provider_costs.values()) / (duration.total_seconds() / 3600)
            }


# Global metrics instances
_error_metrics: Optional[ErrorMetrics] = None
_performance_metrics: Optional[PerformanceMetrics] = None
_llm_metrics: Optional[LLMMetrics] = None


def get_error_metrics() -> ErrorMetrics:
    """Get global error metrics instance"""
    global _error_metrics
    if _error_metrics is None:
        _error_metrics = ErrorMetrics()
    return _error_metrics


def get_performance_metrics() -> PerformanceMetrics:
    """Get global performance metrics instance"""
    global _performance_metrics
    if _performance_metrics is None:
        _performance_metrics = PerformanceMetrics()
    return _performance_metrics


def get_llm_metrics() -> LLMMetrics:
    """Get global LLM metrics instance"""
    global _llm_metrics
    if _llm_metrics is None:
        _llm_metrics = LLMMetrics()
    return _llm_metrics
