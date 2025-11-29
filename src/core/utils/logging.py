import logging
import sys
import os
from typing import Dict, Any, Optional
import json
from datetime import datetime

def _is_container_environment() -> bool:
    """Check if running in a container/cloud environment"""
    # Check for common container/cloud environment indicators
    return any([
        os.getenv("K_SERVICE"),  # Google Cloud Run
        os.getenv("ECS_CONTAINER_METADATA_URI"),  # AWS ECS
        os.getenv("WEBSITE_INSTANCE_ID"),  # Azure App Service
        os.getenv("CONTAINER_NAME"),  # Generic container
        os.path.exists("/.dockerenv"),  # Docker container
        os.getenv("KUBERNETES_SERVICE_HOST"),  # Kubernetes
    ])

def _get_severity(level: int) -> str:
    """Map Python log level to Cloud Logging severity"""
    # Cloud Logging severity levels: DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL, ALERT, EMERGENCY
    mapping = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }
    return mapping.get(level, "INFO")

class StructuredLogFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging compatible with Stackdriver/CloudWatch"""
    
    def __init__(self, service_name: Optional[str] = None):
        """Initialize formatter
        
        Args:
            service_name: Service name to include in logs (default: "open-matching-engine")
        """
        super().__init__()
        self.service_name = service_name or os.getenv("SERVICE_NAME", "open-matching-engine")
        self.is_container = _is_container_environment()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        severity = _get_severity(record.levelno)
        
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",  # UTC with Z suffix
            "severity": severity,  # Cloud Logging standard
            "level": record.levelname,  # Keep for backward compatibility
            "message": record.getMessage(),
            "service": self.service_name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add trace ID if present (for distributed tracing)
        trace_id = getattr(record, "trace_id", None) or os.getenv("TRACE_ID")
        if trace_id:
            log_data["trace"] = trace_id
        
        # Add request context if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add extra fields if present
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)
        # Also check for any custom attributes added to the record
        for key in ["request_id", "user_id", "trace_id", "endpoint", "method", "status_code"]:
            if hasattr(record, key):
                value = getattr(record, key)
                if value is not None:
                    log_data[key] = value
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add HTTP request info if present (for access logs)
        if hasattr(record, "http_request"):
            log_data["httpRequest"] = record.http_request
            
        return json.dumps(log_data)

def setup_logging(
    level: int = logging.INFO,
    log_file: str = None
) -> None:
    """Setup logging configuration for cloud deployment
    
    In container/cloud environments, logs are only sent to stdout/stderr.
    File logging is only enabled in local development when log_file is specified
    and not running in a container.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file (ignored in container environments)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Determine if we're in a container environment
    is_container = _is_container_environment()
    
    # Always create console handler (stdout for info/debug, stderr for warnings/errors)
    # Cloud services ingest from stdout/stderr
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredLogFormatter())
    
    # Set level filter for console handler
    console_handler.setLevel(level)
    
    # Route ERROR and CRITICAL to stderr, everything else to stdout
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredLogFormatter())
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)
    
    # Only add file handler in local development (not in containers)
    # In containers, all logs should go to stdout/stderr for cloud log ingestion
    if log_file and not is_container:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(StructuredLogFormatter())
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # If file logging fails, log to console and continue
            root_logger.warning(f"Failed to setup file logging: {e}. Logging to console only.")
    elif log_file and is_container:
        # Log a warning that file logging is disabled in containers
        root_logger.info("File logging disabled in container environment. Logs are sent to stdout/stderr.")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name) 