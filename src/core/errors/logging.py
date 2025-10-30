"""
Enhanced logging system for the Open Matching Engine

This module provides specialized logging components for LLM operations,
performance tracking, and audit logging with structured output and monitoring capabilities.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from contextlib import asynccontextmanager
from collections import defaultdict, deque

from .exceptions import LLMError, ErrorSeverity


class LogLevel(Enum):
    """Enhanced log levels for OME"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    AUDIT = "audit"
    PERFORMANCE = "performance"


class LogCategory(Enum):
    """Categories for structured logging"""
    SYSTEM = "system"
    USER_ACTION = "user_action"
    API_REQUEST = "api_request"
    LLM_OPERATION = "llm_operation"
    PERFORMANCE = "performance"
    SECURITY = "security"
    AUDIT = "audit"
    ERROR = "error"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    component: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    error_info: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        data['category'] = self.category.value
        return data


class StructuredFormatter(logging.Formatter):
    """Enhanced structured formatter for OME logging"""
    
    def __init__(self, include_traceback: bool = True):
        super().__init__()
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra') and record.extra:
            log_data.update(record.extra)
        
        # Add structured fields
        for field in ['category', 'component', 'operation', 'user_id', 'request_id', 'session_id']:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        # Add duration if present
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        # Add error information
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info) if self.include_traceback else None
            }
        
        return json.dumps(log_data, default=str)


