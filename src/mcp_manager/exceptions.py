"""Custom exception classes for MCP Manager."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Available recovery actions."""
    RETRY = "retry"
    SKIP = "skip"
    ROLLBACK = "rollback"
    MANUAL_FIX = "manual_fix"
    IGNORE = "ignore"
    ABORT = "abort"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    server_name: Optional[str] = None
    platform_key: Optional[str] = None
    project_path: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class MCPManagerError(Exception):
    """Base exception for MCP Manager errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, 
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 suggested_actions: Optional[List[RecoveryAction]] = None):
        super().__init__(message)
        self.context = context
        self.severity = severity
        self.suggested_actions = suggested_actions or []
        self.user_message = message  # User-friendly version
        self.technical_details = ""  # Technical details for logs
        
    def get_error_code(self) -> str:
        """Get unique error code for this error type."""
        return f"MCP_{self.__class__.__name__.upper()}"


class ConfigurationError(MCPManagerError):
    """Errors related to configuration issues."""
    
    def __init__(self, message: str, config_path: Optional[str] = None, 
                 field_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_path = config_path
        self.field_name = field_name
        self.user_message = f"Configuration error: {message}"
        self.suggested_actions = [
            RecoveryAction.MANUAL_FIX,
            RecoveryAction.ROLLBACK,
            RecoveryAction.SKIP
        ]


class NetworkError(MCPManagerError):
    """Errors related to network connectivity."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None,
                 status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.endpoint = endpoint
        self.status_code = status_code
        self.user_message = f"Network error: {message}"
        self.suggested_actions = [
            RecoveryAction.RETRY,
            RecoveryAction.SKIP,
            RecoveryAction.MANUAL_FIX
        ]


class DeploymentError(MCPManagerError):
    """Errors during server deployment."""
    
    def __init__(self, message: str, server_name: Optional[str] = None,
                 platform_key: Optional[str] = None, deployment_stage: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.server_name = server_name
        self.platform_key = platform_key
        self.deployment_stage = deployment_stage
        self.user_message = f"Deployment failed: {message}"
        self.suggested_actions = [
            RecoveryAction.RETRY,
            RecoveryAction.ROLLBACK,
            RecoveryAction.SKIP,
            RecoveryAction.MANUAL_FIX
        ]


class ValidationError(MCPManagerError):
    """Errors during validation processes."""
    
    def __init__(self, message: str, validation_rule: Optional[str] = None,
                 invalid_value: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_rule = validation_rule
        self.invalid_value = invalid_value
        self.user_message = f"Validation failed: {message}"
        self.suggested_actions = [
            RecoveryAction.MANUAL_FIX,
            RecoveryAction.SKIP
        ]


class PermissionError(MCPManagerError):
    """Errors related to file system permissions."""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 required_permission: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.required_permission = required_permission
        self.user_message = f"Permission error: {message}"
        self.suggested_actions = [
            RecoveryAction.MANUAL_FIX,
            RecoveryAction.SKIP
        ]


class ResourceError(MCPManagerError):
    """Errors related to system resources."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None,
                 available: Optional[str] = None, required: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.available = available
        self.required = required
        self.user_message = f"Resource error: {message}"
        self.suggested_actions = [
            RecoveryAction.RETRY,
            RecoveryAction.ABORT,
            RecoveryAction.MANUAL_FIX
        ]


class WorkerThreadError(MCPManagerError):
    """Errors in worker thread operations."""
    
    def __init__(self, message: str, worker_type: Optional[str] = None,
                 operation: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.worker_type = worker_type
        self.operation = operation
        self.user_message = f"Background operation failed: {message}"
        self.suggested_actions = [
            RecoveryAction.RETRY,
            RecoveryAction.ABORT
        ]


class HealthCheckError(MCPManagerError):
    """Errors during health check operations."""
    
    def __init__(self, message: str, server_name: Optional[str] = None,
                 check_type: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.server_name = server_name
        self.check_type = check_type
        self.user_message = f"Health check failed: {message}"
        self.suggested_actions = [
            RecoveryAction.RETRY,
            RecoveryAction.SKIP
        ]


class DependencyError(MCPManagerError):
    """Errors related to missing or incompatible dependencies."""
    
    def __init__(self, message: str, dependency_name: Optional[str] = None,
                 required_version: Optional[str] = None, 
                 available_version: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.dependency_name = dependency_name
        self.required_version = required_version
        self.available_version = available_version
        self.user_message = f"Dependency issue: {message}"
        self.suggested_actions = [
            RecoveryAction.MANUAL_FIX,
            RecoveryAction.SKIP
        ]


class ConflictError(MCPManagerError):
    """Errors related to deployment conflicts."""
    
    def __init__(self, message: str, conflict_type: Optional[str] = None,
                 conflicting_servers: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.conflict_type = conflict_type
        self.conflicting_servers = conflicting_servers or []
        self.user_message = f"Conflict detected: {message}"
        self.suggested_actions = [
            RecoveryAction.MANUAL_FIX,
            RecoveryAction.SKIP,
            RecoveryAction.ROLLBACK
        ]


# Error factory for creating appropriate error types
class ErrorFactory:
    """Factory for creating appropriate error instances based on error conditions."""
    
    ERROR_TYPE_MAP = {
        "config": ConfigurationError,
        "network": NetworkError,
        "deployment": DeploymentError,
        "validation": ValidationError,
        "permission": PermissionError,
        "resource": ResourceError,
        "worker": WorkerThreadError,
        "health": HealthCheckError,
        "dependency": DependencyError,
        "conflict": ConflictError,
    }
    
    @classmethod
    def create_error(cls, error_type: str, message: str, **kwargs) -> MCPManagerError:
        """Create an appropriate error instance based on error type."""
        error_class = cls.ERROR_TYPE_MAP.get(error_type, MCPManagerError)
        return error_class(message, **kwargs)
    
    @classmethod
    def from_exception(cls, exc: Exception, context: Optional[ErrorContext] = None) -> MCPManagerError:
        """Convert a generic exception to an MCPManagerError."""
        if isinstance(exc, MCPManagerError):
            return exc
        
        # Map common exception types to our error types
        if isinstance(exc, FileNotFoundError):
            return ConfigurationError(f"File not found: {str(exc)}", context=context)
        elif isinstance(exc, PermissionError):
            return PermissionError(f"Permission denied: {str(exc)}", context=context)
        elif isinstance(exc, ConnectionError):
            return NetworkError(f"Connection error: {str(exc)}", context=context)
        elif isinstance(exc, ValueError):
            return ValidationError(f"Invalid value: {str(exc)}", context=context)
        else:
            return MCPManagerError(f"Unexpected error: {str(exc)}", context=context)