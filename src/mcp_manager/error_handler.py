"""Comprehensive error handling system for MCP Manager."""

import traceback
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass
import structlog

from .exceptions import (
    MCPManagerError, ErrorSeverity, RecoveryAction, ErrorContext,
    ConfigurationError, NetworkError, DeploymentError, ValidationError,
    PermissionError, ResourceError, WorkerThreadError, HealthCheckError,
    DependencyError, ConflictError, ErrorFactory
)
from .rollback_manager import RollbackManager
from .backup_system import BackupSystem

logger = structlog.get_logger()


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    action_taken: str
    message: str
    retry_suggested: bool = False
    manual_intervention_required: bool = False


@dataclass
class ErrorDiagnostics:
    """Diagnostic information for an error."""
    error_code: str
    timestamp: str
    stack_trace: Optional[str]
    system_info: Dict[str, Any]
    suggested_fixes: List[str]
    related_logs: List[str]


class RecoveryStrategy:
    """Base class for recovery strategies."""
    
    def can_handle(self, error: MCPManagerError) -> bool:
        """Check if this strategy can handle the given error."""
        raise NotImplementedError
    
    def recover(self, error: MCPManagerError, context: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        """Attempt to recover from the error."""
        raise NotImplementedError


class RetryStrategy(RecoveryStrategy):
    """Recovery strategy that retries the operation with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def can_handle(self, error: MCPManagerError) -> bool:
        return RecoveryAction.RETRY in error.suggested_actions
    
    def recover(self, error: MCPManagerError, context: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        retry_count = context.get('retry_count', 0) if context else 0
        
        if retry_count >= self.max_retries:
            return RecoveryResult(
                success=False,
                action_taken="retry_exhausted",
                message=f"Max retries ({self.max_retries}) exceeded",
                manual_intervention_required=True
            )
        
        # Calculate exponential backoff delay
        delay = self.base_delay * (2 ** retry_count)
        
        return RecoveryResult(
            success=True,
            action_taken="retry_with_backoff",
            message=f"Retrying operation in {delay:.1f} seconds (attempt {retry_count + 1}/{self.max_retries})",
            retry_suggested=True
        )


class RollbackStrategy(RecoveryStrategy):
    """Recovery strategy that rolls back changes."""
    
    def __init__(self, rollback_manager: RollbackManager):
        self.rollback_manager = rollback_manager
    
    def can_handle(self, error: MCPManagerError) -> bool:
        return (RecoveryAction.ROLLBACK in error.suggested_actions and
                self.rollback_manager.can_rollback())
    
    def recover(self, error: MCPManagerError, context: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        try:
            success = self.rollback_manager.rollback_transaction()
            if success:
                return RecoveryResult(
                    success=True,
                    action_taken="rollback_successful",
                    message="Successfully rolled back changes to previous state"
                )
            else:
                return RecoveryResult(
                    success=False,
                    action_taken="rollback_failed",
                    message="Failed to rollback changes",
                    manual_intervention_required=True
                )
        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken="rollback_error",
                message=f"Error during rollback: {str(e)}",
                manual_intervention_required=True
            )


class ConfigFixStrategy(RecoveryStrategy):
    """Recovery strategy for configuration errors."""
    
    def can_handle(self, error: MCPManagerError) -> bool:
        return isinstance(error, ConfigurationError)
    
    def recover(self, error: MCPManagerError, context: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        if not isinstance(error, ConfigurationError):
            return RecoveryResult(False, "not_applicable", "Not a configuration error")
        
        # Attempt automatic fixes for common configuration issues
        fixes_attempted = []
        
        if error.config_path and error.field_name:
            # Try to fix specific field issues
            if error.field_name in ["api_key", "token"]:
                fixes_attempted.append("Check API key configuration")
            elif error.field_name in ["path", "file_path"]:
                fixes_attempted.append("Verify file paths exist and are accessible")
            elif error.field_name in ["url", "endpoint"]:
                fixes_attempted.append("Check URL format and accessibility")
        
        if fixes_attempted:
            return RecoveryResult(
                success=False,  # Requires manual intervention
                action_taken="config_analysis",
                message=f"Configuration issue detected. Suggested fixes: {', '.join(fixes_attempted)}",
                manual_intervention_required=True
            )
        
        return RecoveryResult(
            success=False,
            action_taken="config_generic",
            message="Configuration error requires manual review",
            manual_intervention_required=True
        )


class NetworkRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for network errors."""
    
    def can_handle(self, error: MCPManagerError) -> bool:
        return isinstance(error, NetworkError)
    
    def recover(self, error: MCPManagerError, context: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        if not isinstance(error, NetworkError):
            return RecoveryResult(False, "not_applicable", "Not a network error")
        
        # Analyze network error type
        if error.status_code:
            if error.status_code == 404:
                return RecoveryResult(
                    success=False,
                    action_taken="endpoint_not_found",
                    message="Endpoint not found. Check URL configuration.",
                    manual_intervention_required=True
                )
            elif error.status_code == 401:
                return RecoveryResult(
                    success=False,
                    action_taken="authentication_failed",
                    message="Authentication failed. Check API credentials.",
                    manual_intervention_required=True
                )
            elif error.status_code >= 500:
                return RecoveryResult(
                    success=True,
                    action_taken="server_error_retry",
                    message="Server error detected. Will retry with backoff.",
                    retry_suggested=True
                )
        
        # Generic network error - suggest retry
        return RecoveryResult(
            success=True,
            action_taken="network_retry",
            message="Network error detected. Will retry operation.",
            retry_suggested=True
        )


class ErrorHandler:
    """Main error handler with recovery capabilities."""
    
    def __init__(self, rollback_manager: Optional[RollbackManager] = None):
        self.rollback_manager = rollback_manager or RollbackManager()
        self.backup_system = self.rollback_manager.backup_system
        
        # Initialize recovery strategies
        self.recovery_strategies: List[RecoveryStrategy] = [
            RetryStrategy(),
            RollbackStrategy(self.rollback_manager),
            ConfigFixStrategy(),
            NetworkRecoveryStrategy()
        ]
        
        # Error tracking
        self.error_history: List[Tuple[datetime, MCPManagerError, RecoveryResult]] = []
        self.max_error_history = 100
        
        # Recovery callbacks
        self.recovery_callbacks: Dict[str, Callable] = {}
    
    def handle_error(self, error: Exception, context: Optional[ErrorContext] = None,
                    auto_recover: bool = True) -> RecoveryResult:
        """Main error handling entry point."""
        try:
            # Convert to MCPManagerError if needed
            if not isinstance(error, MCPManagerError):
                mcp_error = ErrorFactory.from_exception(error, context)
            else:
                mcp_error = error
            
            # Log the error
            self.log_error(mcp_error)
            
            # Generate diagnostics
            diagnostics = self.generate_diagnostics(mcp_error)
            
            # Attempt recovery if enabled
            recovery_result = None
            if auto_recover:
                recovery_result = self.attempt_recovery(mcp_error)
            else:
                recovery_result = RecoveryResult(
                    success=False,
                    action_taken="manual_handling",
                    message="Error reported for manual handling",
                    manual_intervention_required=True
                )
            
            # Record in history
            self.error_history.append((datetime.now(), mcp_error, recovery_result))
            self.cleanup_error_history()
            
            return recovery_result
            
        except Exception as e:
            # Error in error handler - log and return basic result
            logger.error(f"Error in error handler: {e}")
            return RecoveryResult(
                success=False,
                action_taken="handler_error",
                message=f"Error handler failed: {str(e)}",
                manual_intervention_required=True
            )
    
    def attempt_recovery(self, error: MCPManagerError) -> RecoveryResult:
        """Attempt to recover from an error using available strategies."""
        for strategy in self.recovery_strategies:
            try:
                if strategy.can_handle(error):
                    logger.info(f"Attempting recovery with {strategy.__class__.__name__}")
                    result = strategy.recover(error)
                    
                    if result.success:
                        logger.info(f"Recovery successful: {result.message}")
                        return result
                    else:
                        logger.warning(f"Recovery failed: {result.message}")
                        if result.manual_intervention_required:
                            break  # Stop trying other strategies
                            
            except Exception as e:
                logger.error(f"Error in recovery strategy {strategy.__class__.__name__}: {e}")
                continue
        
        # No successful recovery
        return RecoveryResult(
            success=False,
            action_taken="no_recovery",
            message="No automatic recovery available",
            manual_intervention_required=True
        )
    
    def log_error(self, error: MCPManagerError) -> None:
        """Log error with appropriate level and context."""
        log_data = {
            "error_code": error.get_error_code(),
            "error_type": error.__class__.__name__,
            "message": error.user_message,
            "severity": error.severity.value
        }
        
        if error.context:
            log_data.update({
                "operation": error.context.operation,
                "server_name": error.context.server_name,
                "platform_key": error.context.platform_key,
                "project_path": error.context.project_path
            })
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", **log_data)
        elif error.severity == ErrorSeverity.ERROR:
            logger.error("Error occurred", **log_data)
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning("Warning", **log_data)
        else:
            logger.info("Info", **log_data)
    
    def generate_diagnostics(self, error: MCPManagerError) -> ErrorDiagnostics:
        """Generate comprehensive diagnostics for an error."""
        return ErrorDiagnostics(
            error_code=error.get_error_code(),
            timestamp=datetime.now().isoformat(),
            stack_trace=traceback.format_exc() if error.__traceback__ else None,
            system_info=self.get_system_info(),
            suggested_fixes=self.get_suggested_fixes(error),
            related_logs=[]  # Could be populated with recent log entries
        )
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get relevant system information for diagnostics."""
        import platform
        import sys
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    
    def get_suggested_fixes(self, error: MCPManagerError) -> List[str]:
        """Get suggested fixes based on error type and context."""
        fixes = []
        
        if isinstance(error, ConfigurationError):
            fixes.extend([
                "Check configuration file syntax and formatting",
                "Verify all required fields are present",
                "Ensure file paths are correct and accessible"
            ])
        elif isinstance(error, NetworkError):
            fixes.extend([
                "Check network connectivity",
                "Verify endpoint URLs and ports",
                "Check firewall and proxy settings",
                "Validate API credentials"
            ])
        elif isinstance(error, DeploymentError):
            fixes.extend([
                "Check platform availability",
                "Verify server configuration",
                "Check for resource conflicts",
                "Review deployment permissions"
            ])
        elif isinstance(error, PermissionError):
            fixes.extend([
                "Check file and directory permissions",
                "Run with appropriate privileges",
                "Verify user has required access rights"
            ])
        
        return fixes
    
    def register_recovery_callback(self, error_type: str, callback: Callable) -> None:
        """Register a callback for specific error types."""
        self.recovery_callbacks[error_type] = callback
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about error occurrences."""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_types = {}
        successful_recoveries = 0
        
        for timestamp, error, recovery in self.error_history:
            error_type = error.__class__.__name__
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if recovery.success:
                successful_recoveries += 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "successful_recoveries": successful_recoveries,
            "recovery_rate": successful_recoveries / len(self.error_history) * 100,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }
    
    def cleanup_error_history(self) -> None:
        """Remove old entries from error history."""
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors with basic information."""
        recent = self.error_history[-limit:] if self.error_history else []
        return [
            {
                "timestamp": timestamp.isoformat(),
                "error_type": error.__class__.__name__,
                "message": error.user_message,
                "severity": error.severity.value,
                "recovery_successful": recovery.success,
                "recovery_action": recovery.action_taken
            }
            for timestamp, error, recovery in recent
        ]


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(error: Exception, context: Optional[ErrorContext] = None,
                auto_recover: bool = True) -> RecoveryResult:
    """Convenience function for handling errors."""
    return get_error_handler().handle_error(error, context, auto_recover)