class LLMLogger:
    """
    Specialized logger for LLM operations.
    
    Provides detailed logging for LLM requests, responses, costs,
    and performance metrics with structured output.
    """
    
    def __init__(self, component_name: str = "llm"):
        self.logger = logging.getLogger(f"ome.llm.{component_name}")
        self.component_name = component_name
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.total_tokens: Dict[str, int] = defaultdict(int)
        self.total_cost: Dict[str, float] = defaultdict(float)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
    
    def log_llm_request(
        self,
        provider: str,
        model: str,
        operation: str,
        request_data: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log LLM request with structured data"""
        self.request_counts[f"{provider}:{model}"] += 1
        
        log_data = {
            "category": LogCategory.LLM_OPERATION.value,
            "component": self.component_name,
            "operation": f"llm_request_{operation}",
            "user_id": user_id,
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "request_type": operation,
            "request_size": len(json.dumps(request_data)),
            "metadata": {
                "provider": provider,
                "model": model,
                "operation": operation,
                "request_data": request_data
            }
        }
        
        self.logger.info(f"LLM request to {provider}/{model} for {operation}", extra=log_data)
    
    def log_llm_response(
        self,
        provider: str,
        model: str,
        operation: str,
        response_data: Dict[str, Any],
        duration_ms: float,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log LLM response with performance and cost data"""
        model_key = f"{provider}:{model}"
        
        if tokens_used:
            self.total_tokens[model_key] += tokens_used
        if cost:
            self.total_cost[model_key] += cost
        
        self.response_times[model_key].append(duration_ms)
        
        log_data = {
            "category": LogCategory.LLM_OPERATION.value,
            "component": self.component_name,
            "operation": f"llm_response_{operation}",
            "user_id": user_id,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "provider": provider,
            "model": model,
            "response_type": operation,
            "response_size": len(json.dumps(response_data)),
            "tokens_used": tokens_used,
            "cost": cost,
            "metadata": {
                "provider": provider,
                "model": model,
                "operation": operation,
                "response_data": response_data,
                "performance": {
                    "duration_ms": duration_ms,
                    "tokens_used": tokens_used,
                    "cost": cost
                }
            }
        }
        
        self.logger.info(f"LLM response from {provider}/{model} in {duration_ms:.2f}ms", extra=log_data)
    
    def log_llm_error(
        self,
        provider: str,
        model: str,
        operation: str,
        error: LLMError,
        duration_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log LLM error with detailed context"""
        log_data = {
            "category": LogCategory.ERROR.value,
            "component": self.component_name,
            "operation": f"llm_error_{operation}",
            "user_id": user_id,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "provider": provider,
            "model": model,
            "error_type": type(error).__name__,
            "error_code": getattr(error, 'error_code', None),
            "error_severity": getattr(error, 'severity', ErrorSeverity.MEDIUM).value,
            "metadata": {
                "provider": provider,
                "model": model,
                "operation": operation,
                "error_info": error.to_dict() if hasattr(error, 'to_dict') else str(error)
            }
        }
        
        self.logger.error(f"LLM error from {provider}/{model}: {error}", extra=log_data)
    
    def get_llm_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        stats = {}
        for model_key in self.request_counts:
            provider, model = model_key.split(':', 1)
            response_times = self.response_times[model_key]
            
            stats[model_key] = {
                "provider": provider,
                "model": model,
                "request_count": self.request_counts[model_key],
                "total_tokens": self.total_tokens[model_key],
                "total_cost": self.total_cost[model_key],
                "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0
            }
        
        return stats


class PerformanceLogger:
    """
    Specialized logger for performance monitoring.
    
    Tracks operation durations, resource usage, and performance
    metrics with detailed timing information.
    """
    
    def __init__(self, component_name: str = "performance"):
        self.logger = logging.getLogger(f"ome.performance.{component_name}")
        self.component_name = component_name
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.active_operations: Dict[str, float] = {}
    
    @asynccontextmanager
    async def time_operation(self, operation: str, **context):
        """Context manager for timing operations"""
        start_time = time.time()
        operation_key = f"{operation}_{id(asyncio.current_task())}"
        self.active_operations[operation_key] = start_time
        
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.operation_times[operation].append(duration_ms)
            self.operation_counts[operation] += 1
            
            if operation_key in self.active_operations:
                del self.active_operations[operation_key]
            
            self.log_operation(operation, duration_ms, **context)
    
    def log_operation(
        self,
        operation: str,
        duration_ms: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **metadata
    ):
        """Log operation performance"""
        log_data = {
            "category": LogCategory.PERFORMANCE.value,
            "component": self.component_name,
            "operation": operation,
            "user_id": user_id,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "metadata": {
                "operation": operation,
                "duration_ms": duration_ms,
                **metadata
            }
        }
        
        # Log at different levels based on duration
        if duration_ms > 5000:  # > 5 seconds
            self.logger.warning(f"Slow operation {operation}: {duration_ms:.2f}ms", extra=log_data)
        elif duration_ms > 1000:  # > 1 second
            self.logger.info(f"Operation {operation}: {duration_ms:.2f}ms", extra=log_data)
        else:
            self.logger.debug(f"Operation {operation}: {duration_ms:.2f}ms", extra=log_data)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}
        for operation in self.operation_times:
            times = self.operation_times[operation]
            stats[operation] = {
                "count": self.operation_counts[operation],
                "avg_duration_ms": sum(times) / len(times),
                "min_duration_ms": min(times),
                "max_duration_ms": max(times),
                "total_duration_ms": sum(times)
            }
        
        return stats


class AuditLogger:
    """
    Specialized logger for audit and security events.
    
    Provides detailed logging for security-sensitive operations,
    user actions, and system changes with immutable audit trails.
    """
    
    def __init__(self, component_name: str = "audit"):
        self.logger = logging.getLogger(f"ome.audit.{component_name}")
        self.component_name = component_name
        self.audit_events: deque = deque(maxlen=10000)  # Keep last 10k events
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log user action for audit trail"""
        log_data = {
            "category": LogCategory.AUDIT.value,
            "component": self.component_name,
            "operation": "user_action",
            "user_id": user_id,
            "request_id": request_id,
            "session_id": session_id,
            "action": action,
            "resource": resource,
            "result": result,
            "metadata": {
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "result": result,
                "details": details or {}
            }
        }
        
        # Store in audit trail
        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "user_action",
            "data": log_data
        }
        self.audit_events.append(audit_event)
        
        self.logger.info(f"User {user_id} performed {action} on {resource}: {result}", extra=log_data)
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log security event"""
        log_data = {
            "category": LogCategory.SECURITY.value,
            "component": self.component_name,
            "operation": "security_event",
            "user_id": user_id,
            "request_id": request_id,
            "session_id": session_id,
            "event_type": event_type,
            "severity": severity,
            "metadata": {
                "event_type": event_type,
                "severity": severity,
                "details": details
            }
        }
        
        # Store in audit trail
        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "security_event",
            "data": log_data
        }
        self.audit_events.append(audit_event)
        
        self.logger.warning(f"Security event: {event_type} ({severity})", extra=log_data)
    
    def log_system_change(
        self,
        change_type: str,
        component: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log system configuration or state change"""
        log_data = {
            "category": LogCategory.AUDIT.value,
            "component": self.component_name,
            "operation": "system_change",
            "user_id": user_id,
            "request_id": request_id,
            "change_type": change_type,
            "target_component": component,
            "metadata": {
                "change_type": change_type,
                "target_component": component,
                "details": details
            }
        }
        
        # Store in audit trail
        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "system_change",
            "data": log_data
        }
        self.audit_events.append(audit_event)
        
        self.logger.info(f"System change: {change_type} in {component}", extra=log_data)
    
    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit trail events"""
        return list(self.audit_events)[-limit:]


# Global logger instances
_llm_loggers: Dict[str, LLMLogger] = {}
_performance_loggers: Dict[str, PerformanceLogger] = {}
_audit_loggers: Dict[str, AuditLogger] = {}


def get_llm_logger(component_name: str = "llm") -> LLMLogger:
    """Get or create LLM logger for component"""
    if component_name not in _llm_loggers:
        _llm_loggers[component_name] = LLMLogger(component_name)
    return _llm_loggers[component_name]


def get_performance_logger(component_name: str = "performance") -> PerformanceLogger:
    """Get or create performance logger for component"""
    if component_name not in _performance_loggers:
        _performance_loggers[component_name] = PerformanceLogger(component_name)
    return _performance_loggers[component_name]


def get_audit_logger(component_name: str = "audit") -> AuditLogger:
    """Get or create audit logger for component"""
    if component_name not in _audit_loggers:
        _audit_loggers[component_name] = AuditLogger(component_name)
    return _audit_loggers[component_name]


def setup_enhanced_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    include_traceback: bool = True
) -> None:
    """
    Setup enhanced logging configuration for OME.
    
    Args:
        level: Logging level
        log_file: Optional log file path
        include_traceback: Whether to include tracebacks in logs
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter(include_traceback))
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter(include_traceback))
        root_logger.addHandler(file_handler)
    
    # Set up specialized loggers
    logging.getLogger("ome.llm").setLevel(logging.INFO)
    logging.getLogger("ome.performance").setLevel(logging.DEBUG)
    logging.getLogger("ome.audit").setLevel(logging.INFO)